#!/usr/bin/env bash
# Create the repo under the sincefirst org and push to it. PUBLIC -- see below.
#
# The token is never typed on a command line, never put in a remote URL that git
# would write into .git/config, and never printed. It is read from a file and
# handed to git over stdin by the credential helper below, the same shape as
# scripts/push-secrets.sh in the commercial apps.
#
# Usage:  bash scripts/push.sh
#
# One token per GitHub ACCOUNT. This repo's org lives under hongnhatnt0410,
# which is NOT the account the `gh` CLI on this machine is signed in as
# (feelthebeat113, which owns the thirty older orgs). Using `gh` here would
# quietly push to the wrong account or fail with a confusing 404.

set -euo pipefail
cd "$(dirname "$0")/.."

ORG="sincefirst"
REPO="sincefirst"
OWNER="hongnhatnt0410"
TOKEN_FILE="${GH_TOKEN_FILE:-$HOME/.gh-hongnhatnt0410.token}"

# EXPIRES 2026-09-19. The token was meant to be non-expiring -- GitHub's
# expiry menu reported the choice as taken and the form still read back
# "30 days", which is why the value is written down here rather than trusted.
# After that date this script fails with a 401 that looks like a wrong file.
TOKEN_EXPIRES="2026-09-19"

[ -f "$TOKEN_FILE" ] || {
  echo "missing $TOKEN_FILE" >&2
  echo "make a classic token at https://github.com/settings/tokens/new" >&2
  echo "  note: sincefirst push   expiry: no expiration   scope: repo" >&2
  echo "then:  echo 'ghp_...' > $TOKEN_FILE" >&2
  exit 1
}

TOKEN="$(tr -d '[:space:]' < "$TOKEN_FILE")"

# Check the token is alive and belongs to who we think, BEFORE anything is
# created. A 401 here is a dead token; a different login means the wrong file.
who=$(curl -sS -H "Authorization: Bearer $TOKEN" https://api.github.com/user \
      | python -c "import sys,json; print(json.load(sys.stdin).get('login','?'))")
if [ "$who" != "$OWNER" ]; then
  echo "that token belongs to '$who', not '$OWNER' - wrong file?" >&2
  exit 1
fi
echo "token ok, account $who"

# Say it out loud while it is still true, rather than after it stops being.
today=$(date +%Y-%m-%d)
if [ "$today" \> "$TOKEN_EXPIRES" ]; then
  echo "note: the token was due to expire $TOKEN_EXPIRES but still works" >&2
else
  echo "token expires $TOKEN_EXPIRES"
fi

# Create the repo. PUBLIC for a Personal app, and that is not a slip.
#
# The playbook line "repo private, Website URL = the live app" is the COMMERCIAL
# rule: those have a domain to point at. A Personal app here is a command-line
# tool with no site, so the Website URL on the Etsy form IS this repo -- and a
# private one hands the reviewer a 404.
#
# Measured 2026-08-20: all eight Personal apps approved the day before are
# public (brackenway/collectr, kilnrow/palette, coldbeck/howlong,
# pennyfold/postedfrom, fenwarrow/newdrop, thistlegate/giftlist,
# crookmill/price-ranges, quillbarrow/justthis), as are pigeon, thicket and
# mochi. The only private ones in the set -- filedunder, sidenote, onceover --
# are all REJECTED apps, made private after the fact.
code=$(curl -sS -o /dev/null -w "%{http_code}" \
       -H "Authorization: Bearer $TOKEN" "https://api.github.com/repos/$ORG/$REPO")
if [ "$code" = "404" ]; then
  curl -sS -X POST -H "Authorization: Bearer $TOKEN" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/orgs/$ORG/repos" \
    -d "{\"name\":\"$REPO\",\"private\":false,\"has_issues\":true,\"has_wiki\":false,\"auto_init\":false}" \
    | python -c "import sys,json; d=json.load(sys.stdin); print('created', d.get('full_name'), 'private=' + str(d.get('private')))"
elif [ "$code" = "200" ]; then
  echo "repo already exists, pushing to it"
else
  echo "unexpected $code asking about $ORG/$REPO" >&2
  exit 1
fi

# The remote carries no credential. Git asks the helper below for one, which
# reads the file -- so nothing lands in .git/config and nothing is in argv.
git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/$ORG/$REPO.git"

# The first version wrote the helper to a file under /tmp and passed the path.
# git.exe on Windows is a native binary and does not resolve an MSYS path like
# /tmp/tmp.XyZ, so it silently used no helper at all, pushed anonymously, and a
# PRIVATE repo answers that with "Repository not found" -- which reads exactly
# like a wrong org or a typo'd name and sent me looking in the wrong place.
#
# The `!` form makes git run the value as a shell command instead of looking for
# an executable, so there is no path to resolve. The token still never reaches
# argv: only the path of the file holding it does.
# `credential.helper=` with an EMPTY value first. Git ACCUMULATES helpers rather
# than replacing them, and this machine has `manager` set in the system gitconfig
# (C:/Program Files/Git/etc/gitconfig). That helper runs first, hands over the
# cached credential for github.com -- which belongs to feelthebeat113, an account
# with no access to this org -- and a private repo answers that with
# "Repository not found". The empty value resets the list so only ours is used.
git -c credential.helper= -c credential.helper='!f() { [ "$1" = get ] || exit 0; echo "username='"$OWNER"'"; echo "password=$(tr -d "[:space:]" < '"$TOKEN_FILE"')"; }; f' \
    push -u origin HEAD:main

echo
echo "pushed. https://github.com/$ORG/$REPO  (public -- it is the Website URL on the Etsy form)"
