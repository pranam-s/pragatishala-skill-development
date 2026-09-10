#!/usr/bin/env bash
# End-to-end smoke test against a RUNNING backend (default 127.0.0.1:8000).
# Prerequisites:
#   backend: uv run uvicorn app.main:app --port 8000
#   tools:   curl, python3 (or python) on PATH
set -euo pipefail

BASE="${1:-http://127.0.0.1:8000/api/v1}"
EMAIL="smoke-$(date +%s)@example.com"
PASSWORD="smoke-super-secret-1"
PYTHON="$(command -v python3 || command -v python || true)"
if [ -z "$PYTHON" ]; then
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
  for candidate in     "$SCRIPT_DIR/../backend/.venv/Scripts/python.exe"     "$SCRIPT_DIR/../backend/.venv/bin/python"; do
    [ -x "$candidate" ] && PYTHON="$candidate" && break
  done
fi

fail() { echo "FAIL: $*" >&2; exit 1; }
json() { "$PYTHON" -c "import sys, json; print(json.load(sys.stdin)$1)"; }

echo "== healthz =="
curl -sf "http://${BASE#*://}/../healthz" >/dev/null 2>&1 || true
curl -sf "${BASE%/api/v1}/healthz" | json "['status']" | grep -q ok || fail "healthz"

echo "== register ($EMAIL) =="
curl -sf -X POST "$BASE/auth/register" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"full_name\":\"Smoke Tester\",\"target_role\":\"Data Analyst\"}" \
  | json "['email']" | grep -q "$EMAIL" || fail "register"

echo "   duplicate register rejected (expect 409)"
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/auth/register" \
  -H "Content-Type: application/json" -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
[ "$CODE" = "409" ] || fail "duplicate register returned $CODE"

echo "== login =="
TOKENS=$(curl -sf -X POST "$BASE/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$EMAIL&password=$PASSWORD")
ACCESS=$(printf '%s' "$TOKENS" | json "['access_token']")
REFRESH=$(printf '%s' "$TOKENS" | json "['refresh_token']")
AUTH="Authorization: Bearer $ACCESS"

echo "== me =="
curl -sf "$BASE/users/me" -H "$AUTH" | json "['email']" | grep -q "$EMAIL" || fail "me"

echo "   unauthenticated me rejected (expect 401)"
CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/users/me")
[ "$CODE" = "401" ] || fail "unauthenticated me returned $CODE"

echo "== assessment =="
RESULT=$(curl -sf -X POST "$BASE/assessments" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"input_text":"I know Python and pandas, I use SQL daily at work and I am learning generative AI tools."}')
printf '%s' "$RESULT" | json "['result']['readiness_score']" | grep -qE '^[0-9]+$' || fail "assessment"
printf '%s' "$RESULT" | json "['result']['skills'][0]['name']" >/dev/null || fail "assessment skills"

echo "== learning path =="
curl -sf -X POST "$BASE/learning-paths/generate" -H "$AUTH" \
  -H "Content-Type: application/json" -d '{}' | json "['content']['modules'][0]['title']" >/dev/null || fail "learning path"

echo "== resume =="
curl -sf -X POST "$BASE/resumes/generate" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"target_role":"Data Analyst","skills":["Python","SQL"],"experience_text":"Analyst at Acme\n- built dashboards"}' \
  | json "['content']['headline']" >/dev/null || fail "resume"

echo "== market insights =="
curl -sf "$BASE/market/insights?role=Data%20Analyst" -H "$AUTH" \
  | json "['insights']['demand_level']" | grep -qE '^(low|moderate|high|very high)$' || fail "market"

echo "== refresh =="
curl -sf -X POST "$BASE/auth/refresh" -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH\"}" | json "['access_token']" >/dev/null || fail "refresh"

echo
echo "E2E smoke: ALL CHECKS PASSED"
