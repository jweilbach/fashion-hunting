#!/usr/bin/env python3
import os, time, json, feedparser, requests, yaml, logging, traceback, random, re, math, unicodedata
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from datetime import datetime, timezone
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound
from requests.exceptions import HTTPError, Timeout, RequestException
from typing import List, Optional, Tuple, Set
from urllib.parse import urlparse, parse_qs, unquote, urljoin
from html import unescape as html_unescape
from connector import Connector
from ai_client import AIClient  # <-- NEW

# Full-article extraction & parsing
import trafilatura
from trafilatura.settings import use_config as trafi_use_config
from bs4 import BeautifulSoup

# --- Selenium resolver (optional fast-path for Google News; ADDED) ---
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as _ChromeOptions
    from selenium.webdriver.chrome.service import Service as _ChromeService
    try:
        from webdriver_manager.chrome import ChromeDriverManager as _ChromeDriverManager
    except Exception:
        _ChromeDriverManager = None
    _SELENIUM_AVAILABLE = True
except Exception:
    _SELENIUM_AVAILABLE = False
# ---------------------------------------------------------------------

# ----------------------------
# Logging
# ----------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Load env (try .env, then .env.example as a fallback)
loaded = load_dotenv()
if not loaded:
    load_dotenv(".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ---- Rate-limit knobs
MAX_RPM = 15
SLEEP_BETWEEN_CALLS = max(60.0 / MAX_RPM, 3.5)
MAX_ITEMS_PER_RUN = 10  # adjust as needed

# ---- Prompt size control
MAX_TEXT_CHARS = 20000  # allow more room for full-article text

# ---- Canonical header
CANONICAL_HEADER = ["timestamp","source","brands","title","link","summary","sentiment","topic","est_reach"]

# ---- Minimal brand safety net (seed examples)
DEFAULT_BRANDS = ["Coors Light", "Doritos"]

# ---- HTTP session with a desktop UA
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
})

# Config for trafilatura
TRAFI_CFG = trafi_use_config()
TRAFI_CFG.set("DEFAULT", "MIN_OUTPUT_SIZE", "200")
TRAFI_CFG.set("DEFAULT", "EXTRACTION_TIMEOUT", "0")
TRAFI_CFG.set("DEFAULT", "STRICT", "False")
TRAFI_CFG.set("DEFAULT", "NO_FOLLOW", "False")

# ----------------------------
# Config & Sheets
# ----------------------------
def load_config():
    with open("config/feeds.yaml", "r") as f:
        feeds = yaml.safe_load(f)["feeds"]
    with open("config/settings.yaml", "r") as f:
        settings = yaml.safe_load(f)

    settings.setdefault("extra_meta_names", [
        "parsely-description", "sailthru.description", "dc.description",
        "summary", "excerpt"
    ])
    settings.setdefault("extra_meta_properties", [
        "article:summary", "twitter:text:title"
    ])
    settings.setdefault("extra_itemprops", [
        "description", "headline", "alternativeHeadline"
    ])
    settings.setdefault("ignore_brand_exact", [
        "Roboto", "Material Icons", "Material Icons Extended",
        "Google Material Icons", "Product Sans", "Google Sans", "Google Sans Display",
        "Google News", "CNN"
    ])
    settings.setdefault("ignore_brand_patterns", [
        r".*\bIcons?\b$",
        r"^Google$",
        r"^https?://",
        r"^[A-Z]\d{2,}$",
    ])
    settings.setdefault("known_brands", ["Coors Light","Doritos","Glossier","Maybelline","Target","Revlon","CoverGirl","Milk Makeup"])

    logging.info(
        "Loaded %d feed URLs; sheet_id=%s / worksheet=%r / known_brands=%s",
        len(feeds), settings.get("sheet_id"), settings.get("worksheet_name"),
        len(settings.get("known_brands", []))
    )
    return feeds, settings

# ----------------------------
# HTML cleaning & Google News URL fix (HARDENED)
# ----------------------------
GOOGLE_HOSTS = ("google.com", "news.google.com", "www.google.com")

def clean_html_to_text(s: str) -> str:
    if not s:
        return ""
    s = html_unescape(s)
    s = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", s)
    s = re.sub(r"(?s)<.*?>", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def extract_publisher_url_from_google_news_param(gn_url: str) -> Optional[str]:
    try:
        p = urlparse(gn_url)
        if p.netloc.endswith("news.google.com"):
            qs = parse_qs(p.query)
            if "url" in qs and qs["url"]:
                return unquote(qs["url"][0])
    except Exception:
        pass
    return None

def _extract_publisher_from_gn_html(gn_html: bytes, base_url: str) -> Optional[str]:
    if not gn_html:
        return None
    try:
        soup = BeautifulSoup(gn_html, "lxml")
    except Exception:
        return None

    def is_external(u: str) -> bool:
        try:
            host = urlparse(u).netloc
        except Exception:
            return False
        if not host:
            return False
        return not any(host.endswith(h) for h in GOOGLE_HOSTS)

    for meta in soup.find_all("meta", attrs={"http-equiv": re.compile(r"refresh", re.I)}):
        content = meta.get("content") or ""
        m = re.search(r'url\s*=\s*([^;]+)', content, flags=re.I)
        if m:
            candidate = urljoin(base_url, m.group(1).strip().strip('"\'')) 
            if is_external(candidate):
                logging.info("GN resolver: meta-refresh -> %s", candidate)
                return candidate

    link_canon = soup.find("link", rel=lambda v: v and "canonical" in v.lower())
    if link_canon and link_canon.get("href"):
        href = link_canon["href"].strip()
        if is_external(href):
            logging.info("GN resolver: canonical -> %s", href)
            return href

    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"].strip())
        if is_external(href):
            logging.info("GN resolver: external anchor -> %s", href)
            return href

    raw = gn_html.decode("utf-8", errors="ignore")
    m = re.search(r'destinationUrl"\s*:\s*"([^"]+)"', raw)
    if m and is_external(m.group(1)):
        logging.info("GN resolver: script destinationUrl -> %s", m.group(1))
        return m.group(1)

    for m in re.finditer(r'"(https?://[^"]+)"', raw):
        url = m.group(1)
        if is_external(url):
            logging.info("GN resolver: script external url -> %s", url)
            return url

    return None

# --- ADDED: Selenium-based resolver for GN article pages ----------------
def _resolve_with_selenium_gn(url: str, wait_secs: float = 4.0) -> Optional[str]:
    """
    Try to resolve Google News /articles/... URLs via headless Chrome.
    Returns publisher URL or None if not resolved or selenium unavailable.
    """
    if not _SELENIUM_AVAILABLE:
        return None
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        path = (parsed.path or "")
        if "news.google.com" not in host or "/articles/" not in path:
            return None

        opts = _ChromeOptions()
        try:
            opts.add_argument("--headless=new")
        except Exception:
            opts.add_argument("--headless")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        # reuse this script's UA for consistency
        try:
            _ua = SESSION.headers.get("User-Agent")
        except Exception:
            _ua = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        opts.add_argument(f"user-agent={_ua}")

        # speed up: block heavy assets
        try:
            prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.managed_default_content_settings.stylesheets": 2,
                "profile.managed_default_content_settings.fonts": 2,
            }
            opts.add_experimental_option("prefs", prefs)
        except Exception:
            pass

        # choose driver init strategy
        if 'CHROMEDRIVER' in os.environ:
            service = _ChromeService(os.environ['CHROMEDRIVER'])
            driver = webdriver.Chrome(service=service, options=opts)
        elif 'GOOGLE_CHROME_SHIM' in os.environ:
            opts.binary_location = os.environ['GOOGLE_CHROME_SHIM']
            driver = webdriver.Chrome(options=opts)
        elif '_ChromeDriverManager' in globals() and _ChromeDriverManager is not None:
            service = _ChromeService(_ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=opts)
        else:
            driver = webdriver.Chrome(options=opts)

        driver.set_page_load_timeout(25)
        try:
            driver.execute_cdp_cmd(
                "Network.setExtraHTTPHeaders",
                {"headers": {"Referer": "https://news.google.com/"}}
            )
        except Exception:
            pass

        driver.get(url)
        time.sleep(wait_secs)
        final = driver.current_url or url
        logging.info("GN resolver (selenium): final -> %s", final)
        if "news.google.com" not in (urlparse(final).netloc or ""):
            try: driver.quit()
            except Exception: pass
            return final

        # sometimes needs an extra tick
        time.sleep(min(6.0, max(1.0, wait_secs)))
        final = driver.current_url or url
        logging.info("GN resolver (selenium): second check -> %s", final)
        try: driver.quit()
        except Exception: pass
        if "news.google.com" not in (urlparse(final).netloc or ""):
            return final
        return None

    except Exception as e:
        logging.info("Selenium resolver error: %s", e)
        try: driver.quit()
        except Exception: pass
        return None
# ----------------------------------------------------------------------

def _resolve_final_url(url: str) -> str:
    direct = extract_publisher_url_from_google_news_param(url)
    if direct:
        logging.info("GN resolver: ?url= param -> %s", direct)
        return direct

    # ADDED: Try Selenium fast-path for GN client-side redirects
    sel = _resolve_with_selenium_gn(url)
    if sel:
        return sel

    try:
        resp = SESSION.get(
            url,
            allow_redirects=True,
            timeout=25,
            headers={" Referer": "https://news.google.com/", "Referer": "https://news.google.com/"}
        )
        http_final = resp.url or url
        host = urlparse(http_final).netloc
        logging.info("Resolver: HTTP final -> %s", http_final)

        if host and not any(host.endswith(h) for h in GOOGLE_HOSTS):
            return http_final

        candidate = _extract_publisher_from_gn_html(resp.content or b"", http_final)
        if candidate:
            return candidate

        return http_final
    except Exception as e:
        logging.warning("Resolver error for %s: %s", url, e)
        return url

def _fetch_full_html(url: str) -> Optional[bytes]:
    try:
        headers = {"Referer": "https://news.google.com/"}
        logging.info("fetching full text from url %s", url)
        r = SESSION.get(url, timeout=35, headers=headers)
        if r.status_code >= 400:
            logging.warning("Fetch returned %s for %s", r.status_code, url)
            return None
        return r.content
    except Exception as e:
        logging.warning("Fetch failed for %s: %s", url, e)
        return None

# ----------------------------
# Full-article text extraction
# ----------------------------
ARTICLE_SELECTORS = [
    "article", "main", '[role=\"main\"]',
    ".article-body", ".articleBody", ".post-content", ".postContent",
    ".entry-content", ".entryContent",
    ".story-body", ".storyBody",
    ".content__article-body", ".ArticleBody",
    ".c-article-body", ".l-article-body",
    ".mainContentContainer", ".content", ".content-body", ".contentBody"
]

NOISE_SELECTORS = [
    "script", "style", "nav", "aside", "footer",
    ".ad", ".ads", ".adsInlineAd", ".sponsored", ".share", ".social",
    "ol.commentlist", "#comments", ".comments"
]

DEFAULT_META_NAMES = {
    "description", "twitter:description", "sailthru.description",
    "parsely-description", "dc.description", "summary", "excerpt"
}
DEFAULT_META_PROPERTIES = {
    "og:description", "og:title", "article:summary", "twitter:text:title"
}
DEFAULT_ITEMPROPS = {
    "description", "headline", "alternativeHeadline"
}

def _meta_blurb(soup: BeautifulSoup,
                extra_meta_names: List[str],
                extra_meta_properties: List[str],
                extra_itemprops: List[str]) -> str:
    parts = []

    names = set(DEFAULT_META_NAMES) | set(map(str.lower, extra_meta_names or []))
    props = set(DEFAULT_META_PROPERTIES) | set(map(str.lower, extra_meta_properties or []))
    itemprops = set(DEFAULT_ITEMPROPS) | set(map(str.lower, extra_itemprops or []))

    for n in names:
        for tag in soup.select(f'meta[name="{n}"]'):
            v = (tag.get("content") or "").strip()
            if v: parts.append(v)
    for p in props:
        for tag in soup.select(f'meta[property="{p}"]'):
            v = (tag.get("content") or "").strip()
            if v: parts.append(v)
    for ip in itemprops:
        for tag in soup.select(f'meta[itemprop="{ip}"]'):
            v = (tag.get("content") or "").strip()
            if v: parts.append(v)
    if soup.title and soup.title.string:
        parts.append(soup.title.string.strip())

    raw = str(soup)
    def rx(pat):
        for m in re.finditer(pat, raw, flags=re.IGNORECASE|re.DOTALL):
            val = (m.group(1) or "").strip()
            if val: parts.append(val)
    for n in names:
        rx(rf'<meta[^>]*\bname\s*=\s*["\']{re.escape(n)}["\'][^>]*\bcontent\s*=\s*["\'](.*?)["\']')
    for p in props:
        rx(rf'<meta[^>]*\bproperty\s*=\s*["\']{re.escape(p)}["\'][^>]*\bcontent\s*=\s*["\'](.*?)["\']')
    for ip in itemprops:
        rx(rf'<meta[^>]*\bitemprop\s*=\s*["\']{re.escape(ip)}["\'][^>]*\bcontent\s*=\s*["\'](.*?)["\']')

    out, seen = [], set()
    for p in parts:
        t = unicodedata.normalize("NFKC", re.sub(r"\s+", " ", html_unescape(p)))
        if t and t not in seen:
            seen.add(t); out.append(t)
    return " \n".join(out)

def _extract_from_candidates(soup: BeautifulSoup) -> str:
    for sel in ARTICLE_SELECTORS:
        node = soup.select_one(sel)
        if not node:
            continue
        try:
            for bad in node.select(", ".join(NOISE_SELECTORS)):
                bad.decompose()
        except Exception:
            pass
        parts = [el.get_text(" ", strip=True) for el in node.select("p, h1, h2, h3, li, a, figcaption")]
        txt = " ".join(p for p in parts if p)
        txt = unicodedata.normalize("NFKC", txt).replace("\u00A0", " ")
        txt = re.sub(r"(\w)-\s+(\w)", r"\1\2", txt)
        txt = re.sub(r"\s+", " ", txt).strip()
        if len(txt) >= 120:
            return txt
    return ""

def extract_article_text(html_bytes: bytes,
                         url: str,
                         extra_meta_names: List[str],
                         extra_meta_properties: List[str],
                         extra_itemprops: List[str]) -> str:
    soup = BeautifulSoup(html_bytes, "lxml")
    meta = _meta_blurb(soup, extra_meta_names, extra_meta_properties, extra_itemprops)
    body = _extract_from_candidates(soup)
    if len(body) < 120:
        try:
            tf = trafilatura.extract(html_bytes, url=url, output="txt",
                                     include_comments=False, include_tables=False, config=TRAFI_CFG)
            if tf and len(tf.strip()) >= 80:
                body = tf.strip()
        except Exception:
            pass
    combo = " \n".join([t for t in [meta, body] if t])
    combo = re.sub(r"\s+", " ", combo).strip()
    return combo[:MAX_TEXT_CHARS]

def fetch_full_article_text(link: str, title: str, summary_clean: str,
                            extra_meta_names: List[str],
                            extra_meta_properties: List[str],
                            extra_itemprops: List[str],
                            *, return_html=False):
    logging.info("resolving link %s", link)
    final_url = _resolve_final_url(link)
    logging.info("Final URL resolved: %s", final_url)

    html = _fetch_full_html(final_url)
    if html:
        logging.info("Fetched HTML bytes: %d", len(html))
    else:
        logging.warning("Failed to fetch HTML for %s", final_url)

    parts = []
    if title: parts.append(title.strip())
    if summary_clean and summary_clean.strip() and summary_clean.strip().lower() != (title or "").strip().lower():
        parts.append(summary_clean.strip())

    article_text = extract_article_text(
        html or b"", url=final_url,
        extra_meta_names=extra_meta_names,
        extra_meta_properties=extra_meta_properties,
        extra_itemprops=extra_itemprops
    )
    if article_text:
        parts.append(article_text)

    big = "\n\n".join(parts).strip()
    if not big:
        big = f"{title}\n\n{summary_clean}\n{final_url}"

    lb = big.lower()

    big = big[:MAX_TEXT_CHARS]
    return (big, html if return_html else None)

# ----------------------------
# Brand helpers (kept here because main still uses _filter_brands after AI call)
# ----------------------------
def _filter_brands(brands: List[str],
                   ignore_exact: List[str],
                   ignore_patterns: List[str]) -> List[str]:
    if not brands:
        return []
    out = []
    seen: Set[str] = set()
    pat_objs = [re.compile(p, re.IGNORECASE) for p in (ignore_patterns or [])]
    ignore_exact_set = set(ignore_exact or [])

    for b in brands:
        if not isinstance(b, str):
            continue
        s = b.strip()
        if not s:
            continue
        s = re.sub(r"\s+", " ", s)
        if len(s) < 2 or len(s) > 120:
            continue
        if re.fullmatch(r"[\W_]+", s) or re.fullmatch(r"\d+", s):
            continue
        if s in ignore_exact_set:
            continue
        blocked = False
        for po in pat_objs:
            if po.search(s):
                blocked = True
                break
        if blocked:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out

# ----------------------------
# Feeds
# ----------------------------
def fetch_mentions(rss_urls):
    items = []
    for url in rss_urls:
        logging.info("fetched news from source %s", url)
        try:
            d = feedparser.parse(url)
            for e in d.entries:
                source = "RSS"
                try:
                    if hasattr(e, "source") and e.source and hasattr(e.source, "title"):
                        source = e.source.title
                except Exception:
                    pass
                title = (getattr(e, "title", "") or "").strip()
                link = (getattr(e, "link", "") or "").strip()
                raw_summary_html = getattr(e, "summary", "") or ""
                raw_summary = clean_html_to_text(raw_summary_html)
                items.append({"source": source, "title": title, "link": link, "raw_summary": raw_summary})
        except Exception as e:
            logging.exception("Failed parsing feed %s: %s", url, e)
            continue
    logging.info("Fetched %d items from %d RSS feeds.", len(items), len(rss_urls))
    return items

# ----------------------------
# Main
# ----------------------------
def main():
    ai_mode = True

    if not OPENAI_API_KEY:
        logging.error("OPENAI_API_KEY is not set. Put it in .env or .env.example.")
        raise SystemExit(1)

    feeds, settings = load_config()
    connector = Connector(settings["sheet_id"], settings["worksheet_name"])
    ws = connector.load_sheet()

    # NEW: create AI client (logic moved, no behavior change)
    ai_client = AIClient(api_key=OPENAI_API_KEY)

    known_brands = settings.get("known_brands", []) or []
    if not isinstance(known_brands, list):
        known_brands = []

    extra_meta_names = settings.get("extra_meta_names", [])
    extra_meta_properties = settings.get("extra_meta_properties", [])
    extra_itemprops = settings.get("extra_itemprops", [])

    ignore_brand_exact = settings.get("ignore_brand_exact", [])
    ignore_brand_patterns = settings.get("ignore_brand_patterns", [])

    rows_to_add, failures = [], 0

    for idx, it in enumerate(fetch_mentions(feeds)):
        if idx >= MAX_ITEMS_PER_RUN:
            logging.info("Hit MAX_ITEMS_PER_RUN=%d; stopping early.", MAX_ITEMS_PER_RUN)
            break

        try:
            logging.info("Fetching full text: source=%s title=%r", it.get("source"), it.get("title"))
            fulltext, html_bytes = fetch_full_article_text(
                it.get("link",""), it.get("title",""), it.get("raw_summary",""),
                extra_meta_names, extra_meta_properties, extra_itemprops, return_html=True
            )

            if len(fulltext) < 100:
                logging.info("Extracted very short article (%d chars) for %s", len(fulltext), it.get("link"))

            logging.info("Analyzing full text (%d chars)…", len(fulltext))
            # MOVED: classify_summarize -> ai_client
            analysis = ai_client.classify_summarize(fulltext, known_brands)

            brands_list = analysis.get("brands", [])
            brands_list = _filter_brands(brands_list, ignore_brand_exact, ignore_brand_patterns)

            if ai_mode:
                # MOVED: ai_extract_brands_from_raw_html -> ai_client
                brands_ai = ai_client.ai_extract_brands_from_raw_html(html_bytes, ignore_brand_exact, ignore_brand_patterns)
                seen = set(map(str.lower, brands_list))
                for b in brands_ai:
                    if b.lower() not in seen:
                        brands_list.append(b)
                        seen.add(b.lower())

            if not brands_list:
                logging.debug("No brands extracted for title=%r | first200=%r",
                              it.get("title"), fulltext[:200])

            brands_cell = ", ".join(brands_list) if brands_list else ""

            row = [
                datetime.now(timezone.utc).isoformat(),
                it.get("source",""),
                brands_cell,
                it.get("title",""),
                it.get("link",""),
                analysis.get("short_summary",""),
                analysis.get("sentiment","neutral"),
                analysis.get("topic","lifestyle"),
                analysis.get("est_reach", 0),
            ]
            rows_to_add.append(row)

            time.sleep(SLEEP_BETWEEN_CALLS + random.uniform(0, 0.4))

        except (Timeout, HTTPError, RequestException) as e:
            logging.error("Network/API error on item (source=%s title=%r link=%s): %s\n%s",
                          it.get("source"), it.get("title"), it.get("link"),
                          e, traceback.format_exc())
            failures += 1
            continue
        except Exception as e:
            logging.error("Unexpected failure on item (source=%s title=%r link=%s): %s\n%s",
                          it.get("source"), it.get("title"), it.get("link"),
                          e, traceback.format_exc())
            failures += 1
            continue

    if rows_to_add:
        try:
            logging.info("Appending %d rows to the sheet…", len(rows_to_add))
            ws.append_rows(rows_to_add, value_input_option="RAW")
            logging.info("Append successful.")
            try:
                n = min(len(rows_to_add), 5)
                vals = ws.get_all_values()[-n:] if n > 0 else []
                logging.info("Verification read (last %d rows): %s", n, vals)
            except Exception as e:
                logging.warning("Could not verify by reading back rows: %s", e)
        except APIError as e:
            logging.error("Failed to append rows (APIError). Do you have Editor access? %s", e)
            raise
        except Exception as e:
            logging.error("Unexpected error during append: %s\n%s", e, traceback.format_exc())
            raise
    else:
        logging.info("No rows to add.")

    today = datetime.now().strftime("%b %d")
    highlights = [
        f"• [{(r[2] or '—')}] {r[3]} — {r[6]} — {r[5]} ({r[4]})"
        for r in rows_to_add[: settings.get("recap_max_items", 8) ]
    ]
    recap = f"""Subject: {today} Media Recap — Top Mentions

Hi team,

Here are today’s highlights ({len(rows_to_add)} total mentions, {failures} failed analyses):

{chr(10).join(highlights) or "No major mentions detected."}

Full tracker is updated in Google Sheets.

Best,
AE Automation Bot
"""
    print(recap)
    logging.info("Run complete. Successes: %d, Failures: %d", len(rows_to_add), failures)

if __name__ == "__main__":
    main()
