#!/bin/zsh
# Daily News Digest — scheduled runner (invoked by launchd at 08:00).
# Uses absolute paths so it works in launchd's minimal environment.
set -euo pipefail

BASE="$(cd "$(dirname "$0")" && pwd)"
PY="$BASE/.venv/bin/python"
LOG_DIR="$BASE/logs"
mkdir -p "$LOG_DIR"
STAMP="$(date '+%Y-%m-%d')"
GIT="/usr/bin/git"
GIT_AUTH_NAME="jacjacli55-star"
GIT_AUTH_EMAIL="jacjacli55@users.noreply.github.com"

# 1) Generate the digest (fetch -> screen -> md + pdf).
#    NOTE: the Google Drive upload may fail until its one-time OAuth is set up;
#    that must never prevent the website from updating, so don't abort here.
cd "$BASE/src"
("$PY" run.py >> "$LOG_DIR/digest_$STAMP.log" 2>&1) || RC=$?
if [ -n "${RC:-}" ] && [ "$RC" -ne 0 ]; then
  echo "[warn] run.py finished with exit=$RC (Drive upload may be pending); continuing" >> "$LOG_DIR/digest_$STAMP.log"
  RC=""
fi

# 2) Rebuild the static news portal from the newest digest.
"$PY" build_site.py >> "$LOG_DIR/digest_$STAMP.log" 2>&1

# 3) Publish to GitHub Pages: replace the portal page and archive the day's
#    Markdown + PDF so the public site always reflects today.
SITE="$BASE/site/index.html"
GH="$BASE/gh-pages"
DIGESTS="$GH/digests"
mkdir -p "$DIGESTS"

cp "$SITE" "$GH/portal.html"
cp "$BASE/output"/DailyNewsDigest_"$STAMP".md "$DIGESTS/" 2>/dev/null || true
cp "$BASE/output"/DailyNewsDigest_"$STAMP".pdf "$DIGESTS/" 2>/dev/null || true

cd "$GH"
if [ -n "$(command -v git)" ] && git status --porcelain | grep -q .; then
  git add -A
  git -c user.name="$GIT_AUTH_NAME" -c user.email="$GIT_AUTH_EMAIL" \
      commit -q -m "Daily digest update $STAMP"
  "$GIT" push -q origin main
  echo "[publish] pushed Pages update for $STAMP" >> "$LOG_DIR/digest_$STAMP.log"
else
  echo "[publish] no changes to push for $STAMP" >> "$LOG_DIR/digest_$STAMP.log"
fi

# 4) Keep only the last 30 digest logs.
ls -1t "$LOG_DIR"/digest_*.log 2>/dev/null | tail -n +31 | xargs -r rm -f 2>/dev/null || true