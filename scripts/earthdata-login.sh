#!/usr/bin/env bash
# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
# One-time NASA Earthdata Login. Run it in your own terminal: it asks for your
# username and password and stores them in ~/.netrc (never in this repo).
set -euo pipefail
umask 077  # files created here (~/.netrc) are readable by you only

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ! -f "$root/.venv/bin/activate" ]]; then
  echo "No .venv found. Run first: uv venv -p 3.12 .venv && uv pip install -r requirements-dev.txt" >&2
  exit 1
fi
# shellcheck disable=SC1091
source "$root/.venv/bin/activate"

# earthaccess asks for username/password on stdin, so stdin must be the terminal
# (a heredoc here would feed it EOF instead).
if [[ ! -t 0 ]]; then
  echo "Run this script in an interactive terminal: it prompts for your Earthdata username and password." >&2
  exit 1
fi

python -c '
import earthaccess

auth = earthaccess.login(strategy="interactive", persist=True)
if not auth.authenticated:
    raise SystemExit("Earthdata Login failed: check your username and password.")
'

netrc="${NETRC:-$HOME/.netrc}"
chmod 600 "$netrc"
echo "Earthdata Login OK. Credentials saved to $netrc (permissions 600)."
