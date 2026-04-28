import asyncio
import os
import re
import urllib.parse
import uuid
from dataclasses import dataclass
from pathlib import Path

import aiohttp
import aiofiles
from pyrogram import errors

from anony import config, logger, app


@dataclass
class MusicTrack:
    cdnurl: str
    url: str
    id: str
    key: str = None

    @classmethod
    def from_dict(cls, data: dict) -> "MusicTrack":
        return cls(
            cdnurl=data.get("cdnurl", ""),
            url=data.get("url", ""),
            id=data.get("id", ""),
            key=data.get("key"),
        )


class FallenApi:
    def __init__(self, retries: int = 3, timeout: int = 15):
        self.api_url = config.API_URL.rstrip("/")
        self.api_key = config.API_KEY
        self.retries = retries
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: aiohttp.ClientSession | None = None
        self.download_dir = Path("downloads")

    def _get_headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
        }

    async def get_session(self) -> None:
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

    async def get_track(self, url: str) -> MusicTrack | None:
        endpoint = f"{self.api_url}/api/track?url={urllib.parse.quote(url)}"

        for attempt in range(1, self.retries + 1):
            try:
                async with self.session.get(endpoint, headers=self._get_headers()) as resp:
                    data = await resp.json(content_type=None)

                    if resp.status == 200 and isinstance(data, dict):
                        return MusicTrack.from_dict(data)

                    error_msg = data.get("message") if isinstance(data, dict) else None
                    status = data.get("status", resp.status) if isinstance(data, dict) else resp.status
                    logger.warning(f"[API ERROR] {error_msg or 'Unexpected error'} (status {status})")
                    return None

            except aiohttp.ClientError as e:
                logger.warning(f"[NETWORK ERROR] Attempt {attempt}/{self.retries} failed: {e}")
                break
            except asyncio.TimeoutError:
                logger.warning(f"[TIMEOUT] Attempt {attempt}/{self.retries} exceeded timeout.")
                break
            except Exception as e:
                logger.warning(f"[UNEXPECTED ERROR] {e}")
                break
            await asyncio.sleep(4)

        logger.warning("[FAILED] All retry attempts exhausted.")
        return None

    async def download_cdn(self, video_id: str, cdn_url: str) -> str | None:
        for _ in range(1, self.retries + 1):
            try:
                async with self.session.get(cdn_url) as resp:
                    if resp.status != 200:
                        logger.warning(f"[HTTP {resp.status}] Failed to download from {cdn_url}")
                        return None

                    cd = resp.headers.get("Content-Disposition")
                    if cd:
                        match = re.findall(r'filename="?([^";]+)"?', cd)
                        filename = match[0] if match else None
                    else:
                        filename = None

                    if not filename:
                        filename = os.path.basename(cdn_url.split("?")[0]) or f"{uuid.uuid4().hex[:8]}.mp3"

                    save_path = self.download_dir / filename

                    async with aiofiles.open(save_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(16 * 1024):
                            if chunk:
                                await f.write(chunk)

                    return str(save_path)

            except aiohttp.ClientError:
                pass
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                logger.warning(f"[{video_id}]: {e}")
            await asyncio.sleep(4)

        logger.warning(f"[{video_id}]: Download failed.")
        return None

    async def download_track(self, video_id: str, url: str) -> str | None:
        track = await self.get_track(url)
        if not track:
            return None

        dl_url = track.cdnurl
        if re.match(r"https?://t\.me/([^/]+)/(\d+)", dl_url):
            try:
                msg = await app.get_messages(message_ids=dl_url)
                if msg.video:
                    return None
                file_path = await msg.download()
                return file_path
            except errors.FloodWait as e:
                logger.warning(f"[FloodWait]: {e.value}s")
            except Exception as e:
                logger.warning(f"[TG DOWNLOAD ERROR]: {e}")
                return None

        return await self.download_cdn(video_id, dl_url)
