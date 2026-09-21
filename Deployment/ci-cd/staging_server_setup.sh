#!/usr/bin/env bash
# Phoneme SDLC SOP Section 8.3 — Staging Server Setup (Teamora / HR Management)
# Target: phoneme@10.100.60.119
#
# HOW TO RUN THIS:
# This script cannot be run by Claude — it has no network path to this
# private (10.x) address, and typing the server password into an SSH
# session isn't something Claude does under any circumstances. Copy this
# file to the server, or paste it into a terminal already logged into
# phoneme@10.100.60.119, and run it there (as root, or with sudo).
#
# WHAT THIS DOES:
#   0. Detects the OS's package manager (apt-get/dnf/yum/apk/zypper) and
#      installs curl automatically if it's missing — some minimal base
#      images (this one included) don't ship curl by default.
#   1. Adds the Claude-generated deploy public key to this server's
#      authorized_keys, so future automation uses key auth, not the
#      shared password.
#   2. Creates /home/projects as the convention for where deployed app
#      code/repo clones live (see note below — this is NOT Coolify's own
#      data directory, which cannot be relocated).
#   3. Installs Coolify using its official installer (data stored at its
#      fixed location, /data/coolify — no supported flag to move this).
#
# LOGGING:
# Every run's full console output (this script's own steps AND the
# Coolify installer's own step-by-step output) is captured to a
# timestamped log file under /home/projects/logs/, in addition to being
# shown on screen as usual. If a run fails partway, that log file is the
# first place to look — see the "Run log" line it prints near the top,
# and the "FAILED" trap message at the bottom on error. Coolify's own
# installer additionally keeps its own log under /data/coolify/source/
# (path printed at the end of Step 3) — that one covers only the
# Coolify-installer portion, not Steps 0-2 of this script.
#
# IMPORTANT — read before running:
# Coolify's install script hardcodes its own data directory to
# /data/coolify; there is no supported way to relocate it (confirmed
# against current docs and an upstream GitHub issue closed "not planned").
# /home/projects is therefore set up here as a separate, plain directory
# for anything outside Coolify's own management — e.g. manually cloned
# repos, scratch build artifacts, or a future non-Coolify service — NOT
# as Coolify's storage root. Coolify itself will still live at
# /data/coolify regardless.

set -uo pipefail

# ---------------------------------------------------------------------------
# Logging setup: mirror all output (stdout + stderr) to a timestamped log
# file, so the run can be reviewed or debugged after the fact, without
# changing anything that's printed to the terminal itself.
# ---------------------------------------------------------------------------
LOG_DIR="/home/projects/logs"
if ! mkdir -p "$LOG_DIR" 2>/dev/null; then
  LOG_DIR="$HOME/staging_setup_logs"
  mkdir -p "$LOG_DIR"
fi
RUN_STAMP="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="$LOG_DIR/staging_server_setup_${RUN_STAMP}.log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "Run log: $LOG_FILE"
echo "Run started: $(date -Is 2>/dev/null || date)"

on_error() {
  local exit_code=$?
  local line_no=$1
  echo ""
  echo "== FAILED =="
  echo "Script exited with status $exit_code at line $line_no."
  echo "Full output of this run was saved to: $LOG_FILE"
  echo "If Step 3 (Coolify install) had already started, also check its own"
  echo "log under /data/coolify/source/installation-*.log or upgrade-*.log"
  echo "for more detail on what Coolify itself was doing at the time."
  exit "$exit_code"
}
trap 'on_error $LINENO' ERR
set -e

echo "== Step 0: Check environment and install missing dependencies (curl, ca-certificates) =="
REQUIRED_CMDS="curl ca-certificates"

install_pkgs() {
  # $@ = list of package names to install, appropriate to the detected package manager
  if command -v apt-get >/dev/null 2>&1; then
    echo "Detected apt-get (Debian/Ubuntu). Installing: $*"
    apt-get update -y
    apt-get install -y "$@"
  elif command -v dnf >/dev/null 2>&1; then
    echo "Detected dnf (Fedora/RHEL 8+). Installing: $*"
    dnf install -y "$@"
  elif command -v yum >/dev/null 2>&1; then
    echo "Detected yum (RHEL/CentOS). Installing: $*"
    yum install -y "$@"
  elif command -v apk >/dev/null 2>&1; then
    echo "Detected apk (Alpine). Installing: $*"
    apk add --no-cache "$@"
  elif command -v zypper >/dev/null 2>&1; then
    echo "Detected zypper (openSUSE). Installing: $*"
    zypper --non-interactive install "$@"
  else
    echo "ERROR: No supported package manager found (looked for apt-get, dnf, yum, apk, zypper)."
    echo "Install curl manually, then re-run this script."
    exit 1
  fi
}

# Run installs as root (directly if we already are root, else via sudo if available)
as_root() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    echo "ERROR: not root and no sudo available — cannot install packages."
    exit 1
  fi
}

if ! command -v curl >/dev/null 2>&1; then
  echo "curl not found — installing it now."
  as_root install_pkgs curl ca-certificates
else
  echo "curl already present: $(command -v curl)"
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "ERROR: curl install attempted but curl is still not on PATH. Aborting."
  exit 1
fi
echo "Dependency check complete."

echo "== Step 1: Add deploy public key for key-based SSH access =="
mkdir -p ~/.ssh
chmod 700 ~/.ssh
DEPLOY_PUBKEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAudqRNIuS8b9a7k1uE0Bj+CQA2YaZlkKvzuPYAabdJj phoneme-staging-deploy"
grep -qxF "$DEPLOY_PUBKEY" ~/.ssh/authorized_keys 2>/dev/null || echo "$DEPLOY_PUBKEY" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
echo "Public key added. Once you've confirmed key-based login works, consider"
echo "disabling PasswordAuthentication in /etc/ssh/sshd_config and rotating the"
echo "shared password (it was passed in plain text over chat, which is worth"
echo "treating as no longer secret)."

echo "== Step 2: Create /home/projects (app-code convention, not Coolify's data dir) =="
as_root mkdir -p /home/projects
as_root chown "$(whoami)":"$(whoami)" /home/projects
echo "/home/projects ready."

echo "== Step 3: Install Coolify =="
echo "Requires: 2+ CPU cores, 2GB+ RAM, 10GB+ free disk, 64-bit Linux. Docker is"
echo "installed automatically by this script if not already present."
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | as_root bash

echo ""
echo "== Done =="
echo "Coolify's dashboard will be reachable at: http://10.100.60.119:8000"
echo "Finish setup there: create the admin account, then follow"
echo "Deployment/ci-cd/COOLIFY_SETUP.md (Section 3 onward) to connect the"
echo "GitHub repo and create the Staging application."
echo ""
echo "Full log of this run saved to: $LOG_FILE"
echo "(Coolify's own installer log, if Step 3 ran, is also under /data/coolify/source/)"
