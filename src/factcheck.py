"""
Fact-check / screening step.

Rule set so we never publish unconfirmed news:
  1. An article from a Tier-1 trusted outlet is accepted as Verified.
  2. Any other article must be reported by >= min_sources_for_verification
     *distinct* publishers before it is accepted.
  3. Everything else is flagged UNVERIFIED and routed to the manual review
     queue (not included in the auto-sent PDF).

NOTE: This is automated *screening* (source-credibility + multi-source
corroboration). It does NOT verify every factual claim sentence-by-sentence.
Keep the manual-review copy of the report for a final human read before
forwarding it onward.
"""
from __future__ import annotations

import datetime as dt


def _norm(name: str) -> str:
    return (name or "").lower().replace(" the ", " ").strip()


def is_tier1(source: str, tier1: list) -> bool:
    n = _norm(source)
    return any(n == _norm(t) or (len(t) > 3 and _norm(t) in n) for t in tier1)


def screen_by_source(articles, tier1_sources, min_sources):
    """Cross-reference articles by normalized title to corroborate sources."""
    # group all titles (across the whole batch) by normalized key
    groups: dict[str, list] = {}
    for a in articles:
        groups.setdefault(a.title_key, []).append(a)

    verified, unverified = [], []
    for key, arts in groups.items():
        sources = {a.source for a in arts if a.source and a.source != "Unknown"}
        any_tier1 = any(is_tier1(s, tier1_sources) for s in sources)
        if any_tier1:
            best = max(arts, key=lambda a: a.ts)
            best.tags.add("verified")
            best.tags.add("tier1")
            verified.append(best)
        elif len(sources) >= min_sources:
            best = max(arts, key=lambda a: a.ts)
            src_count = len(sources)
            best.tags.add("verified")
            best.tags.add("corrob")
            verified.append(best)
        else:
            # keep the newest representative for the review queue
            best = max(arts, key=lambda a: a.ts)
            best.tags.add("unverified")
            unverified.append(best)

    return verified, unverified


def apply_time_window(articles, now, hours):
    cutoff = now - dt.timedelta(hours=int(hours))
    return [a for a in articles if a.ts >= cutoff]


def dedupe_domains(verified, max_per_domain):
    """Cap the number of unique items shown per domain (respect freshness)."""
    by_domain: dict[str, list] = {}
    for a in sorted(verified, key=lambda a: a.ts, reverse=True):
        by_domain.setdefault(a.domain, []).append(a)
    out = []
    for domain, arts in by_domain.items():
        out.extend(arts[:max_per_domain])
    return out