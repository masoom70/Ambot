from pyrogram.errors import (ChatSendMediaForbidden, ChatSendPhotosForbidden,
                             MessageIdInvalid)
from pyrogram.types import InputMediaPhoto, Message
from pytgcalls import PyTgCalls, exceptions
from pytgcalls.types import Update
from pytgcalls.types.input_stream import AudioPiped, AudioVideoPiped
from pytgcalls.types.input_stream.quality import HighQualityAudio, HighQualityVideo

from anony import app, config, db, lang, logger, queue, userbot, yt
from anony.helpers import Media, Track, buttons, thumb

class TgCall(PyTgCalls):
    def __init__(self):
        self.clients = []

    async def pause(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        await db.playing(chat_id, paused=True)
        return await client.pause_stream(chat_id)

    async def resume(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        await db.playing(chat_id, paused=False)
        return await client.resume_stream(chat_id)

    async def stop(self, chat_id: int) -> None:
        client = await db.get_assistant(chat_id)
        queue.clear(chat_id)
        await db.remove_call(chat_id)
        await db.set_autoplay(chat_id, False)
        try:
            await client.leave_group_call(chat_id)
        except Exception:
            pass

    async def play_media(self, chat_id: int, message: Message, media: Media | Track, seek_time: int = 0) -> None:
        client = await db.get_assistant(chat_id)
        _lang = await lang.get_lang(chat_id)
        _thumb = (await thumb.generate(media) if isinstance(media, Track) else config.DEFAULT_THUMB) if config.THUMB_GEN else None

        if not media.file_path:
            return await self.play_next(chat_id)

        if media.video:
            stream = AudioVideoPiped(media.file_path, HighQualityAudio(), HighQualityVideo())
        else:
            stream = AudioPiped(media.file_path, HighQualityAudio())

        try:
            try:
                await client.change_stream(chat_id, stream)
            except Exception:
                await client.join_group_call(chat_id, stream)
            
            if not seek_time:
                media.time = 1
                await db.add_call(chat_id)
                text = _lang["play_media"].format(media.url, media.title, media.duration, media.user)
                keyboard = buttons.controls(chat_id)
                try:
                    if _thumb:
                        await message.edit_media(media=InputMediaPhoto(media=_thumb, caption=text), reply_markup=keyboard)
                    else:
                        await message.edit_text(text, reply_markup=keyboard)
                except Exception:
                    if _thumb:
                        sent = await app.send_photo(chat_id, photo=_thumb, caption=text, reply_markup=keyboard)
                    else:
                        sent = await app.send_message(chat_id, text=text, reply_markup=keyboard)
                    media.message_id = sent.id
        except Exception:
            await self.play_next(chat_id)

    async def play_next(self, chat_id: int) -> None:
        curr = queue.get_current(chat_id)
        media = queue.get_next(chat_id)
        autoplay = await db.is_autoplay(chat_id)
        _lang = await lang.get_lang(chat_id)
        
        if not media and not autoplay:
            return await self.stop(chat_id)
        elif autoplay and not media:
            media = await yt.get_next(curr.id)
            media.user = _lang["autoplay"]
            queue.force_add(chat_id, media)

        msg = await app.send_message(chat_id, _lang["play_next"])
        if not media.file_path:
            media.file_path = await yt.download(media.id, video=media.video)
        media.message_id = msg.id
        await self.play_media(chat_id, msg, media)

    async def decorators(self, client: PyTgCalls) -> None:
        @client.on_stream_end()
        async def on_stream_end(_, update: Update) -> None:
            await self.play_next(update.chat_id)

        @client.on_kicked()
        @client.on_closed_voice_chat()
        async def leave_handler(_, chat_id: int) -> None:
            await self.stop(chat_id)

    async def boot(self) -> None:
        for ub in userbot.clients:
            client = PyTgCalls(ub)
            await client.start()
            self.clients.append(client)
            await self.decorators(client)
        logger.info("PyTgCalls started.")
      
