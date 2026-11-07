"""Daily News Digest — orchestrator.

Fetches news across domains, screens for credibility, writes a Markdown +
PDF report, and uploads to Google Drive. Unverified items are routed to the
review queue (never into the auto-sent PDF).

Usage:  python run.py  [--no-upload] [--config config.yaml]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import fetch          # noqa: E402
import factcheck      # noqa: E402
import digest         # noqa: E402
import topdf          # noqa: E402
import upload_drive   # noqa: E402


def load_config(path):
    cfg_path = os.path.join(HERE, path)
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def write_review_queue(unverified, review_dir, date_str):
    os.makedirs(review_dir, exist_ok=True)
    md_path = os.path.join(review_dir, f"REVIEW_{date_str}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Manual review queue — {date_str}\n\n")
        f.write("These items were found in only one non-Tier-1 source and need "
                "a human fact-check before you publish them.\n\n")
        for a in sorted(unverified, key=lambda x: x.ts, reverse=True):
            f.write(f"- **{a.title}** — {a.source}\n  {a.link}\n  ({a.ts:%Y-%m-%d %H:%M} UTC)\n")
    csv_path = os.path.join(review_dir, f"REVIEW_{date_str}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as c:
        w = csv.writer(c)
        w.writerow(["title", "source", "link", "published_utc", "domain"])
        for a in unverified:
            w.writerow([a.title, a.source, a.link, a.ts.strftime("%Y-%m-%d %H:%M"), a.domain])
    return md_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--no-upload", action="store_true", help="skip Drive upload")
    args = ap.parse_args()

    cfg = load_config(args.config)
    os.chdir(HERE)
    now = dt.datetime.now(dt.timezone.utc)
    local = cfg.get("local", {})
    intl = cfg.get("international", local)
    domains_cfg = cfg["domains"]
    max_per = cfg.get("max_items_per_domain", 8)
    window = cfg.get("time_window_hours", 24)

    print("Fetching news across domains...")
    all_articles = []
    for dom, d in domains_cfg.items():
        queries = d.get("queries", [])
        top = d.get("top_stories", False)
        region = local if dom in ("public_concern",) else intl
        arts = fetch.fetch_domain(dom, queries, region, include_top_stories=top)
        print(f"  {dom}: {len(arts)} fetched")
        all_articles.extend(arts)

    # time-window filter
    all_articles = factcheck.apply_time_window(all_articles, now, window)

    # screen
    verified, unverified = factcheck.screen_by_source(
        all_articles,
        cfg["tier1_sources"],
        cfg["min_sources_for_verification"],
    )
    verified = factcheck.dedupe_domains(verified, max_per)

    print(f"Verified: {len(verified)} | needing manual review: {len(unverified)}")

    # write outputs
    os.makedirs(cfg["output_dir"], exist_ok=True)
    os.makedirs(cfg["review_dir"], exist_ok=True)
    date_str = now.strftime("%Y-%m-%d")

    md_name = now.strftime(cfg["md_name_pattern"])
    pdf_name = now.strftime(cfg["pdf_name_pattern"])
    md_path = os.path.join(cfg["output_dir"], md_name)
    pdf_path = os.path.join(cfg["output_dir"], pdf_name)

    md_text = digest.build_markdown(verified, list(domains_cfg.keys()),
                                    cfg["report_title"], now)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_text)

    topdf.build_pdf(md_text, verified, pdf_path, cfg["report_title"], now)

    review_path = write_review_queue(unverified, cfg["review_dir"], date_str)
    print(f"Markdown -> {md_path}")
    print(f"PDF      -> {pdf_path}")
    if unverified:
        print(f"REVIEW   -> {review_path} ({len(unverified)} items need manual check)")

    # upload
    if args.no_upload:
        print("Skipping Drive upload (--no-upload).")
        return 0

    if not cfg["drive"].get("enabled", True):
        print("Drive upload disabled in config.")
        return 0

    print("Uploading to Google Drive...")
    try:
        from googleapiclient.discovery import build
        creds = upload_drive.get_creds(cfg, reraise=True)
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        folder = cfg["drive"]["folder_name"]
        r = upload_drive.upload_file(service, folder, pdf_path, "application/pdf")
        print(f"Uploaded PDF to Drive: {r.get('webViewLink')}")
        r2 = upload_drive.upload_file(service, folder, md_path,
                                      "text/markdown; charset=utf-8")
        print(f"Uploaded Markdown to Drive: {r2.get('webViewLink')}")
    except Exception as exc:
        print(f"!! Drive upload failed: {exc}")
        print("  The PDF/Markdown are still saved locally in output/.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())