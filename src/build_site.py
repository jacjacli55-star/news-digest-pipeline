#!/usr/bin/env python3
"""Build a static editorial-style news page from a digest Markdown file.

Reads the digest Markdown produced by run.py and renders a self-contained
index.html (inline CSS, no dependencies). Open it in a browser or copy the
site/ folder to GitHub Pages / any static host.

Usage:  python build_site.py [path/to/DailyNewsDigest_YYYY-MM-DD.md]
        (defaults to the newest digest in ../output/)
"""
from __future__ import annotations

import glob
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
DEFAULT_OUT = os.path.join(PROJ, "site", "index.html")

DOMAIN_META = {
    "Technology": ("#0b5394", "tech"),
    "Counter-Terrorism & Security": ("#b23b3b", "security"),
    "Self-Improvement": ("#2e7d32", "self"),
    "Management": ("#6a329f", "management"),
    "Leadership": ("#a6661c", "leadership"),
    "Public-Concern / Trending Issues": ("#c2185b", "public"),
    "Public Concern / Trending Issues": ("#c2185b", "public"),
}


def newest_md():
    files = sorted(glob.glob(os.path.join(PROJ, "output", "DailyNewsDigest_*.md")),
                   key=os.path.getmtime, reverse=True)
    return files[0] if files else None


def parse_digest(text: str):
    """Convert our digest markdown into structured sections."""
    sections = []          # list of {name, color, items:[{title,source,badge_type,link,published}]}
    cur = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("### "):
            if cur is None:
                cur = {"name": "General", "color": "#37474f", "items": []}
                sections.append(cur)
            cur["items"].append({"title": line[4:].strip(), "source": "",
                                 "badge": "verified", "link": "", "label": "",
                                 "published": ""})
        elif line.startswith("## "):
            name = line[3:].strip()
            color = "unknown"
            flag = "general"
            for k, (c, f) in DOMAIN_META.items():
                if name == k:
                    color, flag = c, f
            cur = {"name": name, "color": color, "flag": flag, "items": []}
            sections.append(cur)
        elif line.startswith("- **") and cur and cur["items"]:
            item = cur["items"][-1]
            m = re.match(r"- \*\*\[Verified — (.+?)\]\*\*", line)
            if m:
                item["source"] = m.group(1)
            if "multiple sources" in line:
                item["badge"] = "multi"
        elif line.startswith("- 🔗 Reference:") and cur and cur["items"]:
            item = cur["items"][-1]
            m = re.search(r"\]\((\S+?)\)", line)
            lm = re.search(r"Reference: \[([^\]]+)\]", line)
            if m:
                item["link"] = m.group(1)
            item["label"] = lm.group(1) if lm else item["link"]
        elif line.startswith("- 🕐 Published:") and cur and cur["items"]:
            item = cur["items"][-1]
            item["published"] = line.replace("- 🕐 Published:", "").strip()
    return [s for s in sections if s.get("items")]


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_html(sections, report_title="Daily News Digest", generated=""):
    cards_html = []
    for sec in sections:
        items_html = []
        for it in sec["items"]:
            badge_class = "multi" if it["badge"] == "multi" else "tier1"
            badge_txt = (f"Verified · {_esc(it['source'])}"
                         if not it["link"] else "")
            published = f"<span class='pub'>{_esc(it['published'])}</span>" if it["published"] else ""
            link_html = ""
            if it["link"]:
                link_html = (f"<a class='ref' href='{it['link']}' target='_blank' "
                             f"rel='noopener'><span class='ref-dot'>🔗</span> "
                             f"{_esc(it['label'] or 'Read full story')}</a>")
            items_html.append(f"""
      <article class="card">
        <h3>{_esc(it['title'])}</h3>
        <div class="meta">
          <span class="badge {badge_class}">{badge_txt}</span>
          {published}
        </div>
        <div class="actions">{link_html}</div>
      </article>""")
        if not items_html:
            continue
        head = sec["name"]
        flag = sec.get("flag", "general")
        color = sec.get("color", "#37474f")
        count = len(sec["items"])
        cards_html.append(f"""
    <section class="domain" id="dom-{flag}">
      <div class="domain-head" style="--c:{color}">
        <h2>{_esc(head)}</h2>
        <span class="count">{count}</span>
      </div>
      <div class="grid">{"".join(items_html)}</div>
    </section>""")

    t = datetime.now(timezone.utc).strftime("%A, %d %B %Y")
    date_line = generated or t
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(report_title)} — {t}</title>
<style>
  :root {{
    --ink:#1d2129; --muted:#6b7280; --line:#e6e8ee; --bg:#f6f7f9; --card:#ffffff;
    --accent:#0b5394; --radius:14px;
  }}
  * {{ box-sizing:border-box; }}
  body {{
    margin:0; color:var(--ink);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    background:var(--bg); line-height:1.5;
  }}
  .wrap {{ max-width:1000px; margin:0 auto; padding:28px 20px 60px; }}
  header.hero {{
    border-bottom:3px solid var(--accent); padding-bottom:18px; margin-bottom:8px;
  }}
  header.hero h1 {{
    font-size:34px; margin:0 0 4px; letter-spacing:-.5px;
    font-family:Georgia,"Times New Roman",serif;
  }}
  header.hero .tagline {{ color:var(--muted); font-size:14px; }}
  menu.toc {{
    display:flex; flex-wrap:wrap; gap:8px; padding:14px 0; margin:0;
    border-bottom:1px solid var(--line);
  }}
  menu.toc a {{
    font-size:12.5px; text-decoration:none; color:var(--muted);
    background:#fff; border:1px solid var(--line); border-radius:999px;
    padding:5px 12px; transition:.15s;
  }}
  menu.toc a:hover {{ color:#fff; border-color:var(--accent); background:var(--accent); }}
  .summary {{
    font-size:14px; color:var(--muted); padding:2px 0 10px;
  }}
  section.domain {{ margin-top:24px; }}
  .domain-head {{
    display:flex; align-items:center; gap:10px;
    border-left:4px solid var(--c,#37474f); padding-left:12px; margin-bottom:12px;
  }}
  .domain-head h2 {{ margin:0; font-size:19px; color:var(--c,#37474f); }}
  .domain-head .count {{
    font-size:12px; color:#fff; background:var(--c,#37474f);
    border-radius:999px; padding:1px 9px;
  }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(310px,1fr)); gap:14px; }}
  .card {{
    background:var(--card); border:1px solid var(--line); border-radius:var(--radius);
    padding:16px; display:flex; flex-direction:column; gap:10px;
    transition:box-shadow .18s, transform .18s;
  }}
  .card:hover {{ box-shadow:0 8px 24px rgba(20,30,60,.10); transform:translateY(-2px); }}
  .card h3 {{ margin:0; font-size:16px; line-height:1.34; }}
  .meta {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; }}
  .badge {{
    font-size:11px; font-weight:600; border-radius:999px; padding:2px 9px;
  }}
  .badge.tier1 {{ background:#e7f0fa; color:#0b5394; }}
  .badge.multi  {{ background:#e7f4ea; color:#2e7d32; }}
  .actions {{ margin-top:auto; }}
  a.ref {{
    font-size:12.5px; color:var(--accent); text-decoration:none; font-weight:600;
  }}
  a.ref:hover {{ text-decoration:underline; }}
  .pub {{ font-size:11.5px; color:var(--muted); }}
  .ref-dot {{ margin-right:3px; }}
  footer {{
    margin-top:34px; border-top:1px solid var(--line); padding-top:14px;
    font-size:12px; color:var(--muted);
  }}
  @media (max-width:640px) {{ header.hero h1 {{ font-size:26px; }} }}
</style>
</head>
<body>
<div class="wrap">
  <header class="hero">
    <h1>{_esc(report_title)}</h1>
    <div class="tagline">{_esc(date_line)} · Fact-checked · Source-verified</div>
  </header>

  <menu class="toc" aria-label="Domains">
    {"".join(f'<a href="#dom-{s.get("flag","general")}">{_esc(s["name"])}</a>' for s in sections)}
  </menu>

  <div class="summary">
    Compiled from free Google News RSS (Reuters, BBC, AP, The Guardian, CNN, NYT,
    WSJ, Bloomberg and more). Every story is screened by source credibility and
    multi-source corroboration.
  </div>

  {"".join(cards_html)}

  <footer>
    Credibility note: automated screening checks source credibility &amp;
    multi-outlet corroboration. It does not independently verify every factual
    claim; perform a final human review before redistribution.
  </footer>
</div>
</body>
</html>
"""
    return html


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else newest_md()
    if not arg or not os.path.exists(arg):
        print("No digest markdown found. Run run.py first, or pass a path.")
        return 1
    with open(arg, encoding="utf-8") as f:
        text = f.read()
    sections = parse_digest(text)
    total = sum(len(s["items"]) for s in sections)
    if not sections:
        print("Could not parse any sections from", arg)
        return 1
    html = build_html(sections)
    os.makedirs(os.path.dirname(DEFAULT_OUT), exist_ok=True)
    with open(DEFAULT_OUT, "w", encoding="utf-8") as g:
        g.write(html)
    print(f"Built site: {DEFAULT_OUT}  ({total} stories, {len(sections)} domains)")
    return 0


if __name__ == "__main__":
    sys.exit(main())