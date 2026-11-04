#!/usr/bin/env bash
set -euo pipefail

publisher="${PUBLISHER:-./publisher}"
count="${POSTS_PER_RUN:-10}"
branch="${DEFAULT_BRANCH:?DEFAULT_BRANCH is required}"
delay="${PUBLISH_DELAY_SECONDS:-1}"
if [[ ! "$count" =~ ^(0|[1-9][0-9]*)$ ]] || (( count > 1000 )); then
  echo 'POSTS_PER_RUN must be between 0 and 1000.' >&2
  exit 1
fi
if [[ ! "$delay" =~ ^(0|[1-9][0-9]*)$ ]] || (( delay > 60 )); then
  echo 'PUBLISH_DELAY_SECONDS must be between 0 and 60.' >&2
  exit 1
fi
if (( count == 0 )); then
  echo 'Catch-up target is already fulfilled.'
  exit 0
fi

git config user.name 'rza-publisher[bot]'
git config user.email 'rza-publisher@users.noreply.github.com'

save_changes() {
  git add posts/lessons
  if [[ -f .publisher-state.json ]]; then
    git add .publisher-state.json
  fi
  if ! git diff --cached --quiet; then
    git commit -m "$1"
    git push origin "HEAD:$branch"
  fi
}

save_changes 'Save prepared RZA lessons'
for (( number=1; number<=count; number++ )); do
  "$publisher" -reserve
  save_changes "Reserve RZA lesson $number of $count"
  "$publisher" -deliver
  save_changes "Save RZA delivery $number of $count"
  if (( number < count && delay > 0 )); then sleep "$delay"; fi
done
