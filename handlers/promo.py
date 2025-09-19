# handlers/promo.py 
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, ForceReply
from pyrogram.enums import ParseMode
import asyncio
import database
import config
from pymongo import MongoClient
from datetime import datetime

# Import templates
from utils.crosstempl import get_promo_templates, generate_promo_message, generate_promo_buttons, get_template_selection_keyboard, generate_grid_promo_buttons

# -----------------------------
# MongoDB Connection
# -----------------------------
client = MongoClient(config.MONGO_DB_URI)
db = client[config.MONGO_DB_NAME]  # Use DB name from config

# Temporary in-memory selection store (per admin)
selected_channels = {}

# Module-level category names
CATEGORY_NAMES = {
    "news": "📰 News & Updates",
    "tech": "💻 Technology & Internet",
    "ent": "🎭 Entertainment & Lifestyle",
    "movies": "🎬 Movies & Series",
    "sports": "⚽ Sports",
    "forex": "💸 Forex, Betting & Crypto"
}

# Subscriber ranges
SUBS_RANGES = {
    "500-999": "500 – 999 subs",
    "1k-5k": "1k – 5k subs", 
    "5k-10k": "5k – 10k subs",
    "10k+": "10k+ subs"
}

# ---- Step 1: Admin chooses category ----
@Client.on_callback_query(filters.regex(r"^send_promos$"))
async def cb_send_promos(client, callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Admin access required!", show_alert=True)
        return

    categories = list(CATEGORY_NAMES.keys())

    buttons = [[InlineKeyboardButton(CATEGORY_NAMES[cat], callback_data=f"promo_category:{cat}")]
               for cat in categories]
    buttons.append([InlineKeyboardButton("↩ Back to Admin Panel", callback_data="admin_panel")])

    try:
        await callback.message.edit_text(
            "📢 **Choose a category to run the cross-promo:**",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        # Handle cases where message content is the same
        if "MESSAGE_NOT_MODIFIED" not in str(e):
            await callback.answer("An error occurred. Please try again.", show_alert=True)
            print(f"Error in cb_send_promos: {e}")

@Client.on_message(filters.command("sendpromos") & filters.user(config.ADMINS))
async def start_promo(client, message):
    # Construct a fake CallbackQuery object to reuse the callback logic
    class DummyCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
            self.data = "send_promos"

    await cb_send_promos(client, DummyCallback(message, message.from_user))

# ---- Step 2: Choose Subscriber Range ----
@Client.on_callback_query(filters.regex(r"^promo_category:(.+)"))
async def choose_subs_range(client, callback: CallbackQuery):
    category = callback.data.split(":", 1)[1]
    
    admin_id = callback.from_user.id
    selected_channels[admin_id] = {
        "category": category,
        "selected": set()
    }

    # Create buttons for subscriber ranges
    buttons = []
    for range_key, range_name in SUBS_RANGES.items():
        buttons.append([InlineKeyboardButton(range_name, callback_data=f"promo_range:{range_key}:{category}")])
    
    buttons.append([InlineKeyboardButton("↩ Back to Categories", callback_data="send_promos")])

    try:
        await callback.message.edit_text(
            f"📊 **Select Subscriber Range for {CATEGORY_NAMES.get(category, category)}**\n\n"
            "Choose which subscriber range you want to target:",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        if "MESSAGE_NOT_MODIFIED" not in str(e):
            await callback.answer("An error occurred. Please try again.", show_alert=True)
            print(f"Error in choose_subs_range: {e}")

# ---- Step 3: Select Channels by Range ----
@Client.on_callback_query(filters.regex(r"^promo_range:([\w\+-]+):(.+)"))
async def list_channels_by_range(client, callback: CallbackQuery):
    subs_range = callback.matches[0].group(1)
    category = callback.matches[0].group(2)
    
    admin_id = callback.from_user.id
    selected_channels[admin_id] = {
        "category": category,
        "subs_range": subs_range,
        "selected": set()
    }

    # Get all channels in this category
    all_channels = database.get_channels_by_category(category)
    
    # Filter channels by subscriber range
    filtered_channels = []
    for channel in all_channels:
        subs_count = channel.get('subs_count', 0)
        
        if subs_range == "500-999" and 500 <= subs_count <= 999:
            filtered_channels.append(channel)
        elif subs_range == "1k-5k" and 1000 <= subs_count <= 5000:
            filtered_channels.append(channel)
        elif subs_range == "5k-10k" and 5000 <= subs_count <= 10000:
            filtered_channels.append(channel)
        elif subs_range == "10k+" and subs_count >= 10000:
            filtered_channels.append(channel)

    if not filtered_channels:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("↩ Choose Different Range", callback_data=f"promo_category:{category}")],
            [InlineKeyboardButton("↩ Back to Categories", callback_data="send_promos")]
        ])
        try:
            await callback.message.edit_text(
                f"❌ No channels found in {CATEGORY_NAMES.get(category, category)} "
                f"with {SUBS_RANGES.get(subs_range, subs_range)}.",
                reply_markup=kb,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            if "MESSAGE_NOT_MODIFIED" not in str(e):
                await callback.answer("An error occurred. Please try again.", show_alert=True)
                print(f"Error in list_channels_by_range (no channels): {e}")
        return

    # Build buttons with ON/OFF for selection
    buttons = []
    for ch in filtered_channels:
        cid = ch["channel_id"]
        title = ch.get("title", "Channel")
        subs = ch.get("subs_count", 0)
        buttons.append([InlineKeyboardButton(f"❌ {title} ({subs} subs)", callback_data=f"toggle_channel:{cid}")])

    buttons.append([InlineKeyboardButton("🔒 Done Selecting", callback_data="done_selecting")])
    buttons.append([InlineKeyboardButton("↩ Choose Different Range", callback_data=f"promo_category:{category}")])
    buttons.append([InlineKeyboardButton("↩ Back to Categories", callback_data="send_promos")])

    msg_text = (
        f"🎬 **Available Channels in {CATEGORY_NAMES.get(category, category)} "
        f"({SUBS_RANGES.get(subs_range, subs_range)}):**\n\n" +
        "\n".join([f"• {c.get('title','Unknown')} (@{c.get('username','private')}) - {c.get('subs_count',0)} subs" 
                  for c in filtered_channels])
    )
    
    try:
        await callback.message.edit_text(msg_text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
    except Exception as e:
        if "MESSAGE_NOT_MODIFIED" not in str(e):
            await callback.answer("An error occurred. Please try again.", show_alert=True)
            print(f"Error in list_channels_by_range: {e}")

# ---- Toggle channel selection ----
@Client.on_callback_query(filters.regex(r"^toggle_channel:(-?\d+)"))
async def toggle_channel(client, callback: CallbackQuery):
    channel_id = int(callback.data.split(":", 1)[1])
    admin_id = callback.from_user.id

    if admin_id not in selected_channels:
        await callback.answer("Please start over with /sendpromos", show_alert=True)
        return

    selected_set = selected_channels[admin_id]["selected"]
    if channel_id in selected_set:
        selected_set.remove(channel_id)
        await callback.answer("Channel deselected", show_alert=False)
    else:
        selected_set.add(channel_id)
        await callback.answer("Channel selected", show_alert=False)

    # refresh markup
    category = selected_channels[admin_id]["category"]
    subs_range = selected_channels[admin_id]["subs_range"]

    all_channels = database.get_channels_by_category(category)
    filtered_channels = []
    for channel in all_channels:
        subs_count = channel.get('subs_count', 0)
        
        if subs_range == "500-999" and 500 <= subs_count <= 999:
            filtered_channels.append(channel)
        elif subs_range == "1k-5k" and 1000 <= subs_count <= 5000:
            filtered_channels.append(channel)
        elif subs_range == "5k-10k" and 5000 <= subs_count <= 10000:
            filtered_channels.append(channel)
        elif subs_range == "10k+" and subs_count >= 10000:
            filtered_channels.append(channel)

    buttons = []
    for ch in filtered_channels:
        cid = ch["channel_id"]
        title = ch.get("title", "Channel")
        subs = ch.get("subs_count", 0)
        text = f"✅ {title} ({subs} subs)" if cid in selected_set else f"❌ {title} ({subs} subs)"
        buttons.append([InlineKeyboardButton(text, callback_data=f"toggle_channel:{cid}")])

    buttons.append([InlineKeyboardButton("🔒 Done Selecting", callback_data="done_selecting")])
    buttons.append([InlineKeyboardButton("↩ Choose Different Range", callback_data=f"promo_category:{category}")])
    buttons.append([InlineKeyboardButton("↩ Back to Categories", callback_data="send_promos")])

    try:
        await callback.message.edit_reply_markup(InlineKeyboardMarkup(buttons))
    except Exception as e:
        if "MESSAGE_NOT_MODIFIED" not in str(e):
            await callback.answer("An error occurred. Please try again.", show_alert=True)
            print(f"Error in toggle_channel: {e}")

# ---- Step 4: Choose Template ----
@Client.on_callback_query(filters.regex(r"^done_selecting$"))
async def choose_template(client, callback: CallbackQuery):
    admin_id = callback.from_user.id
    if admin_id not in selected_channels or not selected_channels[admin_id]["selected"]:
        await callback.answer("❌ No channels selected!", show_alert=True)
        return

    selected_channels[admin_id]["final"] = list(selected_channels[admin_id]["selected"])

    try:
        await callback.message.edit_text(
            "🎨 **Choose a Promo Template**\n\n"
            "Select the style for your cross-promotion post:",
            reply_markup=get_template_selection_keyboard(),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        if "MESSAGE_NOT_MODIFIED" not in str(e):
            await callback.answer("An error occurred. Please try again.", show_alert=True)
            print(f"Error in choose_template: {e}")

# ---- Step 5: Set Duration ----
@Client.on_callback_query(filters.regex(r"^promo_template:(.+)"))
async def set_promo_duration(client, callback: CallbackQuery):
    template_id = callback.data.split(":", 1)[1]
    admin_id = callback.from_user.id
    
    if admin_id not in selected_channels:
        await callback.answer("❌ Please start over!", show_alert=True)
        return
    
    selected_channels[admin_id]["template"] = template_id

    duration_buttons = [
        [InlineKeyboardButton("⏰ 1 Hour", callback_data="promo_duration:3600")],
        [InlineKeyboardButton("⏰ 3 Hours", callback_data="promo_duration:10800")],
        [InlineKeyboardButton("⏰ 6 Hours", callback_data="promo_duration:21600")],
        [InlineKeyboardButton("⏰ 12 Hours", callback_data="promo_duration:43200")],
        [InlineKeyboardButton("⏰ 24 Hours", callback_data="promo_duration:86400")],
        [InlineKeyboardButton("↩ Back to Templates", callback_data="done_selecting")]
    ]

    selected_count = len(selected_channels[admin_id]["selected"])
    category = selected_channels[admin_id]["category"]
    
    try:
        await callback.message.edit_text(
            f"✅ Selected {selected_count} channels in {CATEGORY_NAMES.get(category, category)}\n\n"
            "⏱ **How long should the promo post last before auto-deletion?**",
            reply_markup=InlineKeyboardMarkup(duration_buttons),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        if "MESSAGE_NOT_MODIFIED" not in str(e):
            await callback.answer("An error occurred. Please try again.", show_alert=True)
            print(f"Error in set_promo_duration: {e}")

# ---- Step 6: Send Promo ----
@Client.on_callback_query(filters.regex(r"^promo_duration:(\d+)$"))
async def create_promo_post(client, callback: CallbackQuery):
    admin_id = callback.from_user.id
    duration = int(callback.data.split(":")[1])

    if admin_id not in selected_channels or not selected_channels[admin_id].get("final"):
        await callback.answer("❌ Please select channels first.", show_alert=True)
        return

    channel_ids = selected_channels[admin_id]["final"]
    template_id = selected_channels[admin_id].get("template", "template1")
    chosen_channels = [database.get_channel_by_id(cid) for cid in channel_ids if database.get_channel_by_id(cid)]
    
    if not chosen_channels:
        await callback.answer("❌ No valid channels found.", show_alert=True)
        return

    # Get bot username for the "Add Your Channel" button
    bot_username = (await client.get_me()).username
    
    # Generate promo message and buttons using template
    promo_text = generate_promo_message(template_id, chosen_channels, selected_channels[admin_id]["category"], config.BOT_NAME)
    
    # Use special buttons for grid template
    if template_id == "template6":
        promo_buttons = generate_grid_promo_buttons(chosen_channels, bot_username)
    else:
        promo_buttons = generate_promo_buttons(chosen_channels, bot_username)

    success_count = 0
    failed_channels = []
    last_promo_id = None

    for channel in chosen_channels:
        target = f"@{channel['username']}" if channel.get("username") else channel["channel_id"]
        try:
            # Check if PROMO_IMAGE exists and is valid
            promo_image = getattr(config, "PROMO_IMAGE", None)
            if promo_image:
                try:
                    # Try to send as photo first
                    sent = await client.send_photo(
                        chat_id=target,
                        photo=promo_image,
                        caption=promo_text,
                        reply_markup=promo_buttons,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as photo_error:
                    # If photo fails, fall back to text message
                    print(f"Photo send failed for {target}: {photo_error}. Falling back to text.")
                    sent = await client.send_message(
                        chat_id=target,
                        text=promo_text,
                        reply_markup=promo_buttons,
                        parse_mode=ParseMode.MARKDOWN
                    )
            else:
                sent = await client.send_message(
                    chat_id=target,
                    text=promo_text,
                    reply_markup=promo_buttons,
                    parse_mode=ParseMode.MARKDOWN
                )

            promo_id = database.save_promo_post(target, sent.id, duration)
            last_promo_id = promo_id
            success_count += 1
        except Exception as e:
            print(f"❌ Could not post in {target}: {e}")
            failed_channels.append(channel.get('title', 'Unknown'))

    if admin_id in selected_channels:
        del selected_channels[admin_id]

    result_text = f"✅ Promo posted in {success_count}/{len(chosen_channels)} channels!\n"
    result_text += f"⏰ Auto-delete after {duration//3600} hours.\n"
    result_text += f"🎨 Template: {next((t['name'] for t in get_promo_templates() if t['id'] == template_id), 'Standard')}\n"
    
    if last_promo_id:
        result_text += f"📋 Promo ID: `{last_promo_id}`\n"

    if failed_channels:
        result_text += f"\n❌ Failed: {', '.join(failed_channels[:3])}"
        if len(failed_channels) > 3:
            result_text += f" and {len(failed_channels)-3} more..."

    try:
        await callback.message.edit_text(
            result_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩ Back to Admin Panel", callback_data="admin_panel")]]),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        if "MESSAGE_NOT_MODIFIED" not in str(e):
            await callback.answer("An error occurred. Please try again.", show_alert=True)
            print(f"Error in create_promo_post: {e}")


# ---- Back to categories ----
@Client.on_callback_query(filters.regex(r"^promo_back_categories$"))
async def back_to_categories(client, callback: CallbackQuery):
    await cb_send_promos(client, callback)

# ---- Write Promo Selection ----
@Client.on_callback_query(filters.regex(r"^write_promo$"))
async def cb_write_promo(client, callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Admin access required!", show_alert=True)
        return
    
    admin_id = callback.from_user.id
    
    # Store that this admin is in write promo mode
    if admin_id not in selected_channels:
        selected_channels[admin_id] = {}
    
    selected_channels[admin_id]["mode"] = "write_promo"
    
    # Send a new prompt message with ForceReply to make the input specific
    prompt = await callback.message.reply_text(
        "✍️ **Write Your Own Promo**\n\n"
        "Please reply to this message with the content you want to use as a promo post.\n\n"
        "You can send text, media, or forward a message.\n\n"
        "Type /cancel to cancel this operation.",
        reply_markup=ForceReply(selective=True),
        parse_mode=ParseMode.HTML
    )
    
    # Store the prompt message ID for verification
    selected_channels[admin_id]["prompt_message_id"] = prompt.id

# ---- Handle Admin Message for Write Promo ----
@Client.on_message(filters.user(config.ADMINS) & filters.reply & ~filters.command("start") & ~filters.command("cancel"))
async def handle_admin_promo_message(client, message: Message):
    admin_id = message.from_user.id
    
    # Check if admin is in write promo mode and replying to the correct prompt
    if admin_id not in selected_channels or selected_channels[admin_id].get("mode") != "write_promo":
        return
    
    if "prompt_message_id" not in selected_channels[admin_id] or selected_channels[admin_id]["prompt_message_id"] != message.reply_to_message.id:
        return
    
    # Check if we have selected channels
    if "final" not in selected_channels[admin_id] or not selected_channels[admin_id]["final"]:
        try:
            await message.reply_text(
                "❌ No channels selected for promotion. Please start over with /sendpromos",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("↩ Back to Admin Panel", callback_data="admin_panel")]
                ])
            )
        except Exception as e:
            print(f"Error in handle_admin_promo_message (no channels): {e}")
        return
    
    # Store the message details
    selected_channels[admin_id]["custom_message"] = {
        "text": message.text or message.caption,
        "media": None,
        "message_type": "text"
    }
    
    # Check if message has media (handle forwarded messages too)
    if message.photo:
        selected_channels[admin_id]["custom_message"]["media"] = message.photo.file_id
        selected_channels[admin_id]["custom_message"]["message_type"] = "photo"
    elif message.video:
        selected_channels[admin_id]["custom_message"]["media"] = message.video.file_id
        selected_channels[admin_id]["custom_message"]["message_type"] = "video"
    elif message.document:
        selected_channels[admin_id]["custom_message"]["media"] = message.document.file_id
        selected_channels[admin_id]["custom_message"]["message_type"] = "document"
    
    # Handle forwarded messages
    if message.forward_from_chat:
        # This is a forwarded message from a channel
        selected_channels[admin_id]["custom_message"]["is_forward"] = True
        selected_channels[admin_id]["custom_message"]["forward_from_chat_id"] = message.forward_from_chat.id
        selected_channels[admin_id]["custom_message"]["forward_from_message_id"] = message.forward_from_message_id
    
    # Ask for duration
    duration_buttons = [
        [InlineKeyboardButton("⏰ 1 Hour", callback_data="custom_promo_duration:3600")],
        [InlineKeyboardButton("⏰ 3 Hours", callback_data="custom_promo_duration:10800")],
        [InlineKeyboardButton("⏰ 6 Hours", callback_data="custom_promo_duration:21600")],
        [InlineKeyboardButton("⏰ 12 Hours", callback_data="custom_promo_duration:43200")],
        [InlineKeyboardButton("⏰ 24 Hours", callback_data="custom_promo_duration:86400")],
        [InlineKeyboardButton("↩ Cancel", callback_data="done_selecting")]
    ]
    
    selected_count = len(selected_channels[admin_id]["final"])
    category = selected_channels[admin_id].get("category", "Unknown")
    
    try:
        await message.reply_text(
            f"✅ Received your custom promo message!\n"
            f"✅ Selected {selected_count} channels in {CATEGORY_NAMES.get(category, category)}\n\n"
            "⏱ **How long should the promo post last before auto-deletion?**",
            reply_markup=InlineKeyboardMarkup(duration_buttons),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        print(f"Error in handle_admin_promo_message: {e}")

# ---- Handle Custom Promo Duration ----
# ---- Handle Custom Promo Duration ----
@Client.on_callback_query(filters.regex(r"^custom_promo_duration:(\d+)$"))
async def create_custom_promo_post(client, callback: CallbackQuery):
    admin_id = callback.from_user.id
    duration = int(callback.data.split(":")[1])

    if admin_id not in selected_channels or not selected_channels[admin_id].get("final"):
        await callback.answer("❌ Please select channels first.", show_alert=True)
        return

    if "custom_message" not in selected_channels[admin_id]:
        await callback.answer("❌ No custom message found.", show_alert=True)
        return

    channel_ids = selected_channels[admin_id]["final"]
    chosen_channels = [database.get_channel_by_id(cid) for cid in channel_ids if database.get_channel_by_id(cid)]
    
    if not chosen_channels:
        await callback.answer("❌ No valid channels found.", show_alert=True)
        return

    custom_message = selected_channels[admin_id]["custom_message"]
    bot_username = (await client.get_me()).username
    
    # Generate buttons for the custom promo
    promo_buttons = generate_promo_buttons(chosen_channels, bot_username)

    success_count = 0
    failed_channels = []
    last_promo_id = None

    for channel in chosen_channels:
        target = f"@{channel['username']}" if channel.get("username") else channel["channel_id"]
        try:
            # Handle forwarded messages - just forward them without buttons
            if custom_message.get("is_forward"):
                forwarded_msg = await client.forward_messages(
                    chat_id=target,
                    from_chat_id=custom_message["forward_from_chat_id"],
                    message_ids=custom_message["forward_from_message_id"]
                )
                if forwarded_msg:
                    promo_id = database.save_promo_post(target, forwarded_msg.id, duration)
                else:
                    sent = await client.send_message(
                        chat_id=target,
                        text=custom_message.get("text", "🔗 **Check out these channels:**"),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    promo_id = database.save_promo_post(target, sent.id, duration)

            elif custom_message["message_type"] == "photo" and custom_message["media"]:
                try:
                    sent = await client.send_photo(
                        chat_id=target,
                        photo=custom_message["media"],
                        caption=custom_message["text"],
                        reply_markup=promo_buttons,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as photo_error:
                    print(f"Photo send failed for {target}: {photo_error}. Falling back to text.")
                    sent = await client.send_message(
                        chat_id=target,
                        text=custom_message["text"],
                        reply_markup=promo_buttons,
                        parse_mode=ParseMode.MARKDOWN
                    )
                promo_id = database.save_promo_post(target, sent.id, duration)

            elif custom_message["message_type"] == "video" and custom_message["media"]:
                try:
                    sent = await client.send_video(
                        chat_id=target,
                        video=custom_message["media"],
                        caption=custom_message["text"],
                        reply_markup=promo_buttons,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as video_error:
                    print(f"Video send failed for {target}: {video_error}. Falling back to text.")
                    sent = await client.send_message(
                        chat_id=target,
                        text=custom_message["text"],
                        reply_markup=promo_buttons,
                        parse_mode=ParseMode.MARKDOWN
                    )
                promo_id = database.save_promo_post(target, sent.id, duration)

            elif custom_message["message_type"] == "document" and custom_message["media"]:
                try:
                    sent = await client.send_document(
                        chat_id=target,
                        document=custom_message["media"],
                        caption=custom_message["text"],
                        reply_markup=promo_buttons,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as doc_error:
                    print(f"Document send failed for {target}: {doc_error}. Falling back to text.")
                    sent = await client.send_message(
                        chat_id=target,
                        text=custom_message["text"],
                        reply_markup=promo_buttons,
                        parse_mode=ParseMode.MARKDOWN
                    )
                promo_id = database.save_promo_post(target, sent.id, duration)

            else:
                sent = await client.send_message(
                    chat_id=target,
                    text=custom_message["text"],
                    reply_markup=promo_buttons,
                    parse_mode=ParseMode.MARKDOWN
                )
                promo_id = database.save_promo_post(target, sent.id, duration)

            last_promo_id = promo_id
            success_count += 1
        except Exception as e:
            print(f"❌ Could not post in {target}: {e}")
            failed_channels.append(channel.get('title', 'Unknown'))

    # Clean up session state
    if admin_id in selected_channels:
        for key in ["mode", "custom_message", "prompt_message_id"]:
            if key in selected_channels[admin_id]:
                del selected_channels[admin_id][key]

    result_text = f"✅ Custom promo posted in {success_count}/{len(chosen_channels)} channels!\n"
    result_text += f"⏰ Auto-delete after {duration//3600} hours.\n"
    
    if last_promo_id:
        result_text += f"📋 Promo ID: `{last_promo_id}`\n"

    if failed_channels:
        result_text += f"\n❌ Failed: {', '.join(failed_channels[:3])}"
        if len(failed_channels) > 3:
            result_text += f" and {len(failed_channels)-3} more..."

    try:
        await callback.message.edit_text(
            result_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩ Back to Admin Panel", callback_data="admin_panel")]]),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        if "MESSAGE_NOT_MODIFIED" not in str(e):
            await callback.answer("An error occurred. Please try again.", show_alert=True)
            print(f"Error in create_custom_promo_post: {e}")


# ---- Cancel Operation ----
@Client.on_message(filters.user(config.ADMINS) & filters.command("cancel"))
async def cancel_operation(client, message: Message):
    admin_id = message.from_user.id
    
    if admin_id in selected_channels:
        # Clear any operation mode
        if "mode" in selected_channels[admin_id]:
            del selected_channels[admin_id]["mode"]
        if "custom_message" in selected_channels[admin_id]:
            del selected_channels[admin_id]["custom_message"]
        if "prompt_message_id" in selected_channels[admin_id]:
            del selected_channels[admin_id]["prompt_message_id"]
    
    try:
        await message.reply_text(
            "❌ Operation cancelled.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩ Back to Admin Panel", callback_data="admin_panel")]
            ])
        )
    except Exception as e:
        print(f"Error in cancel_operation: {e}")

# ---- Auto Deletion Worker ----
async def promo_cleanup_worker(client: Client):
    while True:
        promos = database.get_scheduled_promos()
        for promo in promos:
            try:
                await client.delete_messages(promo["channel"], promo["message_id"])
                database.remove_promo_post(promo["channel"], promo["message_id"])
                print(f"[PROMO] Deleted expired promo in {promo['channel']}")
            except Exception as e:
                print(f"[ERROR] Failed to delete promo {promo} - {e}")
        await asyncio.sleep(60)
