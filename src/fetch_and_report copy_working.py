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

# Full-article extraction & parsing
import trafilatura
from trafilatura.settings import use_config as trafi_use_config
from bs4 import BeautifulSoup

# ----------------------------
# Logging
# ----------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Load env (try .env, then .env.example as a fallback)
loaded = load_dotenv()
if not loaded:
    load_dotenv(".env.example")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ---- Rate-limit knobs
MAX_RPM = 15
SLEEP_BETWEEN_CALLS = max(60.0 / MAX_RPM, 3.5)
MAX_ITEMS_PER_RUN = 1  # adjust as needed

# ---- Prompt size control
MAX_TEXT_CHARS = 20000  # allow more room for full-article text
MAX_TOKENS = 400        # a bit more room for JSON

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

    # Defaults for configurable whitelist/ignore entries
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
        # Fonts / UI kits
        "Roboto", "Material Icons", "Material Icons Extended",
        "Google Material Icons", "Product Sans", "Google Sans", "Google Sans Display",
        # Generic platforms & outlets we don't want as 'brands mentioned'
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
    return feeds, setting

# ----------------------------
# HTML cleaning & Google News URL fix (HARDENED)
# ----------------------------
GOOGLE_HOSTS = ("google.com", "news.google.com", "www.google.com")

def clean_html_to_text(s: str) -> str:
    """Strip all HTML from a short snippet (e.g., RSS summaries)."""
    if not s:
        return ""
    s = html_unescape(s)
    s = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", s)
    s = re.sub(r"(?s)<.*?>", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def extract_publisher_url_from_google_news_param(gn_url: str) -> Optional[str]:
    """Return ?url= publisher link if present on Google News links."""
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
    """
    Parse Google News interstitial HTML for a publisher URL using several strategies:
    1) meta refresh
    2) canonical
    3) first external <a href="..."> (non-Google)
    4) script JSON with destinationUrl or any external https URL
    """
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

    # 1) meta refresh content="0;url=..."
    for meta in soup.find_all("meta", attrs={"http-equiv": re.compile(r"refresh", re.I)}):
        content = meta.get("content") or ""
        m = re.search(r'url\s*=\s*([^;]+)', content, flags=re.I)
        if m:
            candidate = urljoin(base_url, m.group(1).strip().strip('"\''))  # absolutize
            if is_external(candidate):
                logging.info("GN resolver: meta-refresh -> %s", candidate)
                return candidate

    # 2) canonical
    link_canon = soup.find("link", rel=lambda v: v and "canonical" in v.lower())
    if link_canon and link_canon.get("href"):
        href = link_canon["href"].strip()
        if is_external(href):
            logging.info("GN resolver: canonical -> %s", href)
            return href

    # 3) first external anchor
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"].strip())
        if is_external(href):
            logging.info("GN resolver: external anchor -> %s", href)
            return href

    # 4) script JSON / raw URLs inside scripts
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

def _resolve_final_url(url: str) -> str:
    """Resolve Google News/redirector URLs to the real publisher when possible."""
    # A) ?url= param short-circuit
    direct = extract_publisher_url_from_google_news_param(url)
    if direct:
        logging.info("GN resolver: ?url= param -> %s", direct)
        return direct

    try:
        # B) Follow HTTP redirects first
        resp = SESSION.get(
            url,
            allow_redirects=True,
            timeout=25,
            headers={" Referer": "https://news.google.com/", "Referer": "https://news.google.com/"}  # some servers check this
        )
        http_final = resp.url or url
        host = urlparse(http_final).netloc
        logging.info("Resolver: HTTP final -> %s", http_final)

        # If we already landed off Google, we’re done
        if host and not any(host.endswith(h) for h in GOOGLE_HOSTS):
            return http_final

        # C) Still on a Google domain; inspect HTML for the publisher URL
        candidate = _extract_publisher_from_gn_html(resp.content or b"", http_final)
        if candidate:
            return candidate

        # D) Give up and return whatever we’ve got
        return http_final
    except Exception as e:
        logging.warning("Resolver error for %s: %s", url, e)
        return url

def _fetch_full_html(url: str) -> Optional[bytes]:
    """Fetch HTML with helpful headers for sites reached from Google News."""
    try:
        headers = {"Referer": "https://news.google.com/"}
        logging.info("**hereisurl**")
        logging.info(url)
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

    # BS4 selectors
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

    # Regex fallback for tricky metas
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

    # de-dup + normalize + collapse spaces
    out, seen = [], set()
    for p in parts:
        t = unicodedata.normalize("NFKC", re.sub(r"\s+", " ", html_unescape(p)))
        if t and t not in seen:
            seen.add(t); out.append(t)
    return " \n".join(out)

def _extract_from_candidates(soup: BeautifulSoup) -> str:
    """Try multiple article containers; return normalized visible text or ''."""
    for sel in ARTICLE_SELECTORS:
        node = soup.select_one(sel)
        if not node:
            continue
        # remove noise inside the node
        try:
            for bad in node.select(", ".join(NOISE_SELECTORS)):
                bad.decompose()
        except Exception:
            pass
        # pull readable text (include links/captions)
        parts = [el.get_text(" ", strip=True) for el in node.select("p, h1, h2, h3, li, a, figcaption")]
        txt = " ".join(p for p in parts if p)
        txt = unicodedata.normalize("NFKC", txt).replace("\u00A0", " ")
        # de-hyphenate linebreak splits
        txt = re.sub(r"(\w)-\s+(\w)", r"\1\2", txt)
        txt = re.sub(r"\s+", " ", txt).strip()
        if len(txt) >= 120:  # likely real article text
            return txt
    return ""

def extract_article_text(html_bytes: bytes,
                         url: str,
                         extra_meta_names: List[str],
                         extra_meta_properties: List[str],
                         extra_itemprops: List[str]) -> str:
    """Robust article text extraction with meta + multi-selector + trafilatura fallback."""
    soup = BeautifulSoup(html_bytes, "lxml")
    # 1) meta/title blurb (helps brand scan even if body fails)
    meta = _meta_blurb(soup, extra_meta_names, extra_meta_properties, extra_itemprops)
    # 2) multi-selector attempt on main content
    body = _extract_from_candidates(soup)
    # 3) trafilatura fallback if body is thin
    if len(body) < 120:
        try:
            tf = trafilatura.extract(html_bytes, url=url, output="txt",
                                     include_comments=False, include_tables=False, config=TRAFI_CFG)
            if tf and len(tf.strip()) >= 80:
                body = tf.strip()
        except Exception:
            pass
    # combine, trim
    combo = " \n".join([t for t in [meta, body] if t])
    combo = re.sub(r"\s+", " ", combo).strip()
    return combo[:MAX_TEXT_CHARS]

def fetch_full_article_text(link: str, title: str, summary_clean: str,
                            extra_meta_names: List[str],
                            extra_meta_properties: List[str],
                            extra_itemprops: List[str],
                            *, return_html=False):
    """
    Resolve to final URL, download page, extract robust article text.
    Returns (fulltext[:MAX_TEXT_CHARS], html_bytes or None)
    """
    logging.info("here is link")
    logging.info(link)
    final_url = _resolve_final_url(link)
    logging.info("Final URL resolved: %s", final_url)

    html = _fetch_full_html(final_url)
    if html:
        logging.info("Fetched HTML bytes: %d", len(html))
    else:
        logging.warning("Failed to fetch HTML for %s", final_url)

    # Build combined text (title + summary + robust article text)
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

    # Probe for expected brand tokens in the combined article text:
    lb = big.lower()
    logging.info("Probe: 'doritos' in text? %s | 'coors' in text? %s", "doritos" in lb, "coors" in lb)

    big = big[:MAX_TEXT_CHARS]
    return (big, html if return_html else None)

# ----------------------------
# Brand helpers
# ----------------------------
def _extract_json_fenced(s: str) -> str:
    if not s: return ""
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s, re.IGNORECASE)
    if m: return m.group(1).strip()
    m2 = re.search(r"\{[\s\S]*\}\s*$", s.strip())
    return m2.group(0).strip() if m2 else s.strip()

def _coerce_str_list(v):
    if v is None: return []
    if isinstance(v, list):
        out = []
        for item in v:
            if isinstance(item, str):
                s = item.strip()
                if s: out.append(s)
            elif isinstance(item, dict):
                name = item.get("name") or item.get("label") or item.get("text")
                if isinstance(name, str) and name.strip():
                    out.append(name.strip())
        return out
    if isinstance(v, str):
        parts = re.split(r"[;,]\s*", v.strip())
        return [p for p in parts if p]
    return []

def _extract_brands_from_payload(data: dict) -> List[str]:
    candidates = []
    for k in ("brands", "brand", "brands_mentioned", "companies", "entities"):
        if k in data:
            candidates.extend(_coerce_str_list(data[k]))
    seen, uniq = set(), []
    for b in candidates:
        if b not in seen:
            seen.add(b); uniq.append(b)
    return uniq

def _extract_brands_rule_based(text: str, known_brands: List[str]) -> List[str]:
    """Deterministic scan of text for known brand names (case-insensitive, possessive tolerant)."""
    if not text: return []
    hay = text
    brand_pool, seen = [], set()
    for b in (known_brands or []) + DEFAULT_BRANDS:
        if not isinstance(b, str): continue
        name = b.strip()
        if not name: continue
        key = name.lower()
        if key in seen: continue
        seen.add(key); brand_pool.append(name)
    hits = []
    for b in brand_pool:
        pattern = rf'(?<!\w){re.escape(b)}(?:[\'’]s)?(?!\w)'
        if re.search(pattern, hay, flags=re.IGNORECASE):
            hits.append(b)
    # sort by first occurrence
    hits.sort(key=lambda x: hay.lower().find(x.lower()))
    return hits

def _filter_brands(brands: List[str],
                   ignore_exact: List[str],
                   ignore_patterns: List[str]) -> List[str]:
    """Drop fonts/outlets/junk; keep clean, reasonably brand-like strings."""
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
        # Basic cleanup
        s = re.sub(r"\s+", " ", s)
        # Heuristics: too short / too long
        if len(s) < 2 or len(s) > 120:
            continue
        # Drop pure punctuation/numbers
        if re.fullmatch(r"[\W_]+", s) or re.fullmatch(r"\d+", s):
            continue
        # Exact denylist
        if s in ignore_exact_set:
            continue
        # Pattern denylist
        blocked = False
        for po in pat_objs:
            if po.search(s):
                blocked = True
                break
        if blocked:
            continue
        # Avoid duplicates (case-insensitive)
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out

# ----------------------------
# LLM classify + summarize (full text)
# ----------------------------
@retry(wait=wait_exponential(multiplier=1, min=2, max=60),
       stop=stop_after_attempt(7),
       retry=retry_if_exception_type((Timeout, RequestException, HTTPError)))
def classify_summarize(fulltext: str, known_brands: List[str]):
    example_text = "This year, Coors Light and Doritos leaned into early Super Bowl strategies."
    example_json = {
        "sentiment": "neutral",
        "topic": "trend",
        "brands": ["Coors Light", "Doritos"],
        "short_summary": "Example summary",
        "est_reach": 50000
    }

    if known_brands:
        brand_hint = (
            f"Prioritize normalization against this known brand list: {known_brands}. "
            "Also include other clearly mentioned brands not in the list.\n"
        )
    else:
        brand_hint = "Include all clearly mentioned brands. Infer from context if obvious.\n"

    prompt = f"""
You are a PR analyst for Alison Brod Marketing + Communications (ABMC).

Extract from the FULL article text:
- sentiment: one of ["positive","neutral","negative"]
- topic: one of ["product","influencer","lifestyle","trend","corporate"]
- brands: JSON array of ALL brand/company/product names explicitly mentioned (use exact casing). {brand_hint.strip()}Do not include media outlets or people.
- short_summary: <= 3 sentences, client-facing
- est_reach: integer estimate (best guess if unknown)

Return ONLY valid JSON with keys exactly: sentiment, topic, brands, short_summary, est_reach.

Example text:
{example_text}

Example JSON:
{json.dumps(example_json, ensure_ascii=False)}

Text:
{fulltext}
""".strip()

    logging.info("***prompt***")
    logging.info(fulltext)
    logging.info("SENDING TO LLM: len=%d first500=%r ... last200=%r",
                 len(fulltext), fulltext[:500], fulltext[-200:])

    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type":"application/json"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role":"user","content":prompt}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "max_tokens": MAX_TOKENS
        },
        timeout=120
    )

    if r.status_code == 429:
        retry_after = r.headers.get("retry-after") or r.headers.get("Retry-After")
        try:
            delay = max(2, int(float(retry_after))) if retry_after else 8
        except Exception:
            delay = 8
        delay += random.uniform(0, 1.0)
        logging.warning("Rate limited (429). Retry-After=%s -> sleeping %.2fs.", retry_after, delay)
        time.sleep(min(delay, 90))
        r.raise_for_status()

    r.raise_for_status()

    content = r.json()["choices"][0]["message"]["content"]
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        clean = _extract_json_fenced(content)
        data = json.loads(clean)

    # Merge brands: rule-based (grounded) + LLM keys
    brands_llm = _extract_brands_from_payload(data)
    brands_rule = _extract_brands_rule_based(fulltext, known_brands)

    seen, all_brands = set(), []
    for b in brands_rule + brands_llm:
        if b not in seen:
            seen.add(b); all_brands.append(b)

    data["brands"] = all_brands
    return data

# ----------------------------
# AI brand extraction from RAW HTML (optional, not used by default)
# ----------------------------
def _chunk_text(s: str, chunk_size: int = 20000) -> List[str]:
    return [s[i:i+chunk_size] for i in range(0, len(s), chunk_size)]

@retry(wait=wait_exponential(multiplier=1, min=2, max=60),
       stop=stop_after_attempt(5),
       retry=retry_if_exception_type((Timeout, RequestException, HTTPError)))
def _ai_extract_brands_from_html_chunk(html_chunk: str) -> List[str]:
    prompt = f"""
You are an information extraction model.
From the following raw HTML fragment, extract a JSON array of brand/company/product names
that a human reader would likely see (visible article content, meta descriptions/titles, schema JSON-LD names/brands/mentions).
DO NOT include:
- news outlets, publishers, or platforms (e.g., Google News, CNN)
- UI fonts, icon sets, styles, or technical libraries (e.g., Roboto, Material Icons, Product Sans, Google Sans)
- people names
Return ONLY:

{{"brands": ["Brand A","Brand B", ...]}}

HTML:
{html_chunk}
""".strip()

    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type":"application/json"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role":"user","content":prompt}],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
            "max_tokens": 220
        },
        timeout=120
    )
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    data = json.loads(_extract_json_fenced(content))
    brands = _coerce_str_list(data.get("brands"))
    return brands

def ai_extract_brands_from_raw_html(html_bytes: Optional[bytes],
                                    ignore_exact: List[str],
                                    ignore_patterns: List[str]) -> List[str]:
    if not html_bytes:
        return []
    raw = html_bytes.decode(errors="ignore")
    chunks = _chunk_text(raw, chunk_size=20000)
    agg, seen = [], set()
    for ch in chunks:
        try:
            out = _ai_extract_brands_from_html_chunk(ch)
        except Exception as e:
            logging.warning("AI chunk extraction failed: %s", e)
            continue
        for b in out:
            key = (b or "").strip().lower()
            if key and key not in seen:
                seen.add(key); agg.append(b)
    return _filter_brands(agg, ignore_exact=ignore_exact, ignore_patterns=ignore_patterns)

# ----------------------------
# Feeds
# ----------------------------
def fetch_mentions(rss_urls):
    items = []
    for url in rss_urls:
        logging.info("**original url**")
        logging.info(url)
        try:
            d = feedparser.parse(url)
            for e in d.entries:
                logging.info("check e")
                logging.info(e)
                source = "RSS"
                try:
                    if hasattr(e, "source") and e.source and hasattr(e.source, "title"):
                        source = e.source.title
                except Exception:
                    pass
                title = (getattr(e, "title", "") or "").strip()
                link = (getattr(e, "link", "") or "").strip()
                raw_summary_html = getattr(e, "summary", "") or ""
                raw_summary = clean_html_to_text(raw_summary_html)  # IMPORTANT
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
    # Flip to True if you also want the raw-HTML AI brand extraction unioned in
    ai_mode = False

    if not OPENAI_API_KEY:
        logging.error("OPENAI_API_KEY is not set. Put it in .env or .env.example.")
        raise SystemExit(1)

    feeds, settings = load_config()
    #ws = load_sheet(settings["sheet_id"], settings["worksheet_name"])
    connector = Connector(settings["sheet_id"], settings["worksheet_name"])
    ws = connector.load_sheet()

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
            analysis = classify_summarize(fulltext, known_brands)

            # HTML method brands (LLM + deterministic scan), then filter
            brands_list = analysis.get("brands", [])
            brands_list = _filter_brands(brands_list, ignore_brand_exact, ignore_brand_patterns)

            # If AI mode enabled, run raw-HTML brand extraction and union
            if ai_mode:
                brands_ai = ai_extract_brands_from_raw_html(html_bytes, ignore_brand_exact, ignore_brand_patterns)
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
