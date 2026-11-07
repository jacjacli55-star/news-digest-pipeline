# 📰 Daily News Digest

An **automated, fact-checked news digest**. Runs every day at **08:00**, collects
local + international headlines across 6 domains, screens every story for
credibility (**no fake or unconfirmed news is ever auto-published**), and
delivers a **Markdown + PDF** report, a **static news portal**, and an
**interactive workflow diagram** — all published to GitHub Pages and uploaded to
Google Drive.

> 🌐 Live site: https://jacjacli55-star.github.io/news-digest/
> Workflow diagram built with **Archify**.

## What it does

| Step | What happens |
|---|---|
| **Schedule** | macOS `launchd` fires at 08:00 daily (`com.jacky.dailynewsdigest.plist`) |
| **Ingest** | Google News RSS (free, no API key) — 6 domains × local + international |
| **Screen** | Tier-1 trusted outlets auto-approved; any other source must appear in ≥2 outlets |
| **Build** | Generates `DailyNewsDigest_YYYY-MM-DD.md` + PDF (via reportlab), plus a static portal |
| **Deliver** | Uploads PDF/Markdown to Google Drive; pushes the portal + archive to GitHub Pages |

Anything that fails screening is routed to a **manual review queue** and is
**never** included in the delivered report.

## Domains covered

- Technology · Counter-Terrorism / Security · Self-Improvement · Management ·
  Leadership · Public-Concern / Trending

## Project layout

```
news_digest/
├── config.yaml        # domains, region, tier-1 sources, thresholds, Drive settings
├── run_daily.sh       # scheduled runner (launchd): run -> build site -> push Pages
├── com.jacky.dailynewsdigest.plist
├── requirements.txt
├── src/
│   ├── fetch.py        # Google News RSS ingestion
│   ├── factcheck.py    # tier-1 + multi-source screening
│   ├── digest.py       # Markdown report
│   ├── topdf.py        # Markdown -> PDF (reportlab)
│   ├── build_site.py   # static news portal
│   ├── upload_drive.py # Google Drive upload (headless token reuse)
│   ├── auth_drive.py   # one-time Google Drive OAuth
│   └── run.py          # orchestrator
```

## Getting started

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp config.yaml.example config.yaml   # if applicable, then edit region/domains
.venv/bin/python src/run.py --no-upload   # one-off local run
```

## Security & correctness

- **Fact-check policy** is explicit in `src/factcheck.py`: Tier-1 sources are
  whitelisted; everything else needs ≥2 independent outlets.
- **`credentials/` is git-ignored** — Google Drive OAuth client + saved token
  never go into the repo.
- A credibility disclaimer is printed in every report.

## License

Apache-2.0 (this project's own arrangement; see ARCHIFY for its license).
Archify: https://github.com/tt-a1i/archify (Apache-2.0).