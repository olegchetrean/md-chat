# Production Deployment — md-chat-ai

This guide covers running the `ai-layer` Flask app in production behind
gunicorn. The dev-time `python -m md_chat_ai.wsgi` launches Flask's
single-threaded werkzeug server, which is unsafe for production (no
concurrency, fragile under load, no graceful shutdown, no worker recycling).

## Why gunicorn?

We picked gunicorn over uwsgi for four reasons:

1. **Community size.** Most Flask production deployments use gunicorn; debug
   help, blog posts, and stack overflow answers all assume it. uwsgi has a
   wider feature surface but is mostly abandoned upstream.
2. **gevent / gthread compatibility.** Our codebase is sync-mostly Flask with
   async pockets (LLM streaming via httpx). `gthread` workers handle this
   without rewriting routes. uwsgi's threading story is rougher.
3. **Simpler config.** One pure-Python file, hooks are normal functions, env
   vars override sensibly. uwsgi's `.ini` plus `--http-socket` plus protocol
   options is harder to read.
4. **Docker-native logging.** gunicorn writes access/error logs to stdout/stderr
   with a single `-` configuration, which is exactly what Docker, journald,
   and Kubernetes expect.

Alternatives like `uvicorn` or `hypercorn` are designed for ASGI; Flask is
WSGI, so they would force us to wrap with `asgiref.WsgiToAsgi` and lose the
benefit. Stick with gunicorn until we migrate to ASGI deliberately.

## Quick start

```bash
cd ai-layer
source .venv/bin/activate
pip install -e ".[dev]"
gunicorn --check-config -c gunicorn.conf.py "md_chat_ai.api:create_app()"
./scripts/gunicorn-run.sh   # foreground; Ctrl-C to stop
```

Then verify `/api/health` returns `200`:

```bash
curl -fsS http://localhost:5002/api/health
```

## Configuration knobs

All defaults live in `ai-layer/gunicorn.conf.py`. Override via environment
variables (no config file edits required for routine tuning):

| Variable | Default | Notes |
|----------|---------|-------|
| `AI_LAYER_HOST` | `0.0.0.0` | Bind address. Use `127.0.0.1` if reverse proxy is on the same host. |
| `AI_LAYER_PORT` | `5002` | Bind port. |
| `AI_LAYER_WORKERS` | `min(2*CPU+1, 8)` | Override absolute worker count. |
| `AI_LAYER_THREADS` | `4` | Threads per worker (gthread). |
| `AI_LAYER_TIMEOUT` | `30` | Worker timeout in seconds. |
| `AI_LAYER_KEEPALIVE` | `5` | Keep-alive in seconds. |
| `AI_LAYER_MAX_REQ` | `1000` | Recycle each worker after N requests. |
| `AI_LAYER_MAX_REQ_JITTER` | `50` | Random jitter so workers don't recycle at once. |
| `LOG_LEVEL` | `INFO` | Forwarded to both gunicorn and the app's `_configure_logging()`. |
| `GUNICORN_PRELOAD` | `false` | Preload app for CoW memory savings. Verify socket-holding globals first. |

## Scaling workers

The default formula `2 * CPU_COUNT + 1` (capped at 8) follows the gunicorn
docs and is a good starting point. Rules of thumb when tuning:

- **CPU-bound** (heavy embedding / graph traversals): keep `workers` close to
  CPU count, drop `threads` to 1-2. Add a separate worker pool (RQ, Celery)
  for CPU-heavy tasks instead of expanding the web pool.
- **I/O-bound** (waiting on Router by MP, Neo4j, Synapse): raise `threads`
  before adding workers; threads share memory and recycle faster.
- **Memory-pressured** (Anthropic SDK + httpx + neo4j drivers each hold per-
  process caches): leave `workers` low, raise `max_requests` jitter to keep
  the memory floor predictable. Enable `GUNICORN_PRELOAD=true` for ~30-40%
  RSS savings via copy-on-write — but verify with a load test first because
  some lazy globals in `md_chat_ai.llm` open HTTP connections eagerly.

Cap at 8 workers per process pod. Beyond that, scale horizontally (more pods)
because downstream services (Neo4j connection pool, Synapse AS, Router
quotas) become the bottleneck long before raw worker count does.

## Reverse proxy (nginx → gunicorn)

Gunicorn must run behind a reverse proxy in production. nginx config snippet:

```nginx
upstream md_chat_ai {
    server 127.0.0.1:5002 fail_timeout=0;
    keepalive 32;
}

server {
    listen 443 ssl http2;
    server_name api.md-chat.eu;

    # IMPORTANT: keep nginx timeout > gunicorn timeout to avoid hiding worker hangs.
    # gunicorn timeout=30s  →  nginx proxy_read_timeout=60s
    proxy_read_timeout    60s;
    proxy_connect_timeout 10s;
    proxy_send_timeout    60s;

    location / {
        proxy_pass         http://md_chat_ai;
        proxy_http_version 1.1;
        proxy_set_header   Connection "";
        # Required for gunicorn to know the real client IP and protocol.
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_set_header   X-Forwarded-Host  $host;
        proxy_set_header   X-Forwarded-Port  $server_port;
        # Per-request trace id; forwarded to gunicorn access log via access_log_format.
        proxy_set_header   X-Request-ID      $request_id;
    }

    location /api/health {
        access_log off;
        proxy_pass http://md_chat_ai;
    }
}
```

If you terminate TLS at nginx, make sure Flask trusts the `X-Forwarded-Proto`
header — already handled by `werkzeug.middleware.proxy_fix.ProxyFix` if you
add it in the factory. For now we rely on nginx for the rewrite.

## Healthcheck integration

The Flask app exposes `/api/health` (blueprint in `md_chat_ai.api.health`).
Wire it into:

- **Docker:** already declared in `ai-layer/Dockerfile` via `HEALTHCHECK`.
- **Kubernetes:** `livenessProbe` + `readinessProbe` on `/api/health`,
  `initialDelaySeconds: 10`, `periodSeconds: 30`, `timeoutSeconds: 5`.
- **External monitoring:** UptimeRobot / BetterStack hitting the public
  domain. Alert if `>2` consecutive failures.

Do not let load balancers hammer `/api/health` faster than `periodSeconds: 5`
— each probe still consumes a thread.

## Graceful shutdown

When gunicorn receives `SIGTERM` (Docker stop, k8s rolling update, systemd
stop), it:

1. Stops accepting new connections on the listening socket.
2. Sends `SIGTERM` to every worker.
3. Each worker finishes in-flight requests up to `graceful_timeout` (30s).
4. Any worker still busy after the grace window is killed with `SIGKILL`.

To avoid in-flight LLM streams being cut, terminate the upstream load
balancer first (drain) and only then stop the pod. In nginx land, that means
removing the upstream entry, waiting `proxy_read_timeout`, then issuing the
stop.

The `scripts/gunicorn-run.sh` launcher uses `exec` so PID 1 inside the
container is gunicorn itself — `docker stop` therefore delivers the signal
directly with no shell intermediary.

## Log shipping (Prometheus + Loki)

Gunicorn logs access + error events to stdout in a slightly extended combined
format including request latency in microseconds and the `X-Request-ID`
header. The full format is defined in `gunicorn.conf.py:access_log_format`.

- **Loki:** scrape with Promtail using `docker_sd_configs` or
  `journald_sd_configs`; parse with the LogQL `regexp` parser to extract
  `request_id` and `status`.
- **Prometheus:** the Flask app exposes a `prometheus-client` registry — wire
  in the standard `/metrics` endpoint (planned issue) and scrape from
  Prometheus. Gunicorn itself exposes nothing; per-worker metrics need
  `prometheus_client.multiprocess.MultiProcessCollector` and the
  `PROMETHEUS_MULTIPROC_DIR` env var. See the `prometheus_client` docs for
  the dance.

## Memory profiling

When a worker grows above ~500MB RSS it's almost always one of:

1. **httpx connection pool leak** — usually from forgetting to call
   `await client.aclose()`. Hunt with `tracemalloc`:
   ```python
   import tracemalloc; tracemalloc.start(25)
   # ... reproduce
   snap = tracemalloc.take_snapshot()
   for stat in snap.statistics("lineno")[:20]: print(stat)
   ```
2. **Anthropic / OpenAI SDK retry buffers** — they hold response bodies in
   memory while retrying.
3. **Neo4j driver session leak** — every `session = driver.session()` not
   inside a `with` block.

For production, use `py-spy dump --pid <worker_pid>` to grab a live
stacktrace, and `memray` for ongoing allocation profiling. `max_requests`
plus `max_requests_jitter` exists precisely to recycle leaky workers before
they OOM.

## Common pitfalls

- **Worker timeout < load balancer timeout.** If gunicorn `timeout=30s` and
  the nginx/ALB timeout is `30s`, you get a race where the LB hangs up
  before gunicorn can return its `499`/`502`. Always set the LB timeout at
  least 1.5× the gunicorn timeout.
- **`--reload` in production.** Dev-only. Reloads on every file change and
  doubles memory. Never set this in container images.
- **Forking with open sockets.** Some libraries (psycopg2, certain Redis
  clients) cannot survive a `fork()` while holding a socket. If you set
  `preload_app = True`, ensure no module-level code opens connections. The
  Flask factory pattern (`create_app()` inside each worker) sidesteps this
  by construction — that's why our entry point is `md_chat_ai.api:create_app()`
  *with parens*, not a bare WSGI callable.
- **Healthcheck against the gunicorn admin port.** Gunicorn has no built-in
  admin port. The healthcheck must hit the actual `/api/health` route.
- **Mixing `gthread` and async libraries.** `gthread` workers are sync; if a
  route awaits a coroutine, wrap it with `asgiref.sync.async_to_sync` rather
  than switching the worker class.
- **Bind to `127.0.0.1` inside Docker.** Docker bridges traffic to container
  IP, not loopback — bind to `0.0.0.0` (the default) and let Docker / k8s
  do the network routing.

## Reference

- gunicorn settings: https://docs.gunicorn.org/en/stable/settings.html
- gunicorn signals: https://docs.gunicorn.org/en/stable/signals.html
- Flask deployment options: https://flask.palletsprojects.com/en/3.0.x/deploying/
