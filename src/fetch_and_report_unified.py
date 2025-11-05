#!/usr/bin/env python3
"""
Unified content fetcher and reporter.
Supports multiple providers (RSS feeds, TikTok, etc.)
Maintains all existing RSS logic while adding TikTok support.
"""

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

import os, time, json, yaml, traceback, random, re, math, unicodedata
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from datetime import datetime, timezone
from dotenv import load_dotenv
from typing import List, Optional, Tuple, Set
from urllib.parse import urlparse, parse_qs, unquote, urljoin
from html import unescape as html_unescape
from requests.exceptions import HTTPError, Timeout, RequestException

# Import existing modules
from connector import Connector
from ai_client import AIClient

# Import providers
from providers.base_provider import ContentProvider
from providers.rss_provider import RSSProvider

# Try to import TikTok provider (optional)
try:
    from providers.tiktok_provider import TikTokProvider
    TIKTOK_AVAILABLE = True
except ImportError:
    TIKTOK_AVAILABLE = False
    # logging.warning("TikTok provider not available. Install with: pip install TikTok-Api playwright")

# Full-article extraction & parsing (for RSS)
import requests
import trafilatura
from trafilatura.settings import use_config as trafi_use_config
from bs4 import BeautifulSoup

# Selenium for Google News resolution (optional)
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

# ----------------------------
# Logging
# ----------------------------
# logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Load env
loaded = load_dotenv()
if not loaded:
    load_dotenv(".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ---- Rate-limit knobs
MAX_RPM = 15
SLEEP_BETWEEN_CALLS = max(60.0 / MAX_RPM, 3.5)
MAX_ITEMS_PER_RUN = 2  # Total items across all providers

# ---- Prompt size control
MAX_TEXT_CHARS = 20000

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
# Config Loading
# ----------------------------
def load_config():
    """Load all configuration files"""
    
    # Load RSS feeds
    rss_feeds = []
    if os.path.exists("config/feeds.yaml"):
        with open("config/feeds.yaml", "r") as f:
            feed_data = yaml.safe_load(f)
            rss_feeds = feed_data.get("feeds", [])
    
    # Load TikTok searches
    tiktok_searches = []
    if os.path.exists("config/tiktok_searches.yaml"):
        with open("config/tiktok_searches.yaml", "r") as f:
            tiktok_data = yaml.safe_load(f)
            tiktok_searches = tiktok_data.get("tiktok_searches", [])
    
    # Load settings
    with open("config/settings_unified.yaml", "r") as f:
        settings = yaml.safe_load(f)
    
    # Set defaults
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
        "Google News", "CNN", "TikTok", "Instagram", "Facebook", "Twitter", "Snapchat"
    ])
    settings.setdefault("ignore_brand_patterns", [
        r".*\bIcons?\b$",
        r"^Google$",
        r"^https?://",
        r"^[A-Z]\d{2,}$",
    ])
    settings.setdefault("known_brands", [
        "Coors Light", "Doritos", "Glossier", "Maybelline", 
        "Target", "Revlon", "CoverGirl", "Milk Makeup"
    ])
    
    # Provider settings
    settings.setdefault("enable_rss", True)
    settings.setdefault("enable_tiktok", False)  # Opt-in for TikTok
    
    logging.info(
        "Loaded config: %d RSS feeds, %d TikTok searches | sheet_id=%s / worksheet=%r",
        len(rss_feeds), len(tiktok_searches),
        settings.get("sheet_id"), settings.get("worksheet_name")
    )
    
    return rss_feeds, tiktok_searches, settings

# ----------------------------
# Article extraction helpers (for RSS)
# ----------------------------
GOOGLE_HOSTS = ("google.com", "news.google.com", "www.google.com")
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

def _resolve_with_selenium_gn(url: str, wait_secs: float = 4.0) -> Optional[str]:
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
        
        try:
            _ua = SESSION.headers.get("User-Agent")
        except Exception:
            _ua = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        opts.add_argument(f"user-agent={_ua}")

        try:
            prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.managed_default_content_settings.stylesheets": 2,
                "profile.managed_default_content_settings.fonts": 2,
            }
            opts.add_experimental_option("prefs", prefs)
        except Exception:
            pass

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

def _resolve_final_url(url: str) -> str:
    direct = extract_publisher_url_from_google_news_param(url)
    if direct:
        logging.info("GN resolver: ?url= param -> %s", direct)
        return direct

    sel = _resolve_with_selenium_gn(url)
    if sel:
        return sel

    try:
        resp = SESSION.get(
            url,
            allow_redirects=True,
            timeout=25,
            headers={"Referer": "https://news.google.com/"}
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
        logging.info("Fetching full text from URL %s", url)
        r = SESSION.get(url, timeout=35, headers=headers)
        if r.status_code >= 400:
            logging.warning("Fetch returned %s for %s", r.status_code, url)
            return None
        return r.content
    except Exception as e:
        logging.warning("Fetch failed for %s: %s", url, e)
        return None

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
    logging.info("Resolving link %s", link)
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

    big = big[:MAX_TEXT_CHARS]
    return (big, html if return_html else None)

# ----------------------------
# Brand filtering (shared)
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
# Main
# ----------------------------
def main():
    if not OPENAI_API_KEY:
        logging.error("OPENAI_API_KEY is not set. Put it in .env or .env.example.")
        raise SystemExit(1)

    # Load configuration
    rss_feeds, tiktok_searches, settings = load_config()
    
    # Initialize connector and AI client
    connector = Connector(settings["sheet_id"], settings["worksheet_name"])
    ws = connector.load_sheet()
    ai_client = AIClient(api_key=OPENAI_API_KEY)
    
    known_brands = settings.get("known_brands", []) or []
    if not isinstance(known_brands, list):
        known_brands = []
    
    extra_meta_names = settings.get("extra_meta_names", [])
    extra_meta_properties = settings.get("extra_meta_properties", [])
    extra_itemprops = settings.get("extra_itemprops", [])
    
    ignore_brand_exact = settings.get("ignore_brand_exact", [])
    ignore_brand_patterns = settings.get("ignore_brand_patterns", [])
    
    # Initialize providers
    providers: List[ContentProvider] = []
    
    # Add RSS provider
    if settings.get("enable_rss", True) and rss_feeds:
        logging.info("Enabling RSS provider with %d feeds", len(rss_feeds))
        providers.append(RSSProvider(rss_feeds))
    
    # Add TikTok provider
    if settings.get("enable_tiktok", False) and tiktok_searches:
        if not TIKTOK_AVAILABLE:
            logging.warning("TikTok provider requested but not available. Install TikTok-Api and playwright.")
        else:
            logging.info("Enabling TikTok provider with %d searches", len(tiktok_searches))
            providers.append(TikTokProvider(tiktok_searches, headless=True))
    
    if not providers:
        logging.error("No providers enabled. Enable RSS and/or TikTok in settings.yaml")
        return
    
    # Fetch items from all providers
    all_items = []
    for provider in providers:
        try:
            logging.info("Fetching from provider: %s", provider.get_provider_name())
            items = provider.fetch_items()
            all_items.extend(items)
            logging.info("Got %d items from %s", len(items), provider.get_provider_name())
        except Exception as e:
            logging.error("Error fetching from provider %s: %s\n%s",
                         provider.get_provider_name(), e, traceback.format_exc())
            continue
    
    logging.info("Total items fetched from all providers: %d", len(all_items))
    
    # Limit total items per run
    if len(all_items) > MAX_ITEMS_PER_RUN:
        logging.info("Limiting to %d items (out of %d)", MAX_ITEMS_PER_RUN, len(all_items))
        all_items = all_items[:MAX_ITEMS_PER_RUN]
    
    rows_to_add = []
    failures = 0
    
    # Process each item
    for idx, item in enumerate(all_items):
        try:
            provider_type = item.get('provider', 'unknown')
            logging.info("Processing item %d/%d [%s]: %s",
                        idx+1, len(all_items), provider_type, item.get('title', '')[:50])
            
            # Determine how to extract full text based on provider
            if provider_type == 'RSS':
                # Full article extraction for RSS items
                logging.info("Fetching full text: source=%s title=%r", item.get("source"), item.get("title"))
                fulltext, html_bytes = fetch_full_article_text(
                    item.get("link", ""), item.get("title", ""), item.get("raw_summary", ""),
                    extra_meta_names, extra_meta_properties, extra_itemprops, return_html=True
                )
                
                if len(fulltext) < 100:
                    logging.info("Extracted very short article (%d chars) for %s", len(fulltext), item.get("link"))
            
            elif provider_type == 'TikTok':
                # TikTok videos: construct analysis text from video data
                description = item.get('title', '')
                summary = item.get('raw_summary', '')
                username = item.get('username', '')
                nickname = item.get('nickname', '')
                hashtags = " ".join(item.get('hashtags', []))
                
                stats = item.get('stats', {})
                stats_text = (
                    f"This TikTok video has {stats.get('plays', 0):,} plays, "
                    f"{stats.get('likes', 0):,} likes, "
                    f"{stats.get('comments', 0):,} comments, and "
                    f"{stats.get('shares', 0):,} shares."
                )
                
                fulltext = f"""
TikTok Video by @{username} ({nickname})

Description:
{description}

{stats_text}

Hashtags: {hashtags}

Full context:
{summary}
""".strip()
                html_bytes = None
            
            else:
                # Unknown provider: use raw_summary
                fulltext = f"{item.get('title', '')}\n\n{item.get('raw_summary', '')}"
                html_bytes = None
            
            # AI analysis
            logging.info("Analyzing content (%d chars)…", len(fulltext))
            analysis = ai_client.classify_summarize(fulltext, known_brands)
            
            # Extract and filter brands
            brands_list = analysis.get("brands", [])
            brands_list = _filter_brands(brands_list, ignore_brand_exact, ignore_brand_patterns)
            
            # For RSS: try AI brand extraction from HTML if enabled
            if provider_type == 'RSS' and html_bytes and settings.get("enable_ai_brand_extraction", True):
                brands_ai = ai_client.ai_extract_brands_from_raw_html(
                    html_bytes, ignore_brand_exact, ignore_brand_patterns
                )
                seen = set(map(str.lower, brands_list))
                for b in brands_ai:
                    if b.lower() not in seen:
                        brands_list.append(b)
                        seen.add(b.lower())
            
            # For TikTok: infer from username if no brands detected
            if provider_type == 'TikTok' and not brands_list:
                username_lower = item.get('username', '').lower()
                for brand in known_brands:
                    if brand.lower() in username_lower:
                        brands_list.append(brand)
                        break
            
            if not brands_list:
                logging.debug("No brands extracted for title=%r | first200=%r",
                             item.get('title'), fulltext[:200])
            
            brands_cell = ", ".join(brands_list) if brands_list else ""
            
            # Get estimated reach
            est_reach = item.get('est_reach', analysis.get('est_reach', 0))
            
            # Build row for sheet
            row = [
                datetime.now(timezone.utc).isoformat(),
                item.get("source", ""),
                brands_cell,
                item.get("title", "")[:500],  # Limit title length
                item.get("link", ""),
                analysis.get("short_summary", ""),
                analysis.get("sentiment", "neutral"),
                analysis.get("topic", "lifestyle"),
                est_reach,
            ]
            rows_to_add.append(row)
            
            # Rate limiting
            time.sleep(SLEEP_BETWEEN_CALLS + random.uniform(0, 0.4))
        
        except (Timeout, HTTPError, RequestException) as e:
            logging.error("Network/API error on item (source=%s title=%r link=%s): %s\n%s",
                         item.get("source"), item.get("title"), item.get("link"),
                         e, traceback.format_exc())
            failures += 1
            continue
        except Exception as e:
            logging.error("Unexpected failure on item (source=%s title=%r link=%s): %s\n%s",
                         item.get("source"), item.get("title"), item.get("link"),
                         e, traceback.format_exc())
            failures += 1
            continue
    
    # Append to sheet
    if rows_to_add:
        try:
            logging.info("Appending %d rows to the sheet…", len(rows_to_add))
            ws.append_rows(rows_to_add, value_input_option="RAW")
            logging.info("Append successful.")
            
            # Verification read
            try:
                n = min(len(rows_to_add), 5)
                vals = ws.get_all_values()[-n:] if n > 0 else []
                logging.info("Verification read (last %d rows): %s", n, vals)
            except Exception as e:
                logging.warning("Could not verify by reading back rows: %s", e)
        
        except Exception as e:
            logging.error("Failed to append rows: %s\n%s", e, traceback.format_exc())
            raise
    else:
        logging.info("No rows to add.")
    
    # Generate recap email
    today = datetime.now().strftime("%b %d")
    highlights = [
        f"• [{(r[2] or '—')}] {r[3][:80]} — {r[6]} — {r[5][:100]} ({r[4]})"
        for r in rows_to_add[:settings.get("recap_max_items", 8)]
    ]
    
    recap = f"""Subject: {today} Media Recap — Top Mentions

Hi team,

Here are today's highlights ({len(rows_to_add)} total items, {failures} failed analyses):

{chr(10).join(highlights) or "No major mentions detected."}

Full tracker is updated in Google Sheets.

Best,
AE Automation Bot
"""
    
    print(recap)
    logging.info("Run complete. Successes: %d, Failures: %d", len(rows_to_add), failures)


if __name__ == "__main__":
    main()