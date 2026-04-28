import os

from pymongo import AsyncMongoClient

from anony import app

class Cache:
    def __init__(self, cache_db: str) -> None:
        self.mongo = AsyncMongoClient(cache_db, serverSelectionTimeoutMS=12500)
        self.db = self.mongo.Song
        self.cache = {}
        self.dl_list = []
        self.dl_dict = {}
        self.cachedb = self.db.cache

        self.SLOG: int = -1001065650212
        self.load_cache()

    def load_cache(self) -> None:
        with os.scandir("downloads") as entries:
            for entry in entries:
                fname = entry.name.split(".")[0]
                fpath = entry.path
                self.dl_list.append(fname)
                self.dl_dict[fname] = fpath

    async def get_song(self, id: str) -> int | None:
        if id not in self.cache:
            doc = await self.cachedb.find_one({"_id": id})
            if not doc:
                return None

            self.cache[id] = doc["mid"]
        return self.cache[id]

    async def add_song(self, id: str, m_id: int) -> None:
        await self.cachedb.update_one(
            {"_id": id},
            {"$set": {"mid": m_id}},
            upsert=True,
        )
        self.cache[id] = m_id

    async def handle_dl(self, file: str, vid: str) -> None:
        self.dl_list.append(vid)
        self.dl_dict[vid] = file
        sent = await app.send_audio(
            chat_id=self.SLOG,
            audio=file,
        )
        await self.add_song(vid, sent.id)

    async def fetch_song(self, id: str) -> str | None:
        if id in self.dl_list:
            return self.dl_dict[id]

        if mid := await self.get_song(id):
            try:
                msg = await app.get_messages(
                    chat_id=self.SLOG,
                    message_ids=mid,
                )
                file = await msg.download()
            except Exception:
                return None
            self.dl_list.append(id)
            self.dl_dict[id] = file
            return file
        return None
