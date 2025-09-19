# handlers/start.py
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
import config
import database  # Add this import
from datetime import datetime

# Import admin panel from admin.py
from handlers.admin import get_admin_panel

# -----------------------------
# Helpers
# -----------------------------
def main_keyboard(user_id=None):
    keyboard = [
        [InlineKeyboardButton("➕ Add Channel", callback_data="add_channel")],
        [InlineKeyboardButton("📂 My Channels", callback_data="my_channels:0")],
        [InlineKeyboardButton("❓ Help", callback_data="help")],
        [InlineKeyboardButton("📺 Submission Guide", url=config.SUBMISSION_GUIDE_URL or "")],
        [InlineKeyboardButton("🔗 Support", url=config.SUPPORT_CHAT or config.SUPPORT_CHANNEL or "https://t.me/Megahubbots")],
    ]
    
    # ✅ Add Admin Panel button for admins
    if user_id and user_id in config.ADMINS:
        keyboard.insert(0, [InlineKeyboardButton("👨‍💼 Admin Panel", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(keyboard)

# -----------------------------
# /start command
# -----------------------------
@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    # Save user to database
    database.save_user(message.from_user.id, message.from_user.username or "")
    
    caption = (
        f"👋 Hello <b>{message.from_user.first_name}</b>,\n\n"
        f"Welcome to <b>{config.BOT_NAME}</b> 🚀\n\n"
        f"Grow your Telegram channels for free through cross-promotions!\n\n"
        f"Use the buttons below to Add your channel, view your channels or get help."
    )

    keyboard = main_keyboard(message.from_user.id)

    try:
        if getattr(config, "START_MSG_VID", None):
            await message.reply_video(
                video=config.START_MSG_VID,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        elif getattr(config, "START_MSG_PHOTO", None):
            await message.reply_photo(
                photo=config.START_MSG_PHOTO,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        else:
            await message.reply_text(
                caption,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
    except Exception as e:
        print(f"[ERROR /start] {e}")
        await message.reply_text(
            caption,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

# -----------------------------
# Callback handlers
# -----------------------------

# Admin Panel
@Client.on_callback_query(filters.regex(r"^admin_panel$"))
async def admin_panel_cb(client: Client, cq: CallbackQuery):
    if cq.from_user.id not in config.ADMINS:
        await cq.answer("❌ Admin access required!", show_alert=True)
        return
    
    await cq.message.edit_text(
        "👨‍💼 **Admin Panel**\n\n"
        "Select an option:",
        reply_markup=get_admin_panel(),
        parse_mode=ParseMode.HTML
    )

# Add Channel
@Client.on_callback_query(filters.regex(r"^add_channel$"))
async def cb_add_channel(client: Client, cq: CallbackQuery):
    await cq.answer()
    text = (
        f"<b>➕ Submit Your Channel</b>\n\n"
        "To submit your channel for review, please do one of the following:\n\n"
        "1. Forward the most recent post from your channel to me (preferred), OR\n"
        "2. Send your channel link (e.g., https://t.me/yourchannelusername)\n\n"
        "Make sure the bot is an admin in your channel with permission to post.\n\n"
        f"Minimum required subscribers: <b>{config.MIN_SUBSCRIBERS}</b>.\n\n"
        "When you've forwarded/sent the link, I'll proceed with asking for category & type."
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="go_back_start")]])
    await cq.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

# My Channels - FIXED: Now uses database instead of config.adminlist
@Client.on_callback_query(filters.regex(r"^my_channels:(\d+)$"))
async def cb_my_channels(client: Client, cq: CallbackQuery):
    await cq.answer()
    page = int(cq.matches[0].group(1))
    user_id = cq.from_user.id

    # Get ONLY approved channels from database
    channels = database.get_user_channels(user_id, status_filter="APPROVED")
    total = len(channels)

    if total == 0:
        text = (
            "<b>📂 My Channels</b>\n\n"
            "You don't have any approved channels yet.\n\n"
            "Submit a channel using the button below and wait for admin approval."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Submit Channel", callback_data="add_channel")],
            [InlineKeyboardButton("↩ Back to Main", callback_data="go_back_start")]
        ])
        return await cq.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    if page < 0: page = 0
    if page >= total: page = total - 1

    channel = channels[page]
    created = channel.get("added_at")
    created_str = created.strftime("%Y-%m-%d %H:%M:%S") if hasattr(created, 'strftime') else str(created or "N/A")

    text = (
        f"📘 <b>{channel.get('title', 'Channel')}</b>\n\n"
        f"• ID: <code>{channel.get('channel_id')}</code>\n"
        f"• Username: @{channel.get('username','unknown')}\n"
        f"• Category: {channel.get('category','N/A')}\n"
        f"• Subscribers: {channel.get('subs_count', 'N/A')}\n"
        f"• Subscriber Range: {channel.get('subs_range', 'N/A')}\n"
        f"• Status: {channel.get('status', 'N/A')}\n\n"
        f"📌 This channel was added on {created_str}"
    )

    buttons = []
    buttons.append([InlineKeyboardButton("🗑 Remove Channel", callback_data=f"remove:{channel.get('channel_id')}")])
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("⬅ Prev", callback_data=f"my_channels:{page-1}"))
    nav.append(InlineKeyboardButton("↩ Back to Main", callback_data="go_back_start"))
    if page < total - 1: nav.append(InlineKeyboardButton("Next ➡", callback_data=f"my_channels:{page+1}"))
    buttons.append(nav)

    try:
        await cq.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        await cq.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

# Remove Channel - FIXED: Now uses database
@Client.on_callback_query(filters.regex(r"^remove:(-?\d+)$"))
async def cb_remove_channel(client: Client, cq: CallbackQuery):
    await cq.answer()
    channel_id = int(cq.matches[0].group(1))
    user_id = cq.from_user.id
    
    # Remove channel from database
    success = database.remove_channel(user_id, channel_id)
    
    if success:
        await cq.message.edit_text(
            "✅ Channel removed successfully.", 
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📂 My Channels", callback_data="my_channels:0")],
                [InlineKeyboardButton("↩ Back to Main", callback_data="go_back_start")]
            ])
        )
    else:
        await cq.message.edit_text(
            "❌ Could not remove channel (not found or DB error).", 
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📂 My Channels", callback_data="my_channels:0")],
                [InlineKeyboardButton("↩ Back to Main", callback_data="go_back_start")]
            ])
        )

# Help
@Client.on_callback_query(filters.regex(r"^help$"))
async def cb_help(client: Client, cq: CallbackQuery):
    await cq.answer()
    text = (
        "<b>📘 PromosFatherBot Help</b>\n\n"
        "🔹 To submit your channel:\n"
        "   1. Add this Bot in your channel with Admin Post Rights\n"
        "   2. Use '➕ Add Channel'\n"
        "   3. Forward a message from your channel to here\n"
        "   4. Select a category when prompted\n"
        "   5. Wait for admin approval\n\n"
        f"❗️ Requirements:\n"
        f"- At least {config.MIN_SUBSCRIBERS} subscribers\n"
        "- The bot must be admin in your channel\n"
        "- You must not delete cross promos from the bot they will be deleted automatically after a time range\n"
        "- No prohibited content\n"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="go_back_start")]])
    await cq.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

# Go back
@Client.on_callback_query(filters.regex(r"^go_back_start$"))
async def cb_go_back(client: Client, cq: CallbackQuery):
    await cq.answer()
    keyboard = main_keyboard(cq.from_user.id)
    await cq.message.edit_text(
        f"👋 Hello <b>{cq.from_user.first_name}</b>,\n\n"
        f"Welcome to <b>{config.BOT_NAME}</b> 🚀\n\n"
        f"Use the buttons below to Add your channel, view your channels or get help.",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )