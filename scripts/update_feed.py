import html
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

SOURCE_URL = "https://www.racingpost.com/news/"
BASE_URL = "https://www.racingpost.com"
MAX_ITEMS = 60

OUT = Path("feed.xml")
INDEX = Path("index.html")

# Verified from the Racing Post HTML captured on 4 Oct 2026.
TITLE_SELECTOR = '[data-testid="Text__Title6"]'

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Referer": "https://www.google.com/",
}


def fetch_page():
    """Try a Chrome-like TLS/client first, then fall back to requests."""
    last_error = None

    try:
        from curl_cffi import requests as curl_requests

        for attempt in range(1, 4):
            try:
                r = curl_requests.get(
                    SOURCE_URL,
                    headers=HEADERS,
                    impersonate="chrome",
                    timeout=30,
                    allow_redirects=True,
                )
                if r.status_code == 200 and len(r.text) > 100_000:
                    return r.text
                last_error = f"curl_cffi: HTTP {r.status_code}, {len(r.content)} bytes"
            except Exception as exc:
                last_error = f"curl_cffi: {exc!r}"
    except ImportError:
        last_error = "curl_cffi is not installed"

    try:
        import requests

        for attempt in range(1, 4):
            try:
                r = requests.get(
                    SOURCE_URL,
                    headers=HEADERS,
                    timeout=30,
                    allow_redirects=True,
                )
                if r.status_code == 200 and len(r.text) > 100_000:
                    return r.text
                last_error = f"requests: HTTP {r.status_code}, {len(r.content)} bytes"
            except Exception as exc:
                last_error = f"requests: {exc!r}"
    except ImportError:
        pass

    raise RuntimeError(f"Racing Post fetch failed after retries: {last_error}")


def parse_iso(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def parse_articles(markup):
    soup = BeautifulSoup(markup, "html.parser")
    now = datetime.now(timezone.utc)
    articles = []
    seen = set()

    for title_node in soup.select(TITLE_SELECTOR):
        title = " ".join(title_node.stripped_strings)
        if not title:
            continue

        link_node = title_node.find_parent("a", href=True)
        if not link_node:
            continue

        href = link_node.get("href", "").strip()
        if not href:
            continue

        link = urljoin(BASE_URL, href)

        if not link.startswith(BASE_URL + "/"):
            continue
        if link in seen:
            continue

        seen.add(link)
        pub = now

        # In the current Racing Post markup the title link sits inside
        # a div whose sibling taxonomy block contains Text__Time.
        article_box = title_node.parent.parent
        time_node = article_box.select_one('[data-testid="Text__Time"]')
        if time_node:
            parsed = parse_iso(time_node.get("datetime"))
            if parsed:
                pub = parsed

        articles.append({
            "title": title,
            "link": link,
            "pub": pub,
        })

        if len(articles) >= MAX_ITEMS:
            break

    if len(articles) < 5:
        raise RuntimeError(
            f"Only {len(articles)} article titles found. "
            "The Racing Post page structure may have changed."
        )

    return articles


def esc(value):
    return html.escape(str(value), quote=True)


def build_rss(articles):
    now = datetime.now(timezone.utc)
    items = []

    for a in articles:
        items.append(
            "    <item>\n"
            f"      <title>{esc(a['title'])}</title>\n"
            f"      <link>{esc(a['link'])}</link>\n"
            f"      <guid isPermaLink=\"true\">{esc(a['link'])}</guid>\n"
            f"      <pubDate>{format_datetime(a['pub'])}</pubDate>\n"
            "    </item>"
        )

    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Racing Post News</title>
    <link>https://www.racingpost.com/news/</link>
    <description>Latest Racing Post News</description>
    <language>en-gb</language>
    <ttl>15</ttl>
    <lastBuildDate>%s</lastBuildDate>
%s
  </channel>
</rss>
""" % (format_datetime(now), "\n".join(items))


def build_index():
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Racing Post News RSS</title>
</head>
<body>
<h1>Racing Post News RSS</h1>
<p><a href="feed.xml">Open the RSS feed</a></p>
<p>Automatically generated from the Racing Post News page.</p>
</body>
</html>
"""


def main():
    markup = fetch_page()
    articles = parse_articles(markup)

    # Only write the new feed after the whole fetch/parse succeeded.
    OUT.write_text(build_rss(articles), encoding="utf-8")
    INDEX.write_text(build_index(), encoding="utf-8")

    print(f"OK: created {OUT} with {len(articles)} unique articles.")
    for article in articles[:5]:
        print(f"- {article['title']} -> {article['link']}")


if __name__ == "__main__":
    main()
