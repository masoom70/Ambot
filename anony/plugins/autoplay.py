from pyrogram import errors, filters, types

from anony import app, config, db, lang
from anony.helpers import admin_check, buttons


@app.on_message(filters.command(["autoplay"]) & ~app.bl_users)
@lang.language()
@admin_check
async def _autoplay(_, m: types.Message):
    if not await db.get_call(m.chat.id):
        return await m.reply_text(m.lang["not_playing"])

    status = await db.is_autoplay(m.chat.id)
    if status: txt = m.lang["enabled"]
    else: txt = m.lang["disabled"]

    await m.reply_photo(
        photo=config.START_IMG,
        caption=m.lang["auto_play"].format(txt),
        reply_markup=buttons.auto_play(txt),
    )


@app.on_callback_query(filters.regex("autoplay") & ~app.bl_users)
@lang.language()
@admin_check
async def _autoplay_cb(_, cq: types.CallbackQuery):
    chat_id = cq.message.chat.id
    if not await db.get_call(chat_id):
        try:
            return await cq.answer(cq.lang["not_playing"], show_alert=True)
        except errors.QueryIdInvalid:
            try:
                await cq.message.delete()
            except Exception:
                pass
            return

    status = await db.is_autoplay(chat_id)
    _status = not status
    if _status: txt = cq.lang["enabled"]
    else: txt = cq.lang["disabled"]

    await db.set_autoplay(chat_id, _status)
    await cq.edit_message_text(
        text=cq.lang["auto_play"].format(txt),
        reply_markup=buttons.auto_play(txt),
    )
    
