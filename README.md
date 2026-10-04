# Racing Post News → RSS for Feeder

Ready-to-use GitHub Pages + GitHub Actions RSS bridge for the Racing Post News page.

## What it does

Every 15 minutes, GitHub Actions downloads:

https://www.racingpost.com/news/

and extracts the article titles from the current Racing Post HTML selector:

    [data-testid="Text__Title6"]

This selector was verified against a complete Racing Post `/news/` HTML response captured on 4 Oct 2026.

The workflow creates a normal RSS 2.0 feed:

    feed.xml

You can then add that RSS URL to the free Feeder version as an ordinary RSS feed.

## Installation

1. Create a **new public GitHub repository**.
2. Upload all files from this folder, preserving:
   - `.github/workflows/update-feed.yml`
   - `scripts/update_feed.py`
   - `requirements.txt`
   - `index.html`
   - `feed.xml`
3. In GitHub open:
   **Settings → Pages**
4. Under **Build and deployment → Source**, choose:
   **GitHub Actions**
5. Open **Actions**.
6. Select **Update Racing Post RSS**.
7. Click **Run workflow**.
8. Wait for the green checkmark.
9. Open **Settings → Pages → Visit site**.

Your feed address will be:

    https://YOUR-USERNAME.github.io/YOUR-REPOSITORY/feed.xml

Put that address into Feeder.

## Refresh rate

The workflow is scheduled every 15 minutes. GitHub documents that scheduled workflows can run as often as every 5 minutes, although scheduled jobs can be delayed during periods of high load.

## Important first test

The biggest unknown is whether Racing Post will accept a request from a GitHub-hosted runner.

The script therefore:
- uses a real Chrome-like User-Agent,
- first tries `curl_cffi` with Chrome TLS impersonation,
- retries three times,
- falls back to normal requests,
- refuses to overwrite the existing feed if the fetch fails.

If the first workflow run reports HTTP 403 or 429, Racing Post is blocking GitHub's runner rather than the parser being wrong. In that case we should move only the fetching part to another service; the RSS format and Feeder side can stay exactly the same.

## Why the parser should work

The HAR supplied for this project contains a complete 200 OK response for:

    https://www.racingpost.com/news/

It contains 111 occurrences of `data-testid="Text__Title6"`.

The title is inside an `<a>` whose `href` is the article URL. The same article block also contains:

    data-testid="Text__Time"

The parser uses these elements instead of guessing from visible text such as `NEW`.

## Files

- `.github/workflows/update-feed.yml` — scheduled update + GitHub Pages deployment
- `scripts/update_feed.py` — Racing Post downloader and RSS generator
- `requirements.txt` — Python dependencies
- `index.html` — simple test page
- `feed.xml` — RSS feed
