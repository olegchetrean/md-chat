#!/usr/bin/env bash
# MD-Chat AI layer smoke test.
#
# Boots the Flask app on a free-ish dev port, hits 8 endpoints, verifies
# each returns the expected status code (and where appropriate, the expected
# JSON error code). Kills the app on exit.
#
# Dependencies: bash, curl, jq, python (>=3.11) in the active virtualenv.
# License: Apache-2.0

set -u
set -o pipefail

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_LAYER_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PORT="${SMOKE_PORT:-5099}"
BASE_URL="http://127.0.0.1:${PORT}"
BOOT_TIMEOUT="${SMOKE_BOOT_TIMEOUT:-30}"
LOG_FILE="$(mktemp -t md-chat-smoke.XXXXXX.log)"
PID_FILE="$(mktemp -t md-chat-smoke.XXXXXX.pid)"

# ANSI colours, disabled when not on a TTY.
if [[ -t 1 ]]; then
    GREEN=$'\033[0;32m'
    RED=$'\033[0;31m'
    YELLOW=$'\033[0;33m'
    DIM=$'\033[2m'
    RESET=$'\033[0m'
else
    GREEN=""
    RED=""
    YELLOW=""
    DIM=""
    RESET=""
fi

PASS=0
FAIL=0
FAILED_CHECKS=()

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

note()  { printf '%s\n' "${DIM}--- $* ---${RESET}"; }
ok()    { printf '%s\n' "  ${GREEN}\xE2\x9C\x93${RESET} $*"; PASS=$((PASS + 1)); }
fail()  {
    printf '%s\n' "  ${RED}\xE2\x9C\x97${RESET} $*"
    FAIL=$((FAIL + 1))
    FAILED_CHECKS+=("$*")
}
warn()  { printf '%s\n' "  ${YELLOW}!${RESET} $*"; }

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

cleanup() {
    local pid
    if [[ -f "${PID_FILE}" ]]; then
        pid="$(cat "${PID_FILE}" 2>/dev/null || true)"
        if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
            kill "${pid}" 2>/dev/null || true
            # Give it a moment to drain, then SIGKILL if still alive.
            for _ in 1 2 3 4 5; do
                if ! kill -0 "${pid}" 2>/dev/null; then
                    break
                fi
                sleep 0.5
            done
            kill -9 "${pid}" 2>/dev/null || true
        fi
    fi
    rm -f "${PID_FILE}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------

note "Booting Flask app on ${BASE_URL}"
cd "${AI_LAYER_DIR}" || { echo "cannot cd ${AI_LAYER_DIR}" >&2; exit 1; }

# Force unconfigured state so /api/ready returns 503 as documented.
# (Tests below expect 503 with reason=config_incomplete.)
unset NEO4J_PASSWORD ROUTER_API_KEY INFOBIP_API_KEY EEVIDENCE_INTERNAL_TOKEN
export AI_LAYER_PORT="${PORT}"
export NODE_ENV="development"
export LOG_LEVEL="WARNING"

# Prefer the project venv if active; otherwise rely on python on PATH.
PYBIN="${PYTHON:-python3}"
if [[ -x "${AI_LAYER_DIR}/.venv/bin/python" ]] && [[ -z "${VIRTUAL_ENV:-}" ]]; then
    PYBIN="${AI_LAYER_DIR}/.venv/bin/python"
fi

PYTHONPATH="${AI_LAYER_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}" \
    "${PYBIN}" -m md_chat_ai.wsgi >"${LOG_FILE}" 2>&1 &
echo "$!" >"${PID_FILE}"

# Wait for /api/health.
note "Waiting up to ${BOOT_TIMEOUT}s for /api/health"
waited=0
booted=0
while (( waited < BOOT_TIMEOUT )); do
    if curl -fsS -o /dev/null "${BASE_URL}/api/health"; then
        booted=1
        break
    fi
    sleep 0.5
    waited=$((waited + 1))
done

if (( booted == 0 )); then
    echo "${RED}Flask app did not become healthy within ${BOOT_TIMEOUT}s.${RESET}" >&2
    echo "--- last 50 lines of server log (${LOG_FILE}) ---" >&2
    tail -n 50 "${LOG_FILE}" >&2 || true
    exit 2
fi
ok "app responded on /api/health"

# ---------------------------------------------------------------------------
# Helpers — assert HTTP status and optional JSON expr
# ---------------------------------------------------------------------------

# assert_status <label> <method> <path> <expected_status> [<body-json>] [<jq-filter> <expected>]
assert_status() {
    local label="$1"
    local method="$2"
    local path="$3"
    local expected="$4"
    local body="${5:-}"
    local jq_filter="${6:-}"
    local jq_expected="${7:-}"

    local out
    out="$(mktemp -t md-chat-smoke.body.XXXXXX)"
    local status
    if [[ "${method}" == "GET" ]]; then
        status="$(curl -s -o "${out}" -w '%{http_code}' "${BASE_URL}${path}")"
    else
        status="$(curl -s -o "${out}" -w '%{http_code}' \
            -X "${method}" \
            -H 'Content-Type: application/json' \
            --data "${body:-{}}" \
            "${BASE_URL}${path}")"
    fi

    if [[ "${status}" != "${expected}" ]]; then
        fail "${label}: status=${status} expected=${expected} (body: $(head -c 200 "${out}"))"
        rm -f "${out}"
        return
    fi

    if [[ -n "${jq_filter}" ]]; then
        local actual
        actual="$(jq -r "${jq_filter}" "${out}" 2>/dev/null || true)"
        if [[ "${actual}" != "${jq_expected}" ]]; then
            fail "${label}: status=${status} ok; jq ${jq_filter} -> '${actual}' expected '${jq_expected}'"
            rm -f "${out}"
            return
        fi
    fi
    ok "${label}  (${status})"
    rm -f "${out}"
}

# ---------------------------------------------------------------------------
# Checks (8 endpoints)
# ---------------------------------------------------------------------------

note "Running 8 endpoint checks"

# 1. GET /api/health -> 200
assert_status "GET /api/health" GET "/api/health" 200 "" ".status" "healthy"

# 2. GET /api/ready -> 503 with reason=config_incomplete
assert_status "GET /api/ready" GET "/api/ready" 503 "" ".reason" "config_incomplete"

# 3. GET /.well-known/openid-configuration -> 200
assert_status "GET /.well-known/openid-configuration" GET "/.well-known/openid-configuration" 200

# 4. POST /api/v1/auth/mfa/setup -> 200 ok=true
assert_status "POST /api/v1/auth/mfa/setup" POST "/api/v1/auth/mfa/setup" 200 \
    '{"account_name": "smoke@md-chat.eu"}' ".ok" "true"

# 5. POST /api/v1/auth/phone/send-code -> 200 with ok=false error=sms_provider_not_configured
#    Implementation note: the route returns HTTP 200 when the SMS provider is
#    intentionally absent in dev (config-gate, not a server error); body carries
#    ok=false + error code. If the future contract switches to a non-2xx code,
#    update this check together with the route.
assert_status "POST /api/v1/auth/phone/send-code" POST "/api/v1/auth/phone/send-code" 200 \
    '{"phone_number":"60000000","country_code":"MD","user_id":"smoke-user"}' \
    ".error" "sms_provider_not_configured"

# 6. POST /api/v1/legal/eevidence/submit (bad body) -> 422
assert_status "POST /api/v1/legal/eevidence/submit (bad body)" POST \
    "/api/v1/legal/eevidence/submit" 422 \
    '{"foo":"bar"}' ".error" "validation_failed"

# 7. POST /api/v1/legal/eevidence/submit (good body) -> 201
GOOD_BODY='{
    "issuing_authority":"Tribunalul Chisinau",
    "issuing_authority_type":"judicial",
    "member_state":"RO",
    "target_identifier":"@test:md-chat.eu",
    "requested_data_category":"subscriber",
    "legal_basis":"Art. 145 CPP Romania",
    "case_reference":"SMOKE-001",
    "contact_email":"ops@md-chat.eu"
}'
assert_status "POST /api/v1/legal/eevidence/submit (good body)" POST \
    "/api/v1/legal/eevidence/submit" 201 "${GOOD_BODY}"

# 8. GET /oidc/jwks.json -> 200
assert_status "GET /oidc/jwks.json" GET "/oidc/jwks.json" 200

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

printf '\n'
note "Summary"
printf '  passed: %s%d%s   failed: %s%d%s\n' "${GREEN}" "${PASS}" "${RESET}" "${RED}" "${FAIL}" "${RESET}"

if (( FAIL > 0 )); then
    printf '\n%sFailed checks:%s\n' "${RED}" "${RESET}"
    for f in "${FAILED_CHECKS[@]}"; do
        printf '  - %s\n' "${f}"
    done
    printf '\nServer log: %s\n' "${LOG_FILE}"
    exit 1
fi

# On success we delete the log to avoid leaving artefacts behind.
rm -f "${LOG_FILE}" 2>/dev/null || true
exit 0
