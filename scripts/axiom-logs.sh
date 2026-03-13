#!/usr/bin/env bash
set -euo pipefail

# Query Railway logs via Axiom — reliable alternative to `railway logs`
#
# Usage:
#   ./scripts/axiom-logs.sh                  # Last 15 min, all logs
#   ./scripts/axiom-logs.sh 60              # Last 60 min
#   ./scripts/axiom-logs.sh 30 error        # Last 30 min, errors only
#   ./scripts/axiom-logs.sh 5 "" webhook    # Last 5 min, filter by keyword

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Load token from .env
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    AXIOM_QUERY_TOKEN="${AXIOM_QUERY_TOKEN:-$(grep '^AXIOM_QUERY_TOKEN=' "$SCRIPT_DIR/.env" 2>/dev/null | cut -d= -f2 || true)}"
    AXIOM_DATASET="${AXIOM_DATASET:-$(grep '^AXIOM_DATASET=' "$SCRIPT_DIR/.env" 2>/dev/null | cut -d= -f2 || true)}"
fi

AXIOM_QUERY_TOKEN="${AXIOM_QUERY_TOKEN:-}"
AXIOM_DATASET="${AXIOM_DATASET:-railway-logs}"

if [[ -z "$AXIOM_QUERY_TOKEN" ]]; then
    echo "Error: AXIOM_QUERY_TOKEN not set. Add it to .env or export it." >&2
    exit 1
fi

MINUTES="${1:-15}"
SEVERITY="${2:-}"
KEYWORD="${3:-}"
LIMIT="${4:-100}"

# Build APL query
APL="['${AXIOM_DATASET}'] | order by _time desc"

if [[ -n "$SEVERITY" ]]; then
    APL="['${AXIOM_DATASET}'] | where data.severity == \"${SEVERITY}\" | order by _time desc"
fi

if [[ -n "$KEYWORD" ]]; then
    APL="${APL} | where data.message contains \"${KEYWORD}\""
fi

APL="${APL} | limit ${LIMIT}"

# Query Axiom
RESPONSE=$(curl -s \
    -H "Authorization: Bearer ${AXIOM_QUERY_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"apl\":$(printf '%s' "$APL" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')}" \
    'https://api.axiom.co/v1/datasets/_apl?format=legacy')

# Check for errors
if echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if 'matches' in d else 1)" 2>/dev/null; then
    echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
matches = data.get('matches', [])
if not matches:
    print('No logs found in the last ${MINUTES} minutes.')
    sys.exit(0)
for m in reversed(matches):
    ts = m['_time'][11:19]
    d = m.get('data', {})
    sev = d.get('severity', '?')
    msg = d.get('message', '')
    # Color by severity
    if sev == 'error':
        print(f'\033[31m{ts} [{sev:5s}]\033[0m {msg}')
    elif 'WARNING' in msg:
        print(f'\033[33m{ts} [{sev:5s}]\033[0m {msg}')
    else:
        print(f'{ts} [{sev:5s}] {msg}')
"
else
    echo "Error querying Axiom:" >&2
    echo "$RESPONSE" >&2
    exit 1
fi
