# Load-Test Runbook — MD-Chat AI Layer

This runbook is the canonical procedure for periodic load tests of the
MD-Chat AI layer. Mandatory cadence: **once per quarter** and before any
release that touches `ai-layer/src/md_chat_ai/api/*` or
`ai-layer/gunicorn.conf.py`.

Owner: AI layer maintainer (Sprint 1: Oleg). Reviewer: SRE on-call.

---

## 1. Pre-flight checklist

Run through every item before launching `benchmark.py`. If any item fails,
**STOP** and remediate; do not proceed.

- [ ] **Target is `staging`, NOT production.** Confirm by `kubectl
      config current-context` (or `ssh staging.md-chat.eu`). Production
      load tests require a written change-management approval ticket.
- [ ] **Staging is at parity with prod.** Same gunicorn worker count,
      same Postgres pool size, same Neo4j heap, same Synapse worker mix.
- [ ] **Synthetic data only.** Database has been reset to the seed fixture
      or contains only `bench-*` / `smoke-*` accounts. No real user PII.
- [ ] **No background long-running jobs.** Pause cron'd retention sweeps
      (`retention-cron.ts`) and DSR export workers for the duration of the
      test (re-enable in §5).
- [ ] **Stakeholders notified.** Post in `#md-chat-ops` 15 min before
      start with start ETA + estimated duration.
- [ ] **Observability up.** Confirm Prometheus is scraping the AI layer
      (`up{job="md-chat-ai"} == 1`) and Grafana dashboard
      `md-chat / AI layer overview` shows live data.
- [ ] **Smoke first.** Run `ai-layer/scripts/smoke.sh` against the
      target — eight checks must be green before load-testing the same
      build.

---

## 2. Run the benchmark

### 2.1 Local laptop (sanity check, low-load)

```bash
cd ai-layer
source .venv/bin/activate

# Boot the app in another terminal:
python -m md_chat_ai.wsgi &

python scripts/benchmark.py \
    --duration 30 \
    --workers 20 \
    --base-url http://localhost:5002
```

Expected wall time: ~2 min (4 endpoints × 30 s + boot).

### 2.2 Staging (full run)

From the load-runner host (must be inside the same VPC as staging — see
`infra/runbooks/load-runner.md` for SSH details):

```bash
cd ~/md-chat/ai-layer
source .venv/bin/activate

python scripts/benchmark.py \
    --duration 300 \
    --workers 100 \
    --base-url https://staging.md-chat.eu \
    --output-dir ~/load-test-artefacts/$(date -u +%Y-%m-%dT%H%M)
```

Total wall time: ~21 min (4 endpoints × 5 min + overhead).

### 2.3 Reading the output

* Top table: per-endpoint rps, p50/p95/p99 latency, `pass` column says
  yes/no on the target rps.
* "Status code distribution" block: any 5xx must be investigated.
* JSON artefact: archive in `~/load-test-artefacts/` and link from the
  GitHub Issue (§4).

---

## 3. SLO thresholds

These are the bright-line thresholds against which a run is judged
**pass** or **regression**.

| Endpoint                                       | Latency p95 | Throughput | Success rate |
|------------------------------------------------|-------------|------------|--------------|
| `GET  /api/health`                             | **< 100 ms** (target < 25 ms) | **>= 1 000 rps** | >= 99.5 % |
| `GET  /api/ready`                              | < 100 ms    | n/a (low traffic) | >= 99.5 % |
| `GET  /.well-known/openid-configuration`       | < 100 ms    | >= 500 rps | >= 99.5 % |
| `GET  /oidc/jwks.json`                         | < 100 ms    | >= 500 rps | >= 99.5 % |
| `POST /api/v1/auth/mfa/setup`                  | **< 500 ms**| >= 200 rps | >= 99.0 % |
| `POST /api/v1/auth/phone/send-code`            | < 500 ms    | >= 100 rps | >= 95.0 % (sms_provider_not_configured counted ok)|
| `POST /api/v1/auth/phone/verify`               | < 500 ms    | >= 100 rps | >= 99.0 % |
| `POST /api/v1/legal/eevidence/submit`          | < 750 ms    | >= 50 rps  | >= 99.5 % |
| Twin chat (future, AI agent route)             | < 1 200 ms  | >= 20 rps  | >= 99.0 % |

**Hard failure**: any endpoint with `errors > 0.5 %` or `5xx > 0`.

**Soft regression**: p95 latency > 1.5× the previous quarter's recorded
number on the same endpoint. File a GitHub Issue (§4) with the
``performance-regression`` label.

---

## 4. Post-test artefacts

After every staging run:

1. **Archive the JSON report.** Copy
   `~/load-test-artefacts/<timestamp>/benchmark-*.json` to the
   `md-chat-load-artefacts` S3 bucket (path
   `s3://md-chat-load-artefacts/ai-layer/<YYYY-MM>/`).
2. **Snapshot Prometheus metrics.** Use
   `promtool query range --start=<run_start> --end=<run_end>` for the
   key recording rules:
   * `mdchat:ai_layer_request_rate_5m`
   * `mdchat:ai_layer_p95_latency_5m`
   * `mdchat:ai_layer_5xx_rate_5m`
   * `mdchat:postgres_connections_used`
   * `mdchat:neo4j_query_p95_50m`
   Save outputs alongside the benchmark JSON.
3. **Grafana screenshots.** Capture the `md-chat / AI layer overview`
   dashboard for the run window; attach to the artefact folder.
4. **GitHub Issue.** Open an issue in
   `olegchetrean/md-chat` with title
   `Load test report — <YYYY-MM-DD>`.
   * Label: `performance-report` (or `performance-regression` on failure).
   * Body template:

     ```markdown
     ## Run metadata
     - Target  : staging.md-chat.eu
     - Build   : <git short SHA>
     - Started : <UTC timestamp>
     - Duration: <minutes>

     ## Headline numbers
     | Endpoint | rps | p50 | p95 | p99 | pass |
     | --- | --- | --- | --- | --- | --- |
     | ... copy from benchmark output ... |

     ## SLO verdict
     - [ ] All endpoints met target rps
     - [ ] All endpoints met p95 latency target
     - [ ] No 5xx observed

     ## Regressions vs last quarter
     <or "none">

     ## Action items
     - [ ] ...
     ```

5. **Update `docs/performance.md` §1-5** if numbers shifted by > 10 %.

---

## 5. Restore after the run

- [ ] Re-enable retention cron + DSR worker.
- [ ] Reset staging DB to a clean fixture if the test created residual rows
      (`make staging.reset-db`).
- [ ] Post outcome in `#md-chat-ops` (one sentence + GitHub Issue link).

---

## 6. Cadence + ownership

| Trigger                                        | Run scope                                                | Owner       |
|------------------------------------------------|----------------------------------------------------------|-------------|
| Quarterly (first Monday of Jan / Apr / Jul / Oct) | Full §2.2 staging run, full SLO sweep                | SRE on-call |
| Pre-release (touches `ai-layer/`)              | §2.1 laptop + §2.2 staging on RC build                   | Maintainer  |
| Post-incident (P0 or P1)                       | §2.2 staging run before re-opening traffic               | IC + SRE    |
| On request                                     | Ad-hoc — file a ticket; SRE to schedule within 5 working days | requester |

---

## 7. Escalation

If a load test **fails** (any hard-failure condition in §3):

1. **Do not deploy** the offending build to production. The release is
   blocked until the regression is fixed and re-tested.
2. Page the SRE on-call (PagerDuty service `md-chat-ai`).
3. Open the GitHub Issue with the `performance-regression` label and tag
   `@olegchetrean` and the AI layer maintainer.
4. If the regression is in a critical path (`/api/health`, `/auth/*`),
   roll back to the previous green build immediately.

---

## 8. Future improvements (Sprint 1+)

* Replace `scripts/benchmark.py` quarterly run with a managed **k6 cloud**
  job for graphs + comparison-over-time.
* Wire a `make benchmark` target that combines smoke + benchmark into a
  single GitHub Actions workflow on the `staging` branch.
* Add a synthetic twin-chat endpoint (`POST /api/v1/twin/chat`) once it
  lands; include it in `ENDPOINTS` in `benchmark.py`.
* Capture Neo4j query plans automatically during the run via
  `dbms.listQueries()` sampling.
