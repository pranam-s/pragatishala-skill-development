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
  for candidate in "$SCRIPT_DIR/../backend/.venv/Scripts/python.exe" "$SCRIPT_DIR/../backend/.venv/bin/python"; do
    [ -x "$candidate" ] && PYTHON="$candidate" && break
  done
fi

fail() { echo "FAIL: $*" >&2; exit 1; }
json() { "$PYTHON" -c "import sys, json; print(json.load(sys.stdin)$1)"; }
status_of() { curl -s -o /dev/null -w "%{http_code}" "$@"; }

echo "== healthz =="
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
ASSESSMENT_ID=$(printf '%s' "$RESULT" | json "['id']")

echo "== learning path =="
curl -sf -X POST "$BASE/learning-paths/generate" -H "$AUTH" \
  -H "Content-Type: application/json" -d '{}' | json "['content']['modules'][0]['title']" >/dev/null || fail "learning path"

echo "== resume =="
RESUME=$(curl -sf -X POST "$BASE/resumes/generate" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"target_role":"Data Analyst","skills":["Python","SQL"],"experience_text":"Analyst at Acme\n- built dashboards"}')
RESUME_ID=$(printf '%s' "$RESUME" | json "['id']")

echo "   resume PATCH renames it"
curl -sf -X PATCH "$BASE/resumes/$RESUME_ID" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"title":"Smoke Renamed Resume"}' | json "['title']" | grep -q "Smoke Renamed" || fail "resume PATCH"

echo "   another user cannot read the assessment (expect 404)"
EMAIL2="smoke-second-$(date +%s)@example.com"
curl -sf -X POST "$BASE/auth/register" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL2\",\"password\":\"$PASSWORD\",\"full_name\":\"Second User\"}" >/dev/null
TOKENS2=$(curl -sf -X POST "$BASE/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$EMAIL2&password=$PASSWORD")
AUTH2="Authorization: Bearer $(printf '%s' "$TOKENS2" | json "['access_token']")"
[ "$(status_of "$BASE/assessments/$ASSESSMENT_ID" -H "$AUTH2")" = "404" ] || fail "ownership boundary"

echo "== profile PATCH =="
curl -sf -X PATCH "$BASE/users/me" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"full_name":"Smoke Tester Renamed"}' | json "['full_name']" | grep -q "Renamed" || fail "profile PATCH"

echo "== SSE =="
[ "$(status_of "$BASE/events")" = "401" ] || fail "SSE without token should be 401"
SSE_META=$(curl -s -o /dev/null -w "%{http_code} %{content_type}" -m 2 -H "$AUTH" "$BASE/events" || true)
printf '%s' "$SSE_META" | grep -q "^200 text/event-stream" || fail "SSE stream ($SSE_META)"

echo "== market insights =="
curl -sf "$BASE/market/insights?role=Data%20Analyst" -H "$AUTH" \
  | json "['insights']['demand_level']" | grep -qE '^(low|moderate|high|very high)$' || fail "market"

echo "== refresh =="
curl -sf -X POST "$BASE/auth/refresh" -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH\"}" | json "['access_token']" >/dev/null || fail "refresh"

echo
echo "E2E smoke: ALL CHECKS PASSED"
