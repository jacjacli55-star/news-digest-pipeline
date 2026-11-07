"""One-time authorization helper for Google Drive access.

It needs an OAuth Client JSON (desktop app) which you create once in Google
Cloud Console (see README). Saves a token that the pipeline reuses so the
08:00 job runs without prompting.

Usage:  python auth_drive.py
"""
from __future__ import annotations

import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))

import upload_drive  # noqa: E402


def main():
    with open(os.path.join(HERE, "config.yaml"), encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    oauth_file = cfg["drive"]["oauth_client_file"]
    if not (oauth_file and os.path.exists(oauth_file)):
        print("OAuth client file not found:", oauth_file)
        print("Create a Desktop OAuth Client and save it here (see README).")
        return 1
    upload_drive.ensure_auth(cfg)
    print("Auth OK. Token saved. The 08:00 job can now upload to Drive.")
    return 0


if __name__ == "__main__":
    sys.exit(main())