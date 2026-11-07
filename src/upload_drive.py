"""Upload the generated report to a Google Drive folder.

Authentication is resolved in this order:
  1. OAuth token saved in token_file (from a one-time `python auth_drive.py`,
     using an OAuth Client JSON you create — see README).
  2. OAuth flow triggered by auth_drive.py.
  3. Application Default Credentials (service account or gcloud ADC) + refresh
     -- but NOTE: Drive requires the 'https://www.googleapis.com/auth/drive'
     scope. If ADC does not carry it, only the OAuth path works. The README
     explains how to generate a Desktop OAuth client once.
"""
from __future__ import annotations

import json
import os

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def _load_oauth_creds(cfg):
    token_file = cfg["drive"].get("token_file")
    if not token_file or not os.path.exists(token_file):
        return None
    from google.oauth2.credentials import Credentials
    creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if creds and creds.valid:
        return creds
    return None


def _build_service():
    from googleapiclient.discovery import build
    return build("drive", "v3", cache_discovery=False)


def _creds_from_client_file(oauth_file, token_file):
    """Run the full OAuth flow using a downloaded OAuth Client JSON."""
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_secrets_file(oauth_file, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")
    os.makedirs(os.path.dirname(token_file), exist_ok=True)
    with open(token_file, "w") as f:
        f.write(creds.to_json())
    return creds


def find_or_create_folder(service, folder_name):
    q = (f"name = '{folder_name}' and mimeType = "
         "'application/vnd.google-apps.folder' and trashed = false")
    res = service.files().list(q=q, fields="files(id,name)").execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
    f = service.files().create(body=meta, fields="id").execute()
    return f["id"]


def upload_file(service, folder_name, file_path, mime="application/pdf"):
    folder_id = find_or_create_folder(service, folder_name)
    file_meta = {
        "name": os.path.basename(file_path),
        "parents": [folder_id],
    }
    from googleapiclient.http import MediaFileUpload
    media = MediaFileUpload(file_path, mimetype=mime, resumable=True)
    res = service.files().create(body=file_meta, media_body=media,
                                 fields="id,name,webViewLink,parents").execute()
    return res


def get_creds(cfg, reraise=True):
    try:
        import google.auth  # noqa
    except Exception as exc:
        if reraise:
            raise RuntimeError("google-auth not installed") from exc
        return None

    # 1) OAuth token
    creds = _load_oauth_creds(cfg)
    if creds:
        return creds

    # 2) OAuth client file → run flow (interactive)
    oauth_file = cfg["drive"].get("oauth_client_file")
    token_file = cfg["drive"].get("token_file")
    if oauth_file and os.path.exists(oauth_file) and token_file:
        print("-> No saved token; running interactive OAuth flow...")
        return _creds_from_client_file(oauth_file, token_file)

    # 3) Application Default Credentials (service account)
    if cfg["drive"].get("use_application_default"):
        try:
            from google.auth.transport.requests import Request
            creds, _ = google.auth.default(scopes=SCOPES)
            creds.refresh(Request())
            return creds
        except Exception as exc:
            print(f"-> ADC not usable for Drive: {exc}")

    if reraise:
        raise RuntimeError(
            "Could not authenticate to Google Drive. Run `python auth_drive.py` "
            "with an OAuth Client JSON (see README)."
        )
    return None


def ensure_auth(cfg):
    """Interactive helper for auth_drive.py."""
    service = _build_service()
    creds = get_creds(cfg, reraise=True)
    service = _build_service() if creds else None
    from google.auth.transport.requests import Request
    if creds and getattr(creds, "refresh_token", None):
        creds.refresh(Request())
    return service