import asyncio

from pyrogram import enums, errors, types

from anony import app, config, db, logger, queue, yt
from anony.helpers import utils


def checkUB(play):
    async def wrapper(_, m: types.Message):
        if not m.from_user:
            return await m.reply_text(m.lang["play_user_invalid"])

        chat_id = m.chat.id
        if m.chat.type != enums.ChatType.SUPERGROUP:
            await m.reply_text(m.lang["play_chat_invalid"])
            return await app.leave_chat(chat_id)

        if not m.reply_to_message and (
            len(m.command) < 2 or (len(m.command) == 2 and m.command[1] == "-f")
        ):
            return await m.reply_text(m.lang["play_usage"])

        if len(queue.get_queue(chat_id)) >= config.QUEUE_LIMIT:
            return await m.reply_text(m.lang["play_queue_full"].format(config.QUEUE_LIMIT))

        force = m.command[0].endswith("force") or (
            len(m.command) > 1 and "-f" in m.command[1]
        )
        video = m.command[0][0] == "v" and config.VIDEO_PLAY
        url = utils.get_url(m)
        m3u8 = url and not yt.valid(url)

        play_mode = await db.get_play_mode(chat_id)
        if play_mode or force:
            adminlist = await db.get_admins(chat_id)
            if (
                m.from_user.id not in adminlist
                and not await db.is_auth(chat_id, m.from_user.id)
                and not m.from_user.id in app.sudoers
            ):
                return await m.reply_text(m.lang["play_admin"])

        if chat_id not in db.active_calls:
            client = await db.get_client(chat_id)
            try:
                member = await app.get_chat_member(chat_id, client.id)
                if member.status in [
                    enums.ChatMemberStatus.BANNED,
                    enums.ChatMemberStatus.RESTRICTED,
                ]:
                    try:
                        await app.unban_chat_member(chat_id=chat_id, user_id=client.id)
                    except Exception:
                        return await m.reply_text(
                            m.lang["play_banned"].format(
                                app.name,
                                client.id,
                                client.mention,
                                f"@{client.username}" if client.username else None,
                            )
                        )
            except errors.ChatAdminRequired:
                return await m.reply_text(m.lang["admin_required"])
            except (errors.UserNotParticipant, errors.exceptions.bad_request_400.UserNotParticipant):
                if m.chat.username:
                    invite_link = m.chat.username
                    try:
                        await client.resolve_peer(invite_link)
                    except Exception:
                        pass
                else:
                    try:
                        invite_link = (await app.get_chat(chat_id)).invite_link
                        if not invite_link:
                            invite_link = await app.export_chat_invite_link(chat_id)
                    except errors.ChatAdminRequired:
                        return await m.reply_text(m.lang["admin_required"])
                    except Exception as ex:
                        return await m.reply_text(
                            m.lang["play_invite_error"].format(type(ex).__name__)
                        )

                umm = await m.reply_text(m.lang["play_invite"].format(app.name))
                await asyncio.sleep(2)

                joined = False
                
                # Loop to try joining and switch assistants if FloodWait occurs
                for _ in range(5):  
                    try:
                        await client.join_chat(invite_link)
                        joined = True
                        break
                    except errors.UserAlreadyParticipant:
                        joined = True
                        break
                    except errors.InviteRequestSent:
                        await asyncio.sleep(2)
                        try:
                            await app.approve_chat_join_request(chat_id, client.id)
                            joined = True
                            break
                        except errors.HideRequesterMissing:
                            joined = True
                            break
                        except Exception as ex:
                            return await umm.edit_text(
                                m.lang["play_invite_error"].format(type(ex).__name__)
                            )
                    except errors.FloodWait as fw:
                        logger.warning(f"Assistant {client.id} hit FloodWait of {fw.value}s in {chat_id}. Switching assistant...")
                        await db.cycle_assistant(chat_id)
                        client = await db.get_client(chat_id)
                        await asyncio.sleep(1)
                        continue
                    except Exception as ex:
                        logger.error(f"Error joining chat - {chat_id}: {ex}")
                        return await umm.edit_text(
                            m.lang["play_invite_error"].format(type(ex).__name__)
                        )

                if not joined:
                    return await umm.edit_text("All assistant accounts are currently limited by Telegram (FloodWait). Please try again later.")

                await umm.delete()
                await client.resolve_peer(chat_id)

        if await db.get_cmd_delete(chat_id):
            try:
                await m.delete()
            except Exception:
                pass

        return await play(_, m, force, m3u8, video, url)

    return wrapper
    
