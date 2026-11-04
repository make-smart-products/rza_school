#!/usr/bin/env bash
set -euo pipefail

export RUN_LOG="$(mktemp)"
export PUSH_COUNT="$(mktemp)"
trap 'rm -f -- "$RUN_LOG" "$PUSH_COUNT"' EXIT
export DEFAULT_BRANCH=main POSTS_PER_RUN=10 PUBLISHER=mock_publisher

mock_publisher() {
  local action="${1#-}"
  echo "$action" >> "$RUN_LOG"
  if [[ "$action" == deliver && "${FAIL_DELIVERY:-0}" != 0 ]]; then
    local delivered
    delivered=$(awk '$0 == "deliver" { n++ } END { print n+0 }' "$RUN_LOG")
    if [[ "$delivered" == "$FAIL_DELIVERY" ]]; then return 17; fi
  fi
}
git() {
  case "$1" in
    diff) return 1 ;;
    push)
      local pushes=0
      read -r pushes < "$PUSH_COUNT" || true
      pushes=$((pushes+1))
      echo "$pushes" > "$PUSH_COUNT"
      echo push >> "$RUN_LOG"
      if [[ "$pushes" == "${FAIL_PUSH:-0}" ]]; then return 18; fi
      ;;
  esac
  return 0
}
export -f mock_publisher git

bash .github/scripts/publish-batch.sh
[[ $(awk '$0 == "deliver" { n++ } END { print n+0 }' "$RUN_LOG") == 10 ]]

: > "$RUN_LOG"; : > "$PUSH_COUNT"
if FAIL_DELIVERY=3 bash .github/scripts/publish-batch.sh; then
  echo 'Expected the third failed delivery to stop the batch.' >&2; exit 1
fi
[[ $(awk '$0 == "deliver" { n++ } END { print n+0 }' "$RUN_LOG") == 3 ]]
[[ $(awk '$0 == "reserve" { n++ } END { print n+0 }' "$RUN_LOG") == 3 ]]

: > "$RUN_LOG"; : > "$PUSH_COUNT"
if FAIL_PUSH=2 bash .github/scripts/publish-batch.sh; then
  echo 'Expected a failed reservation push to stop the batch.' >&2; exit 1
fi
[[ $(awk '$0 == "deliver" { n++ } END { print n+0 }' "$RUN_LOG") == 0 ]]
echo 'Batch checks passed: ten deliveries; stops after errors; persists reservation before sending.'
