# ai_client.py
# Extracted from fetch_and_report.py without logic changes (only moved into a class).

import os, time, json, logging, random, re, unicodedata
from typing import List, Optional
import requests
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from requests.exceptions import HTTPError, Timeout, RequestException
from html import unescape as html_unescape

# Create logger for this module
logger = logging.getLogger(__name__)

# ---- Prompt size control (same values as original)
MAX_TEXT_CHARS = 20000
MAX_TOKENS = 400

DEFAULT_BRANDS = ["Coors Light", "Doritos"]

class AIClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.error("OPENAI_API_KEY is not set. Put it in .env or .env.example.")
            raise SystemExit(1)

    # ----------------------------
    # Helper fns moved as-is (kept private)
    # ----------------------------
    def _extract_json_fenced(self, s: str) -> str:
        if not s: return ""
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s, re.IGNORECASE)
        if m: return m.group(1).strip()
        m2 = re.search(r"\{[\s\S]*\}\s*$", s.strip())
        return m2.group(0).strip() if m2 else s.strip()

    def _coerce_str_list(self, v):
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

    def _extract_brands_from_payload(self, data: dict) -> List[str]:
        candidates = []
        for k in ("brands", "brand", "brands_mentioned", "companies", "entities"):
            if k in data:
                candidates.extend(self._coerce_str_list(data[k]))
        seen, uniq = set(), []
        for b in candidates:
            if b not in seen:
                seen.add(b); uniq.append(b)
        return uniq

    def _extract_brands_rule_based(self, text: str, known_brands: List[str]) -> List[str]:
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
        hits.sort(key=lambda x: hay.lower().find(x.lower()))
        return hits

    def _filter_brands(self, brands: List[str], ignore_exact: List[str], ignore_patterns: List[str]) -> List[str]:
        if not brands:
            return []
        out = []
        seen = set()
        pat_objs = [re.compile(p, re.IGNORECASE) for p in (ignore_patterns or [])]
        ignore_exact_set = set(ignore_exact or [])
        for b in brands:
            if not isinstance(b, str):
                continue
            s = (b or "").strip()
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
    # Public API (same signatures/behavior as your originals)
    # ----------------------------
    @retry(wait=wait_exponential(multiplier=1, min=2, max=60),
           stop=stop_after_attempt(7),
           retry=retry_if_exception_type((Timeout, RequestException, HTTPError)))
    def classify_summarize(self, fulltext: str, known_brands: List[str]):
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

        # logger.info("***prompt***")
        # logger.info(prompt)
        logger.info("SENDING TO LLM: len=%d first500=%r ... last200=%r",
                     len(fulltext), fulltext[:500], fulltext[-200:])

        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type":"application/json"},
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
            logger.warning("Rate limited (429). Retry-After=%s -> sleeping %.2fs.", retry_after, delay)
            time.sleep(min(delay, 90))
            r.raise_for_status()

        r.raise_for_status()

        content = r.json()["choices"][0]["message"]["content"]
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            clean = self._extract_json_fenced(content)
            data = json.loads(clean)

        brands_llm = self._extract_brands_from_payload(data)
        brands_rule = self._extract_brands_rule_based(fulltext, known_brands)

        logger.info("LLM extracted brands: %s", brands_llm)
        logger.info("Rule-based extracted brands: %s", brands_rule)

        seen, all_brands = set(), []
        for b in brands_rule + brands_llm:
            if b not in seen:
                seen.add(b); all_brands.append(b)

        logger.info("Combined brands (before filtering): %s", all_brands)
        data["brands"] = all_brands
        return data

    def _chunk_text(self, s: str, chunk_size: int = 20000) -> List[str]:
        return [s[i:i+chunk_size] for i in range(0, len(s), chunk_size)]

    @retry(wait=wait_exponential(multiplier=1, min=2, max=60),
           stop=stop_after_attempt(5),
           retry=retry_if_exception_type((Timeout, RequestException, HTTPError)))
    def _ai_extract_brands_from_html_chunk(self, html_chunk: str) -> List[str]:
        prompt = f"""
You are an information extraction model.
From the following raw HTML fragment, extract a JSON array of brand/company/product names
that a human reader would likely see (visible article content, meta descriptions/titles, schema JSON-LD names/brands/mentions).

INCLUDE companies/brands when they are:
- The subject of the article (e.g., "Refinery29 announces layoffs", "Alison Brod Marketing wins award")
- Products, fashion/beauty brands, retailers being discussed
- PR firms, agencies, or marketing companies mentioned in the content

DO NOT include:
- News outlets ONLY when they are the source/byline (e.g., "Published by CNN")
- UI fonts, icon sets, styles, or technical libraries (e.g., Roboto, Material Icons, Product Sans, Google Sans)
- People names
- Generic terms like "the company", "the brand"

Return ONLY:

{{"brands": ["Brand A","Brand B", ...]}}

HTML:
{html_chunk}
""".strip()

        try:
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type":"application/json"},
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
        except HTTPError as e:
            # Log detailed HTTP error information before retrying
            logger.error(f"OpenAI API HTTP error: {e.response.status_code} - {e.response.text[:200]}")
            raise

        content = r.json()["choices"][0]["message"]["content"]
        data = json.loads(self._extract_json_fenced(content))
        brands = self._coerce_str_list(data.get("brands"))
        return brands

    def ai_extract_brands_from_raw_html(self, html_bytes: Optional[bytes],
                                        ignore_exact: List[str],
                                        ignore_patterns: List[str],
                                        max_html_size: Optional[int] = 500000) -> List[str]:
        """
        Extract brands from raw HTML using AI chunk processing.

        Args:
            html_bytes: Raw HTML bytes
            ignore_exact: List of brand names to filter out (exact match)
            ignore_patterns: List of regex patterns to filter out brands
            max_html_size: Maximum HTML size in bytes to process. Set to None to disable size limit. Default: 500KB

        Returns:
            List of extracted brand names
        """
        if not html_bytes:
            return []

        html_size = len(html_bytes)
        logger.info(f"Extracting brands from HTML ({html_size:,} bytes)")

        # Skip processing if HTML is too large (unless max_html_size is None)
        if max_html_size is not None and html_size > max_html_size:
            logger.warning(f"HTML size ({html_size:,} bytes) exceeds max ({max_html_size:,} bytes). Skipping HTML brand extraction.")
            return []

        raw = html_bytes.decode(errors="ignore")
        chunks = self._chunk_text(raw, chunk_size=20000)
        chunk_count = len(chunks)

        logger.info(f"Processing {chunk_count} HTML chunks for brand extraction")

        agg, seen = [], set()
        for idx, ch in enumerate(chunks, 1):
            try:
                out = self._ai_extract_brands_from_html_chunk(ch)
                logger.debug(f"Chunk {idx}/{chunk_count}: Extracted {len(out)} brands")
            except Exception as e:
                logger.warning(f"AI chunk extraction failed for chunk {idx}/{chunk_count}: {e}")
                continue
            for b in out:
                key = (b or "").strip().lower()
                if key and key not in seen:
                    seen.add(key); agg.append(b)

        logger.info(f"Total brands extracted from HTML: {len(agg)}")
        return self._filter_brands(agg, ignore_exact=ignore_exact, ignore_patterns=ignore_patterns)
