# 🤖 Agent Task Brief — Automated Daily News Digest

> Use this document to build (or continue) an automated system that produces a
> daily, fact-checked news digest and delivers it automatically. It must run
> unattended, respect a schedule, and never publish unconfirmed news.

---

## 1. Objective

Build a self-running program that **every day at 08:00**:

1. Scans **local + international** news across several topic domains.
2. **Fact-checks / screens** every story (no fake or unconfirmed news allowed).
3. Generates a **Markdown** report, renders it to **PDF**.
4. **Automatically uploads** the report to the cloud (Google Drive / GCS).
5. For every story, includes its **reference link** and publisher.

The agent is responsible for the automation working reliably on the target
machine every day with no manual step required (after a one-time setup).

---

## 2. Requirements (must-have)

### Schedule
- Runs automatically at **08:00 daily** (no manual trigger).
- Should trigger via the OS scheduler (macOS `launchd`, Linux `cron`, or
  Windows Task Scheduler), not by an app staying open.

### News coverage — topic domains
Search **both local and international** headlines, filtered into these 6 domains:

| Domain | Description / example queries |
|---|---|
| **Technology** | AI, cybersecurity, gadgets, software, tech industry |
| **Counter-Terrorism / Security** | terrorism, counter-terrorism, national/homeland security |
| **Self-Improvement** | personal development, productivity, habits, mindfulness, wellness |
| **Management** | management, business strategy, corporate, organizations |
| **Leadership** | leadership, executives, CEO, people-management |
| **Public-Concern / Trending** | issues that sparked public concern or public debate |

### Quality conditions (non-negotiable)
- ✅ **Fact-checking:** only confirmed news. Do **not** publish fake or
  unconfirmed stories. (See §3 for how.)
- ✅ **Reference links:** every story must carry the outlet/publisher and a
  usable source link.
- ✅ **Output format:** a **Markdown** report **and** a **PDF** version.
- ✅ **Cloud delivery:** the PDF (and Markdown) must be **uploaded automatically**
  to the user's Google Cloud / Google Drive, into a dedicated folder.

---

## 3. How to satisfy the fact-check requirement

Pure factual claim-verification is not fully automatable, so use a defensible
**screening policy** and make it explicit:

1. **Tier-1 trusted sources** (Reuters, BBC, AP, The Guardian, NYT, WSJ,
   Bloomberg, CNN, CNBC, Financial Times, The Economist, Al Jazeera, France 24,
   DW, Bloomberg, etc.) → accept as verified.
2. **Any other source** → require corroboration from **≥ 2 distinct outlets**
   before acceptance.
3. **Single-source, non-Tier-1** items → **exclude from the auto-sent PDF** and
   route to a manual-review folder, so nothing unconfirmed ever goes out.
4. Print a clear **credibility disclaimer** in every report stating that
   screening checks source credibility + multi-outlet corroboration, and that a
   final human review is recommended before redistribution.

> The screening must happen **before** the PDF is generated and uploaded.

---

## 4. Delivery (cloud upload)

- Upload each day's **PDF** and **Markdown** to the user's **Google Drive**
  (or Google Cloud Storage) inside a folder like `DailyNewsDigest/`.
- Use a **dated filename**, e.g. `DailyNewsDigest_2026-11-07.pdf`.
- **Authentication:** must work headless. Recommended one-time setup:
  - Google Drive: create a **Desktop OAuth Client** (Drive API enabled),
    run an interactive login **once** to save a reusable token, then the job
    reuses the token with no prompting. (A plain `gcloud` user credential /
    ADC usually does **not** carry the Drive scope.)
  - If GCS instead: a **service-account key** issued to the bucket.
- If upload fails, **still save the files locally** and log the error.

---

## 5. Suggested technical approach (free & reliable)

Because it must run every day for free:

- **Data source:** Google News RSS
  (`https://news.google.com/rss/search?q=<QUERY>&hl=en&gl=US&ceid=US:en`)
  — free, no API key, and it aggregates Reuters/BBC/AP/Guardian/etc., with each
  entry tagged by **publisher** and a **link**.
  - Add a query per domain for both local (user's country) and international.
- **Stack:** Python 3 + `feedparser` (fetch), `PyYAML` (config),
  `reportlab` (PDF, pure-Python, no LaTeX/pandoc needed),
  `google-api-python-client` + `google-auth-oauthlib` (Drive upload).
- **Scheduling (macOS):** a `launchd` `StartCalendarInterval` job at Hour 8,
  Minute 0, pointing at a shell wrapper that runs the Python script and logs.
- **Project layout (single folder):**

```
news_digest/
├── config.yaml        # domains, region, tier-1 sources, thresholds, Drive settings
├── src/
│   ├── fetch.py        # pull + normalize Google News RSS
│   ├── factcheck.py    # tier-1 + multi-source screening → verified / review
│   ├── digest.py       # build Markdown
│   ├── topdf.py        # Markdown → PDF (reportlab)
│   ├── upload_drive.py # headless Drive upload (token reuse)
│   ├── auth_drive.py   # one-time interactive OAuth
│   └── run.py          # orchestrator: fetch → screen → md+pdf → upload
├── run_daily.sh        # wrapper for the scheduler (absolute paths, logging)
├── com....plist        # launchd job (Hour 8, Minute 0)
├── output/             # generated .md + .pdf (uploaded to Drive)
└── review/             # unverified items needing manual check
```

---

## 6. Definition of done

The system is complete when, **without any manual step**, at 08:00 each day:

- [ ] All 6 domains are searched (local + international).
- [ ] Stories are screened; **nothing unverified** appears in the delivered PDF.
- [ ] A dated **`.md`** and **`.pdf`** are produced.
- [ ] Both are **uploaded to Google Drive** automatically in `DailyNewsDigest/`.
- [ ] Every story shows its **publisher** and **reference link**.
- [ ] A credibility disclaimer is present.
- [ ] The run is logged; failures don't lose the locally-saved files.

---

## 7. Notes for the agent

- Non-ASCII paths exist (the project may sit inside a folder named
  `未命名資料夾`); handle them, don't strip them.
- Keep changes consistent with the existing files if resuming a build.
- Provide a `README` with the one-time Google Drive OAuth steps and how to
  test a run manually (`python run.py --no-upload`).
- Date shown in samples uses the runtime date (`2026-11-07`).