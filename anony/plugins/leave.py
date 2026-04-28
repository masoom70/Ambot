import asyncio
from pyrogram import enums, filters, types
from anony import app, db, userbot

@app.on_message(filters.command(["leaveall"]) & filters.user(app.owner))
async def _leaveall(_, m: types.Message):
    if len(m.command) < 2:
        return await m.reply_text("Which assistant? (1-3)")
    
    try:
        num = int(m.command[1])
        assistant = getattr(userbot, ["one", "two", "three"][num-1], None)
        if not assistant:
            raise ValueError
    except (ValueError, IndexError):
        return await m.reply_text("Invalid assistant number. Use 1, 2, or 3.")

    left, failed = 0, 0
    sent = await m.reply_text(f"Assistant {num} is leaving all chats...")

    async for dialog in assistant.get_dialogs():
        chat = dialog.chat
        if chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            continue
        if chat.id in [app.logger, -1001686672798, -1001549206010]:
            continue
        if chat.id in db.active_calls:
            continue

        try:
            await assistant.leave_chat(chat.id)
            await asyncio.sleep(2)
            left += 1
        except Exception:
            failed += 1

    await sent.edit_text(f"Assistant {num} finished.\nLeft: {left}\nFailed: {failed}")
    
