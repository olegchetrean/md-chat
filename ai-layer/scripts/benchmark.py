"""HTTP benchmark for the MD-Chat AI layer.

Pure-Python, ``httpx.AsyncClient``-based load generator. Designed to be
runnable on any developer laptop without installing a dedicated tool
(locust / vegeta / k6). Use it for smoke-level capacity checks, regression
sniffing on a staging deploy, and Sprint review numbers.

NOT a substitute for a full load test against a production-shaped cluster
— for that, see ``docs/load-test-runbook.md`` (k6 + Grafana k6 cloud).

CLI
---

.. code-block:: bash

    python scripts/benchmark.py --duration 30 --workers 20 \\
        --base-url http://localhost:5002

Endpoints exercised
-------------------

* ``GET  /api/health``                            — target >1000 rps
* ``GET  /.well-known/openid-configuration``       — target  >500 rps
* ``POST /api/v1/auth/mfa/setup``                  — target  >200 rps
* ``POST /api/v1/auth/phone/send-code``            — best-effort, expect
  ``sms_provider_not_configured`` when ``INFOBIP_API_KEY`` is unset.

Output
------

* Human-readable per-endpoint table on stdout.
* JSON dump ``benchmark-<unix-ts>.json`` next to ``cwd``.

License: Apache-2.0
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import statistics
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:  # pragma: no cover — surfaced to the user
    print("ERROR: httpx is required. Install with `pip install httpx`.", file=sys.stderr)
    raise

# ---------------------------------------------------------------------------
# Endpoint catalogue
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Endpoint:
    """Single endpoint participating in the benchmark."""

    name: str
    method: str
    path: str
    target_rps: int
    body: dict[str, Any] | None = None
    expected_status: tuple[int, ...] = (200,)
    # Status codes that should NOT count as failures even if they fall outside
    # the happy-path expectation — used for the phone OTP endpoint which
    # legitimately returns 400 with ``sms_provider_not_configured`` in dev.
    soft_ok_status: tuple[int, ...] = ()


ENDPOINTS: tuple[Endpoint, ...] = (
    Endpoint(
        name="health",
        method="GET",
        path="/api/health",
        target_rps=1000,
    ),
    Endpoint(
        name="oidc-discovery",
        method="GET",
        path="/.well-known/openid-configuration",
        target_rps=500,
    ),
    Endpoint(
        name="mfa-setup",
        method="POST",
        path="/api/v1/auth/mfa/setup",
        target_rps=200,
        body={"account_name": "bench@md-chat.eu"},
    ),
    Endpoint(
        name="phone-send-code",
        method="POST",
        path="/api/v1/auth/phone/send-code",
        target_rps=100,
        body={
            "phone_number": "60000000",
            "country_code": "MD",
            "user_id": "bench-user",
        },
        # Without INFOBIP_API_KEY the route returns 400 sms_provider_not_configured.
        # We still want to count rps but treat it as a soft-ok.
        expected_status=(200,),
        soft_ok_status=(400,),
    ),
)


# ---------------------------------------------------------------------------
# Per-endpoint result aggregation
# ---------------------------------------------------------------------------


@dataclass
class EndpointResult:
    """Aggregated metrics collected by all workers for a single endpoint."""

    name: str
    method: str
    path: str
    target_rps: int
    total: int = 0
    success: int = 0
    soft_ok: int = 0
    errors: int = 0
    status_counts: Counter[int] = field(default_factory=Counter)
    error_counts: Counter[str] = field(default_factory=Counter)
    latencies_ms: list[float] = field(default_factory=list)

    def add_response(self, status: int, latency_ms: float, *, expected: tuple[int, ...], soft_ok: tuple[int, ...]) -> None:
        self.total += 1
        self.status_counts[status] += 1
        self.latencies_ms.append(latency_ms)
        if status in expected:
            self.success += 1
        elif status in soft_ok:
            self.soft_ok += 1
        else:
            self.errors += 1

    def add_exception(self, exc: BaseException) -> None:
        self.total += 1
        self.errors += 1
        self.error_counts[type(exc).__name__] += 1

    def percentile(self, p: float) -> float:
        if not self.latencies_ms:
            return float("nan")
        return _percentile(self.latencies_ms, p)

    def summary(self, duration_s: float) -> dict[str, Any]:
        ok_total = self.success + self.soft_ok
        return {
            "name": self.name,
            "method": self.method,
            "path": self.path,
            "target_rps": self.target_rps,
            "total": self.total,
            "success": self.success,
            "soft_ok": self.soft_ok,
            "errors": self.errors,
            "success_rate": (ok_total / self.total) if self.total else 0.0,
            "rps": (self.total / duration_s) if duration_s else 0.0,
            "p50_ms": self.percentile(50),
            "p95_ms": self.percentile(95),
            "p99_ms": self.percentile(99),
            "mean_ms": statistics.fmean(self.latencies_ms) if self.latencies_ms else float("nan"),
            "status_counts": dict(self.status_counts),
            "error_counts": dict(self.error_counts),
            "meets_target_rps": (self.total / duration_s) >= self.target_rps if duration_s else False,
        }


def _percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile — robust for highly-skewed latency samples."""
    if not values:
        return float("nan")
    sorted_v = sorted(values)
    k = max(0, min(len(sorted_v) - 1, math.ceil(pct / 100.0 * len(sorted_v)) - 1))
    return sorted_v[k]


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------


async def _worker(
    *,
    worker_id: int,
    client: httpx.AsyncClient,
    endpoint: Endpoint,
    deadline: float,
    result: EndpointResult,
) -> None:
    while time.monotonic() < deadline:
        started = time.perf_counter()
        try:
            if endpoint.method == "GET":
                response = await client.get(endpoint.path)
            else:
                response = await client.request(endpoint.method, endpoint.path, json=endpoint.body)
            elapsed_ms = (time.perf_counter() - started) * 1000
            result.add_response(
                response.status_code,
                elapsed_ms,
                expected=endpoint.expected_status,
                soft_ok=endpoint.soft_ok_status,
            )
        except (httpx.HTTPError, asyncio.TimeoutError) as exc:
            result.add_exception(exc)
            # Brief backoff so the worker pool does not hot-spin on a dead server.
            await asyncio.sleep(0.05)
    # The worker_id is unused but kept for future per-worker stats; reference it
    # to keep linters quiet.
    _ = worker_id


async def _run_endpoint(
    *,
    endpoint: Endpoint,
    base_url: str,
    workers: int,
    duration: float,
) -> EndpointResult:
    """Run ``workers`` concurrent coroutines against a single endpoint."""
    result = EndpointResult(
        name=endpoint.name,
        method=endpoint.method,
        path=endpoint.path,
        target_rps=endpoint.target_rps,
    )
    timeout = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=10.0)
    limits = httpx.Limits(max_connections=max(workers * 2, 100), max_keepalive_connections=workers)
    deadline = time.monotonic() + duration
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout, limits=limits, http2=False) as client:
        await asyncio.gather(
            *(
                _worker(
                    worker_id=i,
                    client=client,
                    endpoint=endpoint,
                    deadline=deadline,
                    result=result,
                )
                for i in range(workers)
            )
        )
    return result


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _format_table(summaries: list[dict[str, Any]]) -> str:
    """Build a fixed-width human-readable table."""
    header = (
        f"{'endpoint':<22}"
        f"{'total':>8}"
        f"{'rps':>10}"
        f"{'target':>8}"
        f"{'ok%':>7}"
        f"{'p50':>8}"
        f"{'p95':>8}"
        f"{'p99':>8}"
        f"{'pass':>6}"
    )
    lines = [header, "-" * len(header)]
    for s in summaries:
        ok_pct = s["success_rate"] * 100
        passed = "yes" if s["meets_target_rps"] else "no"
        lines.append(
            f"{s['name']:<22}"
            f"{s['total']:>8}"
            f"{s['rps']:>10.1f}"
            f"{s['target_rps']:>8}"
            f"{ok_pct:>6.1f}%"
            f"{s['p50_ms']:>7.1f}m"
            f"{s['p95_ms']:>7.1f}m"
            f"{s['p99_ms']:>7.1f}m"
            f"{passed:>6}"
        )
    return "\n".join(lines)


def _format_status_block(summaries: list[dict[str, Any]]) -> str:
    lines = ["", "Status code distribution:"]
    for s in summaries:
        breakdown = ", ".join(f"{code}={n}" for code, n in sorted(s["status_counts"].items()))
        lines.append(f"  {s['name']:<22} {breakdown or '(none)'}")
        if s["error_counts"]:
            err = ", ".join(f"{k}={v}" for k, v in s["error_counts"].items())
            lines.append(f"  {'':<22}   transport errors: {err}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def _main(args: argparse.Namespace) -> int:
    base_url = args.base_url.rstrip("/")
    started_at = time.time()
    started_mono = time.monotonic()

    # Pre-flight: /api/health must respond, otherwise we bail early so we do
    # not waste minutes pelting a dead server.
    async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
        try:
            r = await client.get("/api/health")
        except httpx.HTTPError as exc:
            print(f"ERROR: pre-flight failed — could not reach {base_url}/api/health: {exc}", file=sys.stderr)
            return 2
        if r.status_code != 200:
            print(
                f"ERROR: pre-flight got status {r.status_code} from /api/health "
                f"(expected 200). Aborting benchmark.",
                file=sys.stderr,
            )
            return 2

    print(f"# Benchmark target : {base_url}")
    print(f"# Workers/endpoint : {args.workers}")
    print(f"# Duration/endpoint: {args.duration}s")
    print(f"# Endpoints        : {len(ENDPOINTS)}")
    print("")

    summaries: list[dict[str, Any]] = []
    for endpoint in ENDPOINTS:
        print(f"running {endpoint.name} ({endpoint.method} {endpoint.path}) ...", flush=True)
        result = await _run_endpoint(
            endpoint=endpoint,
            base_url=base_url,
            workers=args.workers,
            duration=args.duration,
        )
        summaries.append(result.summary(duration_s=args.duration))

    duration_total = time.monotonic() - started_mono
    print("")
    print(_format_table(summaries))
    print(_format_status_block(summaries))

    # JSON artefact.
    out_dir = Path(args.output_dir) if args.output_dir else Path.cwd()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"benchmark-{int(started_at)}.json"
    artefact = {
        "started_at": started_at,
        "base_url": base_url,
        "workers_per_endpoint": args.workers,
        "duration_per_endpoint_s": args.duration,
        "total_wall_time_s": duration_total,
        "endpoints": summaries,
    }
    out_path.write_text(json.dumps(artefact, indent=2, sort_keys=True))
    print(f"\nJSON report: {out_path}")

    # Exit code: 0 if every endpoint met its target rps AND success_rate >= 95%
    # (the soft-ok 400 from /phone/send-code counts toward success_rate).
    bad = [s for s in summaries if not s["meets_target_rps"] or s["success_rate"] < 0.95]
    if bad:
        names = ", ".join(b["name"] for b in bad)
        print(f"\nWARN: SLO violations on: {names}", file=sys.stderr)
        return 1
    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MD-Chat AI layer HTTP benchmark.")
    parser.add_argument("--duration", type=float, default=60.0, help="Seconds per endpoint (default 60).")
    parser.add_argument("--workers", type=int, default=50, help="Concurrent workers per endpoint (default 50).")
    parser.add_argument(
        "--base-url",
        default="http://localhost:5002",
        help="Base URL of the AI layer (default http://localhost:5002).",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for the JSON report (default: current working directory).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        return asyncio.run(_main(args))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130


# Make ``asdict`` discoverable for tests that may want to round-trip a result.
__all__ = ["Endpoint", "EndpointResult", "ENDPOINTS", "main", "asdict"]


if __name__ == "__main__":
    raise SystemExit(main())
