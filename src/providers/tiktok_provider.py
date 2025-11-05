# providers/tiktok_provider.py
"""
TikTok Provider - fetches videos from TikTok
"""

import os
import logging
import asyncio
from typing import List, Dict, Optional, Any
from .base_provider import ContentProvider
from TikTokApi import TikTokApi


class TikTokProvider(ContentProvider):
    """
    Provider for TikTok videos.
    Fetches videos based on hashtags, keywords, or user profiles.
    """

    def __init__(self, search_configs: List[Dict], headless: bool = True):
        """
        Initialize TikTok provider.

        Args:
            search_configs: List of search config dicts with keys:
                - type: 'hashtag', 'keyword', or 'user'
                - value: hashtag/keyword/username to search
                - count (optional): number of videos to fetch (default 30)
            headless: Whether to run browser in headless mode
        """
        self.search_configs = search_configs
        self.headless = headless

        # Allow overrides via environment variables without changing call sites
        # Recommended to reduce bot detection:
        #   export TIKTOK_BROWSER=webkit
        #   export TIKTOK_PROXY=http://user:pass@host:port
        self.browser = os.getenv("TIKTOK_BROWSER", "chromium")  # 'chromium' | 'webkit' | 'firefox'
        self.proxy = os.getenv("TIKTOK_PROXY")  # e.g. http://user:pass@host:port

        self.api: Optional[TikTokApi] = None
        logging.info(
            "TikTokProvider initialized with %d searches (headless=%s, browser=%s, proxy=%s)",
            len(search_configs), self.headless, self.browser, bool(self.proxy)
        )

    # ──────────────────────────────────────────────────────────────────────
    # API/session management
    # ──────────────────────────────────────────────────────────────────────
    async def _get_api(self) -> TikTokApi:
        if self.api is None:
            self.api = TikTokApi()
            await self._open_sessions()
        return self.api

    async def _open_sessions(self):
        kwargs: Dict[str, Any] = {
            "headless": self.headless,
            "num_sessions": 1,
            "sleep_after": 2,
            "browser": self.browser,
        }
        if self.proxy:
            # TikTokApi expects a list for proxies in some builds; single string works in recent versions.
            kwargs["proxy"] = self.proxy
        await self.api.create_sessions(**kwargs)

    async def _reset_sessions(self, *, flip_headless: bool = False, browser: Optional[str] = None):
        try:
            if self.api:
                await self.api.close_sessions()
        finally:
            if flip_headless:
                self.headless = not self.headless
            if browser:
                self.browser = browser
            await self._open_sessions()

    # ──────────────────────────────────────────────────────────────────────
    # Search helpers
    # ──────────────────────────────────────────────────────────────────────
    async def _search_hashtag(self, hashtag: str, count: int = 30) -> List[Dict]:
        api = await self._get_api()
        hashtag = hashtag.lstrip('#')
        logging.info("Searching TikTok hashtag: #%s", hashtag)

        # up to two attempts: second attempt toggles to non-headless if needed
        for attempt in (1, 2):
            try:
                tag = api.hashtag(name=hashtag)
                videos: List[Dict] = []
                async for video in tag.videos(count=count):
                    video_data = await self._extract_video_data(video)
                    if video_data:
                        videos.append(video_data)
                logging.info("Found %d videos for #%s", len(videos), hashtag)
                return videos
            except Exception as e:
                logging.error("Error searching hashtag #%s (attempt %d): %s", hashtag, attempt, e)
                if "empty response" in str(e).lower() or "detecting you're a bot" in str(e).lower():
                    await self._reset_sessions(flip_headless=True, browser="webkit")
                else:
                    break
        return []

    async def _search_keyword(self, keyword: str, count: int = 30) -> List[Dict]:
        api = await self._get_api()
        logging.info("Searching TikTok keyword: %s", keyword)

        for attempt in (1, 2):
            try:
                videos: List[Dict] = []

                # Some TikTokApi builds do NOT expose search.videos; fall back to search.general
                search_obj = getattr(api, "search", None)
                videos_method = getattr(search_obj, "videos", None) if search_obj else None

                if callable(videos_method):
                    # Newer/alternate builds where search.videos exists as an async generator
                    async for video in videos_method(keyword, count=count):
                        vd = await self._extract_video_data(video)
                        if vd:
                            videos.append(vd)
                else:
                    # Fallback path: search.general returns mixed items; filter video-like
                    general_method = getattr(search_obj, "general", None)
                    if not callable(general_method):
                        raise RuntimeError("TikTokApi: neither search.videos nor search.general available.")
                    async for item in general_method(keyword, count=count):
                        # Heuristic: treat things with id + author as videos
                        try:
                            d = item.as_dict
                            if d.get("id") and d.get("author"):
                                vd = await self._extract_video_data(item)
                                if vd:
                                    videos.append(vd)
                        except Exception:
                            continue

                logging.info("Found %d videos for keyword: %s", len(videos), keyword)
                return videos
            except Exception as e:
                logging.error("Error searching keyword '%s' (attempt %d): %s", keyword, attempt, e)
                if "empty response" in str(e).lower() or "detecting you're a bot" in str(e).lower():
                    await self._reset_sessions(flip_headless=True, browser="webkit")
                else:
                    break
        return []

    async def _get_user_videos(self, username: str, count: int = 30) -> List[Dict]:
        api = await self._get_api()
        username = username.lstrip('@')
        logging.info("Fetching videos from user: @%s", username)

        for attempt in (1, 2):
            try:
                user = api.user(username=username)
                videos: List[Dict] = []
                async for video in user.videos(count=count):
                    vd = await self._extract_video_data(video)
                    if vd:
                        videos.append(vd)
                logging.info("Found %d videos from @%s", len(videos), username)
                return videos
            except Exception as e:
                logging.error("Error fetching videos from @%s (attempt %d): %s", username, attempt, e)
                if "empty response" in str(e).lower() or "detecting you're a bot" in str(e).lower():
                    await self._reset_sessions(flip_headless=True, browser="webkit")
                else:
                    break
        return []

    # ──────────────────────────────────────────────────────────────────────
    # Normalization
    # ──────────────────────────────────────────────────────────────────────
    async def _extract_video_data(self, video) -> Optional[Dict]:
        try:
            video_dict = video.as_dict

            # Creator
            author = video_dict.get('author', {}) or {}
            username = author.get('uniqueId') or 'unknown'
            nickname = author.get('nickname') or username

            # Video
            video_id = video_dict.get('id') or ''
            desc = (video_dict.get('desc') or '').strip()

            # URL
            video_url = f"https://www.tiktok.com/@{username}/video/{video_id}" if username and video_id else ""

            # Hashtags
            hashtags = []
            for c in (video_dict.get('challenges') or []):
                title = (c.get('title') or '').strip()
                if title:
                    hashtags.append(f"#{title}")

            # Stats
            stats = video_dict.get('stats') or {}
            play_count = int(stats.get('playCount') or 0)
            like_count = int(stats.get('diggCount') or 0)
            comment_count = int(stats.get('commentCount') or 0)
            share_count = int(stats.get('shareCount') or 0)

            stats_text = (
                f"[👁️ {self._format_number(play_count)} | "
                f"❤️ {self._format_number(like_count)} | "
                f"💬 {self._format_number(comment_count)} | "
                f"🔗 {self._format_number(share_count)}]"
            )
            hashtag_text = " ".join(hashtags) if hashtags else ""
            raw_summary = "\n\n".join(x for x in [desc, hashtag_text, stats_text] if x).strip()

            return {
                'source': f"TikTok (@{username})",
                'title': desc[:200] if desc else f"Video by @{username}",
                'link': video_url,
                'raw_summary': raw_summary,
                'provider': 'TikTok',
                'video_id': video_id,
                'username': username,
                'nickname': nickname,
                'hashtags': hashtags,
                'stats': {
                    'plays': play_count,
                    'likes': like_count,
                    'comments': comment_count,
                    'shares': share_count,
                },
                'est_reach': play_count,
                'create_time': video_dict.get('createTime', 0),
            }
        except Exception as e:
            logging.error("Error extracting video data: %s", e)
            return None

    def _format_number(self, num: int) -> str:
        if num >= 1_000_000_000:
            return f"{num/1_000_000_000:.1f}B"
        if num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        if num >= 1_000:
            return f"{num/1_000:.1f}K"
        return str(num)

    # ──────────────────────────────────────────────────────────────────────
    # Orchestration
    # ──────────────────────────────────────────────────────────────────────
    async def _fetch_all_videos(self) -> List[Dict]:
        all_videos: List[Dict] = []

        for config in self.search_configs:
            search_type = config.get('type', 'hashtag')
            value = config.get('value', '')
            count = int(config.get('count', 30))

            if not value:
                logging.warning("Skipping empty search config: %s", config)
                continue

            if search_type == 'hashtag':
                vids = await self._search_hashtag(value, count)
            elif search_type == 'keyword':
                vids = await self._search_keyword(value, count)
            elif search_type == 'user':
                vids = await self._get_user_videos(value, count)
            else:
                logging.warning("Unknown search type: %s", search_type)
                continue

            all_videos.extend(vids)

            # Gentle pacing between searches
            if len(self.search_configs) > 1:
                await asyncio.sleep(2)

        return all_videos

    def fetch_items(self) -> List[Dict]:
        async def _fetch():
            try:
                return await self._fetch_all_videos()
            finally:
                if self.api:
                    await self.api.close_sessions()
                    self.api = None

        videos = asyncio.run(_fetch())
        logging.info("TikTokProvider: Fetched %d total videos", len(videos))
        return videos

    def get_provider_name(self) -> str:
        return "TikTok"
