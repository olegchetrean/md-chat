"""Gunicorn production configuration for md-chat-ai.

Loaded with ``gunicorn -c gunicorn.conf.py "md_chat_ai.api:create_app()"``.

Environment variables (all optional, sensible defaults applied):
    AI_LAYER_HOST       Bind host (default: 0.0.0.0)
    AI_LAYER_PORT       Bind port (default: 5002)
    AI_LAYER_WORKERS    Override worker count (default: 2*CPU + 1, capped at 8)
    AI_LAYER_THREADS    Threads per worker (default: 4)
    AI_LAYER_TIMEOUT    Worker timeout in seconds (default: 30)
    AI_LAYER_KEEPALIVE  Keep-alive in seconds (default: 5)
    AI_LAYER_MAX_REQ    Max requests per worker before recycle (default: 1000)
    AI_LAYER_MAX_REQ_JITTER  Jitter on max requests (default: 50)
    LOG_LEVEL           Gunicorn + app log level (default: INFO)
    GUNICORN_PRELOAD    Set "true" to preload app for copy-on-write savings
"""

from __future__ import annotations

import multiprocessing
import os

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _env_int(name: str, default: int) -> int:
    """Read an int env var; fall back to default on missing/invalid."""
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _compute_worker_count() -> int:
    """Standard gunicorn formula 2*CPU + 1, capped at 8.

    Capping avoids accidentally spawning 32+ workers on big bare-metal hosts
    where Neo4j/Synapse downstream connections become the real bottleneck.
    """
    override = _env_int("AI_LAYER_WORKERS", 0)
    if override > 0:
        return override
    try:
        cpu = multiprocessing.cpu_count()
    except NotImplementedError:  # pragma: no cover — extremely rare
        cpu = 1
    return min(2 * cpu + 1, 8)


# ---------------------------------------------------------------------------
# Server socket
# ---------------------------------------------------------------------------

bind = f"{os.getenv('AI_LAYER_HOST', '0.0.0.0')}:{_env_int('AI_LAYER_PORT', 5002)}"
backlog = 2048

# ---------------------------------------------------------------------------
# Worker processes
# ---------------------------------------------------------------------------

workers = _compute_worker_count()
# gthread = sync worker that hands off to a thread pool; suits Flask + httpx
# (mostly synchronous, async pockets like LLM streaming use background threads).
worker_class = "gthread"
threads = _env_int("AI_LAYER_THREADS", 4)
worker_connections = 1000

# Recycle workers periodically to combat slow memory leaks in third-party libs
# (anthropic, openai, neo4j drivers all keep some per-process caches).
max_requests = _env_int("AI_LAYER_MAX_REQ", 1000)
max_requests_jitter = _env_int("AI_LAYER_MAX_REQ_JITTER", 50)

# Timeouts -------------------------------------------------------------------
# Twin chat with LLM streaming may legitimately exceed 30s; accept that and
# rely on upstream nginx/L7 LB to surface client cancellations.
timeout = _env_int("AI_LAYER_TIMEOUT", 30)
graceful_timeout = 30  # SIGTERM -> SIGKILL window
keepalive = _env_int("AI_LAYER_KEEPALIVE", 5)

# Preload trades startup speed for memory savings (CoW). Off by default
# because some lazy globals in md_chat_ai.llm hold sockets we don't want
# duplicated across forks; flip via GUNICORN_PRELOAD=true once verified.
preload_app = _env_bool("GUNICORN_PRELOAD", False)

# ---------------------------------------------------------------------------
# Logging — all to stdout/stderr so Docker, journald, k8s can pick it up.
# ---------------------------------------------------------------------------

accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "INFO").lower()
# Combined-style log with request time + trace id (X-Request-ID forwarded by nginx).
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s '
    '"%(f)s" "%(a)s" %(D)sus rid=%({x-request-id}i)s'
)
capture_output = True

# ---------------------------------------------------------------------------
# Process naming (helps `ps`, `top`, supervisor dashboards)
# ---------------------------------------------------------------------------

proc_name = "md-chat-ai"

# ---------------------------------------------------------------------------
# Server hooks
# ---------------------------------------------------------------------------


def on_starting(server) -> None:  # noqa: ANN001 — gunicorn passes its Arbiter
    """Configure application logging once, master-side, before any forks."""
    try:
        from md_chat_ai.wsgi import _configure_logging

        _configure_logging()
    except Exception as exc:  # pragma: no cover — defensive only
        server.log.warning("md-chat-ai logging bootstrap failed: %s", exc)
    server.log.info(
        "md-chat-ai gunicorn starting: workers=%s threads=%s bind=%s timeout=%ss",
        workers,
        threads,
        bind,
        timeout,
    )


def post_fork(server, worker) -> None:  # noqa: ANN001
    """Log worker PID so log lines can be traced back to a process."""
    server.log.info("worker spawned pid=%s id=%s", worker.pid, worker.age)


def worker_int(worker) -> None:  # noqa: ANN001
    """Log Ctrl-C / SIGINT escalation for graceful shutdown debugging."""
    worker.log.info("worker received SIGINT pid=%s", worker.pid)


def worker_abort(worker) -> None:  # noqa: ANN001
    """Triggered when a worker is killed for timeout — log loudly."""
    worker.log.error("worker aborted (timeout) pid=%s", worker.pid)


def on_exit(server) -> None:  # noqa: ANN001
    server.log.info("md-chat-ai gunicorn shutting down")
