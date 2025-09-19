# handlers/submission.py
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
import config
import database
import re
from datetime import datetime

CHANNEL_LINK_RE = re.compile(r"(https?://t\.me/[\w\d_]+)")

# ------------------------------
# Step 1: Handle submission input
# ------------------------------
@Client.on_message(filters.private & (filters.forwarded | filters.text))
async def handle_submission(client: Client, message: Message):
    user_id = message.from_user.id

    # Forwarded post case
    if message.forward_from_chat and message.forward_from_chat.type.name == "CHANNEL":
        channel = message.forward_from_chat
        channel_id = channel.id
        username = channel.username or "private"
        title = channel.title
    else:
        # Extract from link
        match = CHANNEL_LINK_RE.search(message.text or "")
        if not match:
            return  # ignore unrelated messages
        link = match.group(1)
        try:
            channel = await client.get_chat(link)
            channel_id = channel.id
            username = channel.username or "private"
            title = channel.title
        except Exception as e:
            return await message.reply_text(f"❌ Invalid or inaccessible channel link.\n\n{e}")

    # Step 2: Subscriber check
    try:
        subs_count = await client.get_chat_members_count(channel_id)
    except Exception as e:
        return await message.reply_text(f"❌ Couldn’t fetch subscriber count. Ensure I’m an admin in the channel.\n\n{e}")

    if subs_count < config.MIN_SUBSCRIBERS:
        return await message.reply_text(
            f"❌ Your channel <b>{title}</b> has <b>{subs_count}</b> subscribers.\n"
            f"Minimum required: <b>{config.MIN_SUBSCRIBERS}</b>.\n\n"
            "Please grow your channel and try again.",
            parse_mode=ParseMode.HTML
        )

    # Step 3: Ask for subscriber range first
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("500 – 999 subs", callback_data=f"range:500-999:{channel_id}")],
            [InlineKeyboardButton("1k – 5k subs", callback_data=f"range:1000-5000:{channel_id}")],
            [InlineKeyboardButton("5k – 10k subs", callback_data=f"range:5000-10000:{channel_id}")],
            [InlineKeyboardButton("10k+ subs", callback_data=f"range:10000+:{channel_id}")]
        ]
    )

    await message.reply_text(
        f"✅ Your channel <b>{title}</b> has <b>{subs_count}</b> subscribers.\n\n"
        "Now select your subscriber range:",
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )


# ------------------------------
# Step 4: Handle subscriber range choice
# ------------------------------
@Client.on_callback_query(filters.regex(r"^range:([\d\+\-]+):(-?\d+)$"))
async def cb_range(client: Client, cq: CallbackQuery):
    subs_range = cq.matches[0].group(1)
    channel_id = int(cq.matches[0].group(2))
    user_id = cq.from_user.id

    try:
        channel = await client.get_chat(channel_id)
        subs_count = await client.get_chat_members_count(channel_id)
    except Exception as e:
        return await cq.message.edit_text(f"❌ Error fetching channel info: {e}")

    # Verify range
    valid = False
    if subs_range == "500-999" and 500 <= subs_count <= 999:
        valid = True
    elif subs_range == "1000-5000" and 1000 <= subs_count <= 5000:
        valid = True
    elif subs_range == "5000-10000" and 5000 <= subs_count <= 10000:
        valid = True
    elif subs_range == "10000+" and subs_count >= 10000:
        valid = True

    if not valid:
        return await cq.message.edit_text(
            f"❌ Your subscriber count <b>{subs_count}</b> does not match the selected range <b>{subs_range}</b>.\n\n"
            "Please restart submission and select the correct range.",
            parse_mode=ParseMode.HTML
        )

    # Step 5: Ask for niche (only if valid range)
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📰 News & Updates", callback_data=f"cat:news:{channel_id}:{subs_range}")],
            [InlineKeyboardButton("💻 Technology & Internet", callback_data=f"cat:tech:{channel_id}:{subs_range}")],
            [InlineKeyboardButton("🎭 Entertainment & Lifestyle", callback_data=f"cat:ent:{channel_id}:{subs_range}")],
            [InlineKeyboardButton("🎬 Movies & Series", callback_data=f"cat:movies:{channel_id}:{subs_range}")],
            [InlineKeyboardButton("⚽ Sports", callback_data=f"cat:sports:{channel_id}:{subs_range}")],
            [InlineKeyboardButton("💸 Forex, Betting & Crypto", callback_data=f"cat:forex:{channel_id}:{subs_range}")]
        ]
    )

    await cq.message.edit_text(
        f"✅ Subscriber range verified: <b>{subs_range}</b>\n\n"
        "Now choose a niche for your channel:",
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )


# ------------------------------
# Step 6: Handle category choice
# ------------------------------
@Client.on_callback_query(filters.regex(r"^cat:(\w+):(-?\d+):([\d\+\-]+)$"))
async def cb_category(client: Client, cq: CallbackQuery):
    category = cq.matches[0].group(1)
    channel_id = int(cq.matches[0].group(2))
    subs_range = cq.matches[0].group(3)
    user_id = cq.from_user.id

    try:
        channel = await client.get_chat(channel_id)
        subs_count = await client.get_chat_members_count(channel_id)
    except Exception as e:
        return await cq.message.edit_text(f"❌ Error fetching channel info: {e}")

    data = {
        "user_id": user_id,
        "channel_id": channel.id,
        "username": channel.username,
        "title": channel.title,
        "category": category,
        "subs_range": subs_range,
        "subs_count": subs_count,
        "status": "PENDING",
        "added_at": datetime.utcnow()
    }

    # ✅ Save submission in DB
    database.save_submission(data)

    ref_id = hex(hash(f"{user_id}{channel.id}{datetime.utcnow()}"))[2:12]

    # Confirmation to user
    await cq.message.edit_text(
        f"✅ Your channel <b>{channel.title}</b> has been submitted for review!\n\n"
        f"Reference ID: <code>{ref_id}</code>",
        parse_mode=ParseMode.HTML
    )

    # Notify main admins
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve:{channel.id}"),
                InlineKeyboardButton("❌ Deny", callback_data=f"deny:{channel.id}")
            ]
        ]
    )
    for admin_id in config.EVALOP:  # use your main admin / owner
        try:
            await client.send_message(
                admin_id,
                f"📩 <b>New Channel Submission</b>\n\n"
                f"• Title: <b>{channel.title}</b>\n"
                f"• Username: @{channel.username}\n"
                f"• Subs: {subs_count}\n"
                f"• Range: {subs_range}\n"
                f"• Category: {category}\n"
                f"• Submitted by: <a href='tg://user?id={user_id}'>{cq.from_user.first_name}</a>\n"
                f"• Ref ID: <code>{ref_id}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=kb
            )
        except Exception:
            pass


# ------------------------------
# Step 7: Approve / Deny by Admin
# ------------------------------
@Client.on_callback_query(filters.regex(r"^(approve|deny):(-?\d+)$"))
async def cb_admin_action(client: Client, cq: CallbackQuery):
    action = cq.matches[0].group(1)
    channel_id = int(cq.matches[0].group(2))

    if cq.from_user.id not in config.ADMINS:
        return await cq.answer("❌ Not authorized.", show_alert=True)

    status = "APPROVED" if action == "approve" else "DENIED"
    database.update_status(channel_id, status)

    await cq.message.edit_text(f"Channel <code>{channel_id}</code> has been {status}.", parse_mode=ParseMode.HTML)

    # Notify owner
    ch = database.get_channel_by_id(channel_id)
    if ch:
        owner_id = ch["user_id"]
        try:
            if action == "approve":
                # Enhanced approval notification for user
                message_text = (
                    f"🎉 **CONGRATULATIONS!** 🎉\n\n"
                    f"📢 Your channel **{ch['title']}** has been **APPROVED**!\n\n"
                    f"✅ **What this means for you:**\n"
                    f"• Your channel is now part of our growing network\n"
                    f"• You'll receive regular cross-promotion opportunities\n"
                    f"• Your subscriber count will grow faster\n"
                    f"• You'll get more engagement on your content\n\n"
                    f"🌟 **Next Steps:**\n"
                    f"• Join our official channel for updates and tips\n"
                    f"• Keep your content quality high for better results\n"
                    f"• Invite other channel owners to join our platform\n\n"
                    f"Thank you for choosing us! 🚀"
                )
                
                # Create button that redirects to the approved channel
                buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📢 Join Our Official Channel", url=config.APPROVED_CHANNEL_LINK)]
                ])
                
                await client.send_message(
                    owner_id,
                    message_text,
                    reply_markup=buttons,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                # Enhanced approval notification for admins
                admin_message_text = (
                    f"✅ **CHANNEL APPROVED** ✅\n\n"
                    f"**Channel Details:**\n"
                    f"• ID: `{channel_id}`\n"
                    f"• Title: **{ch['title']}**\n"
                    f"• Username: @{ch.get('username', 'Private')}\n\n"
                    f"**Approval Status:** ✅ APPROVED\n"
                    f"**Action Taken:** Added to cross-promotion network\n"
                    f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"The channel has been successfully verified and added to the database."
                )
                
                # Create button that goes back to admin panel
                admin_buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("↩ Back to Admin Panel", callback_data="admin_panel")]
                ])
                
                # Send to all admins except the one who performed the action
                for admin_id in config.ADMINS:
                    if admin_id != cq.from_user.id:
                        try:
                            await client.send_message(
                                chat_id=admin_id,
                                text=admin_message_text,
                                reply_markup=admin_buttons,
                                parse_mode=ParseMode.MARKDOWN
                            )
                        except Exception as e:
                            print(f"Failed to send approval notification to admin {admin_id}: {e}")
            
            else:  # Denied
                # Standard denial notification
                await client.send_message(
                    owner_id,
                    f"📢 Your channel <b>{ch['title']}</b> has been <b>{status}</b>.",
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            print(f"Failed to send notification to owner {owner_id}: {e}")