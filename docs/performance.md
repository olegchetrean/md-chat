# MD-Chat — Performance Characteristics

Status: **draft v0.1** — captured during Sprint 1 bootstrap. Numbers below
mix (a) verified single-host measurements, (b) Element ESS / Synapse community
benchmarks, and (c) cautious extrapolations clearly marked *projected*.
Re-validate on the staging cluster before quoting any of these externally.

The architecture this document refers to is the four-service stack:

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Synapse    │ ←→ │  AI layer    │ ←→ │   Neo4j      │ ←→ │  Postgres    │
│ (Element ESS)│    │  Flask 3 +   │    │ knowledge    │    │ users/auth/  │
│  Matrix HS   │    │  gunicorn    │    │ graph        │    │ eEvidence    │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

---

## 1. Synapse — expected load envelope

Source: Element Server Suite (ESS) operations docs, `synapse-admin` field
data, and the matrix.org public homeserver post-mortems.

| Topology                         | Sustained MAU per worker pool | Federation peers | Notes |
|----------------------------------|-------------------------------|------------------|-------|
| Single-process Synapse           | up to **5 000** MAU           | < 50 active      | Bootstrap tier. CPU-bound on `presence`, `device_lists`. |
| Worker mode (generic + federation_sender + event_persister + media_repo) | **10 000 – 50 000** MAU | 100 – 1 000 | Recommended baseline once we cross 2 k MAU. |
| Full ESS topology (8 – 12 worker types, Postgres replication, Redis stream) | **50 000 – 100 000** MAU | > 1 000 | Mandatory for any production rollout > 25 k MAU. |

Worker rule of thumb (Element guidance):

* 1 × `generic_worker` per 10 k concurrent Matrix clients.
* 1 × `federation_sender` per 200 actively-federating peers.
* 1 × `event_persister` shard per ~1 k events/s of room writes.
* `media_repository` is bandwidth-bound — scale on egress, not on event rate.

> **MD-Chat target Y1**: 100 k – 300 k MAU consumer + 5 k B2B seats. Plan for a
> 12-worker ESS topology by month 6 of public launch.

---

## 2. AI layer (Flask) — expected throughput

Endpoints fall in three latency classes:

| Class    | Examples                                            | Expected p95 | Per-worker rps |
|----------|-----------------------------------------------------|--------------|----------------|
| Static   | `/api/health`, `/api/ready`, OIDC discovery, JWKS   | < 5 ms       | 1 500 – 3 000  |
| Light I/O| auth verifies, ticket look-ups (Postgres single-row)| < 50 ms      | 500 – 800      |
| Heavy CPU| `/mfa/setup` (TOTP + Argon2 backup hash), PIN wrap  | < 250 ms     | 30 – 80        |
| AI agent | twin chat (Neo4j query + LLM round-trip via Router) | < 1 200 ms   | 5 – 20         |

**Per-gunicorn-worker budget (sync workers, 4 threads):** 200 – 500 rps
across mixed traffic. Confirmed with `scripts/benchmark.py` against a single
laptop worker; staging numbers expected to exceed this once kernel TCP
backlog and connection pool are tuned (`scripts/gunicorn-run.sh`).

**Worker count formula** (already encoded in `gunicorn.conf.py`):

```
workers = min(2 * CPU + 1, 8)   # cap at 8 → Neo4j/Postgres pool becomes bottleneck
threads = 4
```

On a 4-vCPU host that gives 8 workers × 4 threads = 32 in-flight requests
(soft cap; Postgres pool = 30 by default — see §4).

---

## 3. Neo4j — query budget per twin chat

The AI layer's "Digital Twin" feature performs **at most 3 graph round-trips**
per user-facing chat turn:

| Step                                         | Target p95 | Notes |
|----------------------------------------------|------------|-------|
| Fetch user node + 1-hop neighbours (≤ 50)    | 12 ms      | Indexed on `user_id`. |
| Pattern match for topic / commitment recall  | 22 ms      | Cypher uses `apoc.path.expandConfig`. |
| Append new fact node + relationships         | 16 ms      | Single `CREATE` + `MERGE`. |

**Total Neo4j budget per chat turn: p95 < 50 ms.** Anything above 50 ms
sustained must trigger an index audit (`CALL db.indexes()`) and a query plan
review (`EXPLAIN`/`PROFILE`).

Pool size: Bolt driver `max_connection_pool_size=50` (one per AI layer
worker × ~6× over-subscription factor for short-lived queries).

---

## 4. Postgres — connection pool sizing

The AI layer uses SQLAlchemy with psycopg2; the Synapse cluster uses Synapse's
native asynchronous pool. They MUST live in separate Postgres roles to avoid
slot exhaustion between services.

### AI layer pool (`config.py`)

| Setting                          | Default | Knob (env)                    | Rationale |
|----------------------------------|---------|-------------------------------|-----------|
| `postgres_pool_size`             | 10      | `POSTGRES_POOL_SIZE`          | Per worker process. With 8 workers → 80 base connections. |
| `postgres_max_overflow`          | 20      | `POSTGRES_MAX_OVERFLOW`       | Hot-burst cushion; freed after `pool_timeout`. |
| `postgres_pool_timeout`          | 30 s    | `POSTGRES_POOL_TIMEOUT`       | Time to wait for a free connection before failing the request. |
| `postgres_echo`                  | false   | `POSTGRES_ECHO`               | Set true only for query-plan debugging. |

### Synapse (`homeserver.yaml`)

```yaml
database:
  name: psycopg2
  args:
    user: synapse
    password: <vault>
    database: synapse
    host: pg.internal
    cp_min: 5
    cp_max: 10
    keepalives: 1
    keepalives_idle: 10
    keepalives_interval: 10
    keepalives_count: 3
```

* `cp_min: 5` per worker, `cp_max: 10` per worker.
* On a 12-worker topology that's 60 – 120 connections from Synapse alone.

### Server-side ceiling

| Postgres setting       | Target value                                            |
|------------------------|---------------------------------------------------------|
| `max_connections`      | 400 (AI layer 240 + Synapse 120 + admin 40)             |
| `shared_buffers`       | 25 % of host RAM                                        |
| `effective_cache_size` | 75 % of host RAM                                        |
| `work_mem`             | 16 MB (raise carefully — multiplies per query)          |
| `wal_compression`      | `on` (zstd preferred where available)                   |

If `max_connections` is contested, deploy **PgBouncer** in transaction mode
in front of Postgres — both services support it.

---

## 5. Memory profile per service (RSS, post-boot, idle)

Measured locally on macOS arm64; Linux x86_64 production hosts run within
10 % of these numbers in our experience.

| Service             | Idle RSS    | Steady-state under load     | Notes                                |
|---------------------|-------------|------------------------------|--------------------------------------|
| AI layer worker     | 95 – 130 MB | 180 – 280 MB                 | Larger if Neo4j driver caches many sessions. |
| AI layer master     | 60 MB       | 60 MB                        | Gunicorn parent.                     |
| Synapse single-proc | 350 MB      | 1.2 – 2.0 GB                 | Federation grows steady-state.       |
| Synapse generic_w   | 200 MB      | 400 – 700 MB                 | Per worker.                          |
| Neo4j (1 GB heap)   | 1.2 GB      | 1.5 – 2.5 GB                 | Heap + page cache.                   |
| Postgres            | 250 MB      | 1 – 4 GB                     | Scales with `shared_buffers`.        |

**Provision rule**: budget AI layer worker peak at **300 MB** for capacity
planning; set Kubernetes `requests.memory=200Mi`, `limits.memory=512Mi`.

---

## 6. When to scale horizontally

Heuristics — applied in this order:

1. **AI layer first.** It is stateless, behind a load balancer, and easy
   to scale. Add a replica when:
   * sustained CPU > 60 % across 5 min, OR
   * p95 latency on `/api/health` > 25 ms (a canary — health should always
     be fast; high latency means CPU starvation), OR
   * Postgres pool exhaustion errors appear in logs (`QueuePool limit … reached`).

2. **Postgres vertical first, horizontal later.**
   * Vertical: bump `shared_buffers` and instance class until 70 % of
     `max_connections` is the bottleneck.
   * Horizontal: read replicas for analytical queries (registers, audit
     chain views) — never split writes.

3. **Synapse workers.** Add another `generic_worker` per 10 k MAU step;
   add `federation_sender` if `synapse_federation_client_send_outgoing`
   queue depth > 1 000 sustained. Adding workers is cheap if Redis stream
   + Postgres can keep up — see [Synapse worker docs](https://element-hq.github.io/synapse/latest/workers.html).

4. **Neo4j scale-up before scale-out.**
   Causal clustering is operationally heavy. For < 1 M users a single
   well-provisioned instance (8 vCPU, 32 GB RAM, NVMe) handily covers the
   twin-chat workload. Move to Neo4j Causal Cluster only if write rate
   exceeds 1 k events/s or you require multi-DC resilience.

---

## 7. Benchmark + smoke harness

* `ai-layer/scripts/benchmark.py` — pure-Python httpx benchmark, see
  `docs/load-test-runbook.md`.
* `ai-layer/scripts/smoke.sh` — boots the Flask app and runs eight
  contract checks. Run pre-deploy and in CI on every PR touching
  `ai-layer/`.

The smoke test is the canonical green-light gate; the benchmark is the
quarterly capacity check.

---

## 8. Open performance work (Sprint 1+ candidates)

| ID    | Area              | Description                                           | Priority |
|-------|-------------------|-------------------------------------------------------|----------|
| PERF-1| AI layer          | Switch gunicorn to gthread + `gevent` for I/O-bound twin-chat workers; benchmark before/after. | P1 |
| PERF-2| Postgres          | Introduce PgBouncer + connection multiplexing.        | P1 |
| PERF-3| Neo4j             | Cypher query plan review; add composite indices on `(user_id, topic)`. | P2 |
| PERF-4| Observability     | Wire Prometheus histograms on every Flask route — already exposed via `prometheus_client`. | P1 |
| PERF-5| Synapse           | Plan worker-mode migration; target month-3 of public launch. | P0 |
| PERF-6| AI layer          | Cache OIDC discovery & JWKS in nginx (long TTL).      | P2 |
| PERF-7| AI layer          | Implement Anthropic `cache_control: ephemeral` on system-prompt heavy routes (drop-in saving on Router). | P1 |
