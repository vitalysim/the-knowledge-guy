#!/usr/bin/env bash
# =============================================================================
# measure_ingest.sh — Measure the real cost of a /book-to-skill ingest
#
# Two-step harness:
#   1) ./measure_ingest.sh --start
#        snapshots Anthropic subscription usage to /tmp/ingest-pre.json
#        and records a start epoch in /tmp/ingest-start-ts
#   2) (in a fresh Claude Code window) run /book-to-skill <book.pdf>
#   3) ./measure_ingest.sh --finish [session_id]
#        snapshots usage again, walks the session JSONL + every
#        agent-*.jsonl, and prints:
#          - wall-clock time
#          - subscription quota Δ (5-hour block %, 7-day window %)
#          - token totals (in / out / cache-read / cache-creation)
#          - per-stage split (main session vs Stage 1 subagents)
#          - equivalent-API-cost estimate at current Anthropic rates
#          - per-subagent breakdown + outlier
#
# If session_id is omitted on --finish, the script picks the most-recently
# -modified <uuid>.jsonl under the project's projects/ directory.
#
# Inspiration: vuln-hunters-v2/hunting_factory/statusline.sh (parse_agent,
# fetch_rate_limits).
# =============================================================================

set -uo pipefail

# Project dir override: set INGEST_PROJ_ROOT or pass --project <dir>
PROJECT_DIR_ENC="${INGEST_PROJECT_ENC:--Users-vitaly-MyPlace-projects-the-knowledge-guy}"
PROJ_ROOT="$HOME/.claude/projects/${PROJECT_DIR_ENC}"
PRE_FILE="/tmp/ingest-pre.json"
POST_FILE="/tmp/ingest-post.json"
TS_FILE="/tmp/ingest-start-ts"

# Anthropic rates ($ per 1M tokens) — Opus 4.7 default. Override via env.
RATE_IN="${RATE_IN:-15}"
RATE_OUT="${RATE_OUT:-75}"
RATE_CACHE_READ="${RATE_CACHE_READ:-1.5}"     # 10% of input
RATE_CACHE_WRITE="${RATE_CACHE_WRITE:-18.75}" # 1.25x input (5-min TTL)

# ── helpers ───────────────────────────────────────────────────────────────────
have() { command -v "$1" >/dev/null 2>&1; }

oauth_token() {
    local tok=""
    local creds="$HOME/.claude/.credentials.json"
    [ -f "$creds" ] && tok=$(jq -r '.claudeAiOauth.accessToken // empty' "$creds" 2>/dev/null)
    if [ -z "$tok" ] && have security; then
        tok=$(security find-generic-password -s "Claude Code-credentials" -w 2>/dev/null \
              | jq -r '.claudeAiOauth.accessToken // empty' 2>/dev/null)
    fi
    [ -n "$tok" ] && printf '%s' "$tok"
}

fetch_usage() {
    local out="$1"
    local tok; tok=$(oauth_token)
    if [ -z "$tok" ]; then
        echo "ERROR: no OAuth token found (~/.claude/.credentials.json or keychain)" >&2
        return 1
    fi
    local r
    r=$(curl -s --max-time 6 "https://api.anthropic.com/api/oauth/usage" \
        -H "Authorization: Bearer $tok" \
        -H "anthropic-beta: oauth-2025-04-20" 2>/dev/null)
    if ! echo "$r" | jq -e '.five_hour' >/dev/null 2>&1; then
        echo "ERROR: usage endpoint returned no .five_hour field" >&2
        echo "$r" | head -c 200 >&2; echo >&2
        return 1
    fi
    echo "$r" > "$out"
}

fmt_n() {  # 12345 → 12,345
    if have python3; then python3 -c "import sys;print(f'{int(sys.argv[1]):,}')" "$1"
    else printf '%d' "$1"; fi
}

# Sum input/output/cache_read/cache_creation across every assistant turn in a JSONL.
# Output: "in out cache_read cache_write"
sum_jsonl_usage() {
    local f="$1"
    [ -f "$f" ] || { echo "0 0 0 0"; return; }
    jq -r '
        select(.message.usage != null) |
        .message.usage |
        [(.input_tokens // 0),
         (.output_tokens // 0),
         (.cache_read_input_tokens // 0),
         (.cache_creation_input_tokens // 0)]
        | @tsv
    ' "$f" 2>/dev/null | awk '
        { in_t+=$1; out_t+=$2; cr+=$3; cw+=$4 }
        END { printf "%d %d %d %d\n", in_t+0, out_t+0, cr+0, cw+0 }
    '
}

# Slug of a subagent (from its meta.json or first JSONL line)
subagent_slug() {
    local f="$1"
    local meta="${f%.jsonl}.meta.json"
    if [ -f "$meta" ]; then
        jq -r '.slug // .agentType // "agent"' "$meta" 2>/dev/null
    else
        head -c 4096 "$f" | grep -o '"slug":"[^"]*"' | head -1 | cut -d'"' -f4
    fi
}

# Compute $ from a "in out cr cw" tuple
dollars() {
    read -r i o cr cw <<<"$1"
    awk -v i="$i" -v o="$o" -v cr="$cr" -v cw="$cw" \
        -v ri="$RATE_IN" -v ro="$RATE_OUT" -v rcr="$RATE_CACHE_READ" -v rcw="$RATE_CACHE_WRITE" \
        'BEGIN { printf "%.2f", (i*ri + o*ro + cr*rcr + cw*rcw)/1000000 }'
}

# ── commands ──────────────────────────────────────────────────────────────────

cmd_start() {
    if ! have jq;   then echo "need jq";   exit 1; fi
    if ! have curl; then echo "need curl"; exit 1; fi

    fetch_usage "$PRE_FILE" || exit 1
    date +%s > "$TS_FILE"

    local b5 b7
    b5=$(jq -r '.five_hour.utilization // 0' "$PRE_FILE")
    b7=$(jq -r '.seven_day.utilization // 0' "$PRE_FILE")

    cat <<EOF
✓ pre-snapshot saved to $PRE_FILE
  five_hour utilization:  ${b5}%
  seven_day utilization:  ${b7}%
  start ts:               $(date)

Now, in a FRESH Claude Code window inside this project, run:

  /book-to-skill "/Users/vitaly/Downloads/The Ghidra Book_2Ed_True/The Ghidra Book_2Ed_True.pdf"

When it completes, come back here and run:

  $0 --finish [session_id]

(session_id is optional — if omitted, the most-recently-modified
session JSONL since the start timestamp is used.)
EOF
}

cmd_finish() {
    # Parse optional --project <enc> flag, then session id
    while [ "${1:-}" = "--project" ]; do
        PROJECT_DIR_ENC="$2"
        PROJ_ROOT="$HOME/.claude/projects/${PROJECT_DIR_ENC}"
        shift 2
    done
    local sid="${1:-}"
    if [ ! -f "$PRE_FILE" ] || [ ! -f "$TS_FILE" ]; then
        echo "no pre-snapshot found — run --start first" >&2; exit 1
    fi
    local start_ts; start_ts=$(cat "$TS_FILE")
    local end_ts;   end_ts=$(date +%s)
    local elapsed=$(( end_ts - start_ts ))
    local elapsed_m=$(( elapsed / 60 ))
    local elapsed_s=$(( elapsed % 60 ))

    fetch_usage "$POST_FILE" || exit 1

    # Auto-detect session: most-recently-modified <uuid>.jsonl with mtime > start_ts
    if [ -z "$sid" ]; then
        sid=$(find "$PROJ_ROOT" -maxdepth 1 -name '*.jsonl' -type f \
              -newer "$TS_FILE" 2>/dev/null \
              | xargs -I{} stat -f '%m %N' {} 2>/dev/null \
              | sort -nr | head -1 | awk '{print $2}' | xargs basename 2>/dev/null \
              | sed 's/\.jsonl$//')
        if [ -z "$sid" ]; then
            echo "could not auto-detect session id — pass it explicitly" >&2
            exit 1
        fi
        echo "auto-detected session: $sid"
    fi

    local main_jsonl="${PROJ_ROOT}/${sid}.jsonl"
    local sub_dir="${PROJ_ROOT}/${sid}/subagents"

    [ -f "$main_jsonl" ] || { echo "main JSONL not found: $main_jsonl" >&2; exit 1; }

    # Quota delta
    local pre5 pre7 post5 post7
    pre5=$(jq -r '.five_hour.utilization // 0' "$PRE_FILE")
    pre7=$(jq -r '.seven_day.utilization // 0' "$PRE_FILE")
    post5=$(jq -r '.five_hour.utilization // 0' "$POST_FILE")
    post7=$(jq -r '.seven_day.utilization // 0' "$POST_FILE")
    local d5 d7
    d5=$(awk -v a="$post5" -v b="$pre5" 'BEGIN{printf "%.1f", a-b}')
    d7=$(awk -v a="$post7" -v b="$pre7" 'BEGIN{printf "%.1f", a-b}')

    # Main session totals
    local main_tup; main_tup=$(sum_jsonl_usage "$main_jsonl")

    # Subagent totals
    local n_agents=0
    local sub_in=0 sub_out=0 sub_cr=0 sub_cw=0
    declare -a agent_rows=()
    if [ -d "$sub_dir" ]; then
        while IFS= read -r -d '' af; do
            n_agents=$((n_agents+1))
            local tup; tup=$(sum_jsonl_usage "$af")
            read -r ai ao acr acw <<<"$tup"
            sub_in=$((  sub_in  + ai  ))
            sub_out=$(( sub_out + ao  ))
            sub_cr=$((  sub_cr  + acr ))
            sub_cw=$((  sub_cw  + acw ))
            local slug; slug=$(subagent_slug "$af")
            local total=$(( ai + ao + acr + acw ))
            agent_rows+=("$total|$slug|$ai|$ao|$acr|$acw")
        done < <(find "$sub_dir" -maxdepth 1 -name 'agent-*.jsonl' -print0 2>/dev/null)
    fi
    local sub_tup="$sub_in $sub_out $sub_cr $sub_cw"

    # Combined
    read -r mi mo mcr mcw <<<"$main_tup"
    local tot_in=$((  mi  + sub_in  ))
    local tot_out=$(( mo  + sub_out ))
    local tot_cr=$((  mcr + sub_cr  ))
    local tot_cw=$((  mcw + sub_cw  ))
    local tot_tup="$tot_in $tot_out $tot_cr $tot_cw"

    # Dollar estimates
    local d_main d_sub d_tot
    d_main=$(dollars "$main_tup")
    d_sub=$(dollars  "$sub_tup")
    d_tot=$(dollars  "$tot_tup")

    # Report
    cat <<EOF

═══════════════════════════════════════════════════════════════════
  /book-to-skill ingest — measurement report
═══════════════════════════════════════════════════════════════════
  session:        $sid
  wall-clock:     ${elapsed_m}m ${elapsed_s}s   ($(date -r "$start_ts" '+%H:%M:%S') → $(date -r "$end_ts" '+%H:%M:%S'))

  ── subscription quota burn ────────────────────────────────────
  5-hour block:   ${pre5}% → ${post5}%   Δ ${d5}%
  7-day window:   ${pre7}% → ${post7}%   Δ ${d7}%

  ── tokens ─────────────────────────────────────────────────────
                       input        output      cache-read    cache-write
  main session     $(printf '%12s %12s %12s %12s\n' "$(fmt_n $mi)" "$(fmt_n $mo)" "$(fmt_n $mcr)" "$(fmt_n $mcw)")
  subagents (${n_agents})$(printf '%12s %12s %12s %12s\n' "$(fmt_n $sub_in)" "$(fmt_n $sub_out)" "$(fmt_n $sub_cr)" "$(fmt_n $sub_cw)")
  ─────────────────────────────────────────────────────────────
  TOTAL           $(printf '%12s %12s %12s %12s\n' "$(fmt_n $tot_in)" "$(fmt_n $tot_out)" "$(fmt_n $tot_cr)" "$(fmt_n $tot_cw)")

  ── equivalent API cost ────────────────────────────────────────
  (rates: in=\$${RATE_IN}/M  out=\$${RATE_OUT}/M  cache_read=\$${RATE_CACHE_READ}/M  cache_write=\$${RATE_CACHE_WRITE}/M)
  main session:   \$${d_main}
  subagents:      \$${d_sub}
  TOTAL:          \$${d_tot}

EOF

    if [ "$n_agents" -gt 0 ]; then
        echo "  ── per-subagent breakdown (top 10 by total tokens) ────────────"
        printf '  %-30s %12s %12s %12s %12s\n' "slug" "input" "output" "cache-r" "cache-w"
        printf '%s\n' "${agent_rows[@]}" \
          | sort -t'|' -k1,1 -nr | head -10 \
          | while IFS='|' read -r _tot slug ai ao acr acw; do
                printf '  %-30s %12s %12s %12s %12s\n' \
                  "${slug:0:30}" "$(fmt_n $ai)" "$(fmt_n $ao)" "$(fmt_n $acr)" "$(fmt_n $acw)"
            done
        echo
    fi

    cat <<EOF
  ── linkedin-ready summary ─────────────────────────────────────
  Ghidra Book 2nd Ed (635pp, ~17MB PDF):
    • wall-clock: ${elapsed_m} min
    • equivalent API cost: \$${d_tot} (Opus rates)
    • subscription burn:   ${d5}% of a 5-hour block,
                           ${d7}% of the weekly window
    • ${n_agents} Stage-1 subagents spawned
═══════════════════════════════════════════════════════════════════
EOF
}

# ── main ──────────────────────────────────────────────────────────────────────
case "${1:-}" in
    --start)   cmd_start ;;
    --finish)  shift; cmd_finish "${1:-}" ;;
    *)
        cat <<EOF
usage:
  $0 --start              # snapshot pre-ingest subscription usage
  $0 --finish [session]   # snapshot post-ingest, emit measurement report

env overrides:
  RATE_IN, RATE_OUT, RATE_CACHE_READ, RATE_CACHE_WRITE   (\$/M tokens)
  default = Opus 4.7 rates (\$15 / \$75 / \$1.5 / \$18.75)
EOF
        exit 1 ;;
esac
