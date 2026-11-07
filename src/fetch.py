"""Fetch news from Google News RSS and normalize entries."""
from __future__ import annotations

import datetime as dt
import hashlib
import re
import urllib.parse

import feedparser
import requests

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
GOOGLE_NEWS = "https://news.google.com/rss"
TOP_STORIES = "https://news.google.com/rss?{query}"


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _title_key(title: str) -> str:
    """Normalized title used for dedup / cross-referencing."""
    t = title.lower()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^\w\s&]", "", t)
    return t.strip()


class Article:
    __slots__ = ("title", "title_key", "source", "link", "published",
                 "ts", "summary", "domain", "tags")

    def __init__(self, title, source, link, published, summary, domain):
        self.title = _clean(title)
        self.source = _clean(source)
        self.link = _clean(link)
        self.summary = _clean(summary)
        self.domain = domain
        self.title_key = _title_key(self.title)
        self.tags = set()
        # parse pub date
        self.ts = _parse_date(published)

    @property
    def id(self) -> str:
        return hashlib.md5(self.title_key.encode("utf-8")).hexdigest()


def _parse_date(published) -> dt.datetime:
    if not published:
        return dt.datetime.now(dt.timezone.utc)
    try:
        parsed = feedparser.parse(str(published))
        struct = getattr(parsed, "updated_parsed", None)
        if struct:
            return dt.datetime(*struct[:6], tzinfo=dt.timezone.utc)
    except Exception:
        pass
    try:
        # RFC 822
        return dt.datetime.fromtimestamp(feedparser._parse_date(str(published))).replace(tzinfo=dt.timezone.utc)
    except Exception:
        return dt.datetime.now(dt.timezone.utc)


def _search_url(query: str, region) -> str:
    params = {
        "q": query,
        "hl": region["hl"],
        "gl": region["gl"],
        "ceid": region["ceid"],
    }
    enc = urllib.parse.urlencode(params)
    return f"{TOP_STORIES.format(query=enc)}"


def _topic_url(region, label: str = "top") -> str:
    params = {
        "hl": region["hl"],
        "gl": region["gl"],
        "ceid": region["ceid"],
    }
    # topic code for top headlines
    if label == "top":
        params["topic"] = "h"
    return GOOGLE_NEWS + "?" + urllib.parse.urlencode(params)


def _fetch_feed(url: str, timeout: int = 25) -> list:
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": UA})
        resp.raise_for_status()
    except Exception as exc:
        print(f"  [fetch] failed {url} -> {exc}")
        return []
    parsed = feedparser.parse(resp.content)
    out = []
    for e in parsed.entries:
        source = None
        if hasattr(e, "source") and getattr(e.source, "title", None):
            source = e.source.title
        title = _clean(e.get("title", ""))
        link = e.get("link", "")
        summary = _clean(e.get("summary", ""))
        if title:
            out.append(Article(title, source or "Unknown", link, e.get("published", ""), summary, None))
    return out


def fetch_domain(domain: str, queries, region, include_top_stories=False):
    """Returns a list of Article objects tagged with the domain."""
    seen = {}
    for q in queries:
        for art in _fetch_feed(_search_url(q, region)):
            if art.title_key not in seen:
                seen[art.title_key] = art
                art.domain = domain
    if include_top_stories:
        for art in _fetch_feed(_topic_url(region, "top")):
            if art.title_key not in seen:
                seen[art.title_key] = art
                art.domain = domain
    return list(seen.values())