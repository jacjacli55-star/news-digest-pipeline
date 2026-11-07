"""Render the verified articles into a Markdown digest."""
from __future__ import annotations

import datetime as dt

DOMAIN_LABELS = {
    "technology": "Technology",
    "counter_terrorism": "Counter-Terrorism & Security",
    "self_improvement": "Self-Improvement",
    "management": "Management",
    "leadership": "Leadership",
    "public_concern": "Public-Concern / Trending Issues",
}


def _badge(art) -> str:
    if "corrob" in art.tags:
        return f"**[Verified — multiple sources]** <sub>[{art.source}]</sub>"
    return f"**[Verified — {art.source}]**"


def _title_without_publisher(title: str, source: str) -> str:
    """Google News appends ' - PublisherName'; drop that suffix for the heading."""
    if not source:
        return title
    suffix = f" - {source}"
    if title.endswith(suffix):
        return title[: -len(suffix)].rstrip()
    return title


def build_markdown(verified, domain_order, report_title, now) -> str:
    date = now.strftime("%A, %d %B %Y")
    lines = []
    lines.append(f"# {report_title}")
    lines.append("")
    lines.append(f"*{date}*  ")
    lines.append("")
    lines.append(
        "Compiled from free Google News RSS (Reuters, BBC, AP, The Guardian, "
        "CNN, NYT, WSJ, Bloomberg and more). Facts were screened by source "
        "credibility and multi-source corroboration — every story below carries "
        "its publisher and a reference link."
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    by_domain = {}
    for a in verified:
        by_domain.setdefault(a.domain, []).append(a)

    total = len(verified)
    lines.append(f"**{total} verified stories** across {len(by_domain)} domains.")
    lines.append("")

    for dom in domain_order:
        if dom not in by_domain:
            continue
        label = DOMAIN_LABELS.get(dom, dom.replace("_", " ").title())
        lines.append(f"## {label}")
        lines.append("")
        items = sorted(by_domain[dom], key=lambda a: a.ts, reverse=True)
        for a in items:
            t = _title_without_publisher(a.title, a.source)
            lines.append(f"### {t}")
            lines.append("")
            lines.append(f"- {_badge(a)}")
            lines.append(f"- 🔗 Reference: [{_pub_domain(a.link)}]({a.link})")
            lines.append(f"- 🕐 Published: {a.ts.strftime('%Y-%m-%d %H:%M UTC')}")
            lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Disclaimer: Automated screening checks source credibility and "
                 "multi-outlet corroboration. It does not independently verify every "
                 "factual claim. Please do a final human review before redistribution.*")
    lines.append("")
    return "\n".join(lines)


def _domain(url):
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return parsed.netloc or url


def _pub_domain(url):
    from urllib.parse import urlparse
    parsed = urlparse(url)
    label = parsed.netloc
    return label if label else url