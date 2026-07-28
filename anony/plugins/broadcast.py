# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import os
import asyncio

from pyrogram import errors, filters, types

from anony import app, db, lang


@app.on_message(filters.command(["broadcast"]) & app.sudoers)
@lang.language()
async def _broadcast(_, message: types.Message):
    if not message.reply_to_message:
        return await message.reply_text(message.lang["gcast_usage"])

    msg = message.reply_to_message
    count, ucount = 0, 0
    groups, users = [], []
    sent = await message.reply_text(message.lang["gcast_start"])

    if "-nochat" not in message.command:
        groups.extend(await db.get_chats())
    if "-user" in message.command:
        users.extend(await db.get_users())
    await asyncio.sleep(5)

    failed = ""
    for chat in groups:
        try:
            (
                await msg.copy(chat, reply_markup=msg.reply_markup)
                if "-copy" in message.text
                else await msg.forward(chat)
            )
            count += 1
            await asyncio.sleep(0.1)
        except errors.FloodWait as fw:
            await asyncio.sleep(fw.value + 60)
        except Exception as ex:
            failed += f"{chat} - {ex}\n"
            continue
    await message.reply_text(f"Broadcated to {count} chats.")

    for chat in users:
        try:
            (
                await msg.copy(chat, reply_markup=msg.reply_markup)
                if "-copy" in message.text
                else await msg.forward(chat)
            )
            ucount += 1
            await asyncio.sleep(0.1)
        except errors.FloodWait as fw:
            await asyncio.sleep(fw.value + 60)
        except Exception as ex:
            failed += f"{chat} - {ex}\n"
            continue

    text = message.lang["gcast_end"].format(count, ucount)
    if failed:
        with open("errors.txt", "w") as f:
            f.write(failed)
        await message.reply_document(
            document="errors.txt",
            caption=text,
        )
        os.remove("errors.txt")
    try: await sent.delete()
    except Exception: pass
    await message.reply_text(text)


@app.on_message(filters.command(["checkbroadcaststats", "cbstats"]) & app.sudoers)
@lang.language()
async def _check_broadcast_stats(_, message: types.Message):
    groups = await db.get_chats()
    users = await db.get_users()

    sent = await message.reply_text(message.lang["cbstats_start"])

    alive_chats, dead_chats = [], []
    alive_users, dead_users = [], []

    # CHATS CHECK
    for chat in groups:
        try:
            await app.get_chat(chat)
            alive_chats.append(chat)
        except errors.FloodWait as fw:
            await asyncio.sleep(fw.value + 5)
            try:
                await app.get_chat(chat)
                alive_chats.append(chat)
            except Exception:
                dead_chats.append(chat)
        except Exception:
            dead_chats.append(chat)
        await asyncio.sleep(0.1)

    # USERS CHECK
    for user in users:
        try:
            await app.get_chat(user)
            alive_users.append(user)
        except errors.FloodWait as fw:
            await asyncio.sleep(fw.value + 5)
            try:
                await app.get_chat(user)
                alive_users.append(user)
            except Exception:
                dead_users.append(user)
        except Exception:
            dead_users.append(user)
        await asyncio.sleep(0.1)

    text = message.lang["cbstats_result"].format(
        len(groups), len(alive_chats), len(dead_chats),
        len(users), len(alive_users), len(dead_users),
    )

    failed = ""
    if dead_chats:
        failed += "Dead Chats:\n" + "\n".join(str(c) for c in dead_chats) + "\n\n"
    if dead_users:
        failed += "Dead Users:\n" + "\n".join(str(u) for u in dead_users) + "\n\n"

    if "-clean" in message.command:
        for chat in dead_chats:
            await db.rm_chat(chat)
        for user in dead_users:
            await db.rm_user(user)
        text += message.lang["cbstats_cleaned"].format(len(dead_chats), len(dead_users))

    try: await sent.delete()
    except Exception: pass

    if failed:
        with open("dead_list.txt", "w") as f:
            f.write(failed)
        await message.reply_document(
            document="dead_list.txt",
            caption=text,
        )
        os.remove("dead_list.txt")
    else:
        await message.reply_text(text)
