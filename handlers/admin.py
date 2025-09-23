# handlers/admin.py
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pyrogram.enums import ParseMode
from datetime import datetime, timedelta
import config
import database

# Admin panel keyboard
def get_admin_panel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Send Promos", callback_data="send_promos"),
         InlineKeyboardButton("🗑️ Delete Promo", callback_data="delete_promo_menu")],
        [InlineKeyboardButton("📋 List Promos", callback_data="list_promos_menu"),
         InlineKeyboardButton("👥 Check Users", callback_data="check_users:0")],
        [InlineKeyboardButton("📋 Check Channels", callback_data="check_channels:0"),
         InlineKeyboardButton("🗑️ Delete Channel", callback_data="delete_channel_menu:0")],
        [InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
         InlineKeyboardButton("🚫 Ban Menu", callback_data="ban_menu")],
        [InlineKeyboardButton("↩ Back to Main", callback_data="go_back_start")]
    ])

# Admin stats callback
@Client.on_callback_query(filters.regex(r"^admin_stats$"))
async def admin_stats_cb(client: Client, cq: CallbackQuery):
    if cq.from_user.id not in config.ADMINS:
        await cq.answer("❌ Admin access required!", show_alert=True)
        return
    
    # Get basic stats
    all_channels = database.get_all_channels()
    total_channels = len(all_channels)
    pending_count = len([ch for ch in all_channels if ch.get("status") == "PENDING"])
    approved_count = len([ch for ch in all_channels if ch.get("status") == "APPROVED"])
    total_users = len(database.get_all_users())
    banned_users = len(database.get_banned_users())
    banned_channels = len(database.get_banned_channels())
    
    stats_text = (
        "📊 **Bot Statistics**\n\n"
        f"• Total Channels: {total_channels}\n"
        f"• Pending Approvals: {pending_count}\n"
        f"• Approved Channels: {approved_count}\n"
        f"• Total Users: {total_users}\n"
        f"• Banned Users: {banned_users}\n"
        f"• Banned Channels: {banned_channels}\n\n"
        "More stats coming soon..."
    )
    
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("↩ Back to Admin Panel", callback_data="admin_panel")]])
    await cq.message.edit_text(stats_text, parse_mode=ParseMode.HTML, reply_markup=kb)

# Ping command for admins
@Client.on_message(filters.command("ping") & filters.user(config.ADMINS))
async def ping_command(client, message):
    await message.reply_text("🏓 Pong! Bot is working!")

# Debug command for admins
@Client.on_message(filters.command("debug") & filters.user(config.ADMINS))
async def debug_command(client, message):
    await message.reply_text(
        f"🤖 **Bot Debug Info**\n\n"
        f"• Your ID: `{message.from_user.id}`\n"
        f"• ADMINS list: `{config.ADMINS}`\n"
        f"• Is admin: `{message.from_user.id in config.ADMINS}`\n"
        f"• Bot username: @{client.me.username}\n"
        f"• MongoDB connected: `{bool(config.MONGO_DB_URI)}`"
    )

# Delete promo menu
@Client.on_callback_query(filters.regex(r"^delete_promo_menu$"))
async def delete_promo_menu(client: Client, cq: CallbackQuery):
    await cq.answer()
    
    promos = database.get_scheduled_promos()
    if not promos:
        await cq.message.edit_text(
            "📭 **No Active Promotions to Delete**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩ Back to Admin Panel", callback_data="admin_panel")]
            ]),
            parse_mode=ParseMode.HTML
        )
        return
    
    buttons = []
    for promo in promos[:10]:  # Show first 10 promos
        short_id = promo.get('promo_id', 'N/A')[:8] + "..." if promo.get('promo_id') else 'N/A'
        buttons.append([InlineKeyboardButton(
            f"🗑️ {promo['channel']} - ID: {short_id}",
            callback_data=f"confirm_delete:{promo.get('promo_id', '')}"
        )])
    
    buttons.append([InlineKeyboardButton("↩ Back to Admin Panel", callback_data="admin_panel")])
    
    await cq.message.edit_text(
        "🗑️ **Select Promo to Delete**\n\nChoose a promotion to delete:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.HTML
    )

# Confirm delete
@Client.on_callback_query(filters.regex(r"^confirm_delete:(.+)$"))
async def confirm_delete_promo(client: Client, cq: CallbackQuery):
    await cq.answer()
    promo_id = cq.matches[0].group(1)
    
    await cq.message.edit_text(
        f"⚠️ **Confirm Deletion**\n\n"
        f"Are you sure you want to delete promo `{promo_id}`?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"delete_yes:{promo_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="delete_promo_menu")]
        ]),
        parse_mode=ParseMode.HTML
    )

# Execute delete
@Client.on_callback_query(filters.regex(r"^delete_yes:(.+)$"))
async def execute_delete_promo(client: Client, cq: CallbackQuery):
    await cq.answer()
    promo_id = cq.matches[0].group(1)
    
    promo_data = database.get_promo_by_id(promo_id)
    if not promo_data:
        await cq.message.edit_text(
            "❌ Promo not found. It may have been already deleted.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩ Back to Admin Panel", callback_data="admin_panel")]
            ]),
            parse_mode=ParseMode.HTML
        )
        return
    
    try:
        await client.delete_messages(promo_data["channel"], promo_data["message_id"])
        database.remove_promo_post(promo_data["channel"], promo_data["message_id"])
        
        await cq.message.edit_text(
            f"✅ **Promo Deleted Successfully**\n\n"
            f"• Promo ID: `{promo_id}`\n"
            f"• Channel: {promo_data['channel']}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩ Back to Admin Panel", callback_data="admin_panel")]
            ]),
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        await cq.message.edit_text(
            f"❌ **Error deleting promo:**\n\n{str(e)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩ Back to Admin Panel", callback_data="admin_panel")]
            ]),
            parse_mode=ParseMode.HTML
        )

# List promos menu with pagination
@Client.on_callback_query(filters.regex(r"^list_promos_menu(?::(\d+))?$"))
async def list_promos_menu(client: Client, cq: CallbackQuery):
    await cq.answer()
    
    # Extract page number from callback data (default to 0 if not provided)
    page = int(cq.matches[0].group(1) or 0) if cq.matches else 0
    
    promos = database.get_scheduled_promos()
    if not promos:
        await cq.message.edit_text(
            "📭 **No Active Promotions**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩ Back to Admin Panel", callback_data="admin_panel")]
            ]),
            parse_mode=ParseMode.HTML
        )
        return
    
    # Paginate the promos
    ITEMS_PER_PAGE = 5
    start_idx = page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    promos_page = promos[start_idx:end_idx]
    total_pages = (len(promos) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    # Build the message with summarized info
    promo_list = []
    for i, promo in enumerate(promos_page, start=start_idx + 1):
        created_at = promo.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                created_at = datetime.utcnow()
        
        expires_at = created_at + timedelta(seconds=promo["duration"])
        time_left = expires_at - datetime.utcnow()
        hours_left = max(0, int(time_left.total_seconds() // 3600))
        minutes_left = max(0, int((time_left.total_seconds() % 3600) // 60))
        
        # Shorten channel name if too long
        channel_name = promo['channel']
        if len(channel_name) > 25:
            channel_name = channel_name[:22] + "..."
        
        promo_list.append(
            f"**{i}. ID:** `{promo.get('promo_id', 'N/A')[:8]}...`\n"
            f"   **Channel:** {channel_name}\n"
            f"   **Time Left:** {hours_left}h {minutes_left}m\n"
            f"   **Expires:** {expires_at.strftime('%m/%d %H:%M UTC')}\n"
        )
    
    # Build navigation buttons
    buttons = []
    
    # Navigation row
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"list_promos_menu:{page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="no_action"))
    
    if end_idx < len(promos):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"list_promos_menu:{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Action buttons
    buttons.append([
        InlineKeyboardButton("🔍 View Details", callback_data=f"view_promo_details:{page}"),
        InlineKeyboardButton("🗑️ Delete Promo", callback_data="delete_promo_menu")
    ])
    
    buttons.append([InlineKeyboardButton("↩ Back to Admin Panel", callback_data="admin_panel")])
    
    message_text = (
        f"📋 **Active Promotions** ({len(promos)} total)\n\n"
        + "\n".join(promo_list)
        + f"\n\n**Page {page+1} of {total_pages}**"
    )
    
    try:
        await cq.message.edit_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        # If message is still too long, truncate further
        if "MEDIA_CAPTION_TOO_LONG" in str(e) or "MESSAGE_TOO_LONG" in str(e):
            # Create an even more summarized version
            short_promo_list = []
            for i, promo in enumerate(promos_page, start=start_idx + 1):
                channel_name = promo['channel']
                if len(channel_name) > 15:
                    channel_name = channel_name[:12] + "..."
                
                short_promo_list.append(
                    f"**{i}.** {channel_name} - `{promo.get('promo_id', 'N/A')[:6]}...`"
                )
            
            short_message = (
                f"📋 **Active Promotions** ({len(promos)} total)\n\n"
                + "\n".join(short_promo_list)
                + f"\n\n**Page {page+1} of {total_pages}**\n"
                "Use 'View Details' to see more information."
            )
            
            await cq.message.edit_text(
                short_message,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.HTML
            )

# No action callback for page number button
@Client.on_callback_query(filters.regex(r"^no_action$"))
async def no_action_cb(client: Client, cq: CallbackQuery):
    await cq.answer()  # Just acknowledge the click without doing anything

# View promo details
@Client.on_callback_query(filters.regex(r"^view_promo_details:(\d+)$"))
async def view_promo_details(client: Client, cq: CallbackQuery):
    await cq.answer()
    page = int(cq.matches[0].group(1))
    
    promos = database.get_scheduled_promos()
    if not promos:
        await cq.answer("No active promotions found.", show_alert=True)
        return
    
    # Get the first promo from the current page for detailed view
    start_idx = page * 5
    if start_idx >= len(promos):
        await cq.answer("Invalid page.", show_alert=True)
        return
    
    promo = promos[start_idx]
    
    # Get detailed information
    created_at = promo.get("created_at")
    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except:
            created_at = datetime.utcnow()
    
    expires_at = created_at + timedelta(seconds=promo["duration"])
    time_left = expires_at - datetime.utcnow()
    hours_left = max(0, int(time_left.total_seconds() // 3600))
    minutes_left = max(0, int((time_left.total_seconds() % 3600) // 60))
    
    # Get channel info from database
    channel_info = database.get_channel_by_id(promo['channel'])
    channel_title = channel_info.get('title', 'Unknown') if channel_info else 'Unknown'
    
    details_text = (
        f"🔍 **Promo Details**\n\n"
        f"**Promo ID:** `{promo.get('promo_id', 'N/A')}`\n"
        f"**Channel:** {promo['channel']}\n"
        f"**Channel Title:** {channel_title}\n"
        f"**Message ID:** {promo['message_id']}\n"
        f"**Created:** {created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"**Duration:** {promo['duration'] // 3600} hours\n"
        f"**Expires:** {expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"**Time Left:** {hours_left} hours, {minutes_left} minutes\n"
        f"**Status:** {'Active' if time_left.total_seconds() > 0 else 'Expired'}"
    )
    
    buttons = [
        [InlineKeyboardButton("🗑️ Delete This Promo", callback_data=f"confirm_delete:{promo.get('promo_id', '')}")],
        [InlineKeyboardButton("📋 Back to List", callback_data=f"list_promos_menu:{page}")],
        [InlineKeyboardButton("↩ Admin Panel", callback_data="admin_panel")]
    ]
    
    await cq.message.edit_text(
        details_text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.HTML
    )

# ============== PAGINATION HELPERS =================
ITEMS_PER_PAGE = 5

def paginate_list(items, page):
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    return items[start:end], len(items) > end

# ================= BAN & UNBAN MENU =================
@Client.on_callback_query(filters.regex(r"^ban_menu$"))
async def ban_menu(client: Client, cq: CallbackQuery):
    if cq.from_user.id not in config.ADMINS:
        await cq.answer("❌ Admin access required!", show_alert=True)
        return
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Ban User", callback_data="ban_user"),
         InlineKeyboardButton("👤 Unban User", callback_data="unban_user")],
        [InlineKeyboardButton("📢 Ban Channel", callback_data="ban_channel"),
         InlineKeyboardButton("📢 Unban Channel", callback_data="unban_channel")],
        [InlineKeyboardButton("↩ Back to Admin Panel", callback_data="admin_panel")]
    ])
    await cq.message.edit_text("🚫 **Ban & Unban Menu**", reply_markup=kb, parse_mode=ParseMode.HTML)

# ================= CHECK USERS =================
@Client.on_callback_query(filters.regex(r"^check_users:(\d+)$"))
async def check_users_cb(client: Client, cq: CallbackQuery):
    page = int(cq.matches[0].group(1))
    users = database.get_all_users()
    users_page, has_next = paginate_list(users, page)

    if not users_page:
        await cq.message.edit_text(
            "📭 **No Users Found**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩ Back to Admin Panel", callback_data="admin_panel")]
            ]),
            parse_mode=ParseMode.HTML
        )
        return
    
    text = "👥 **Registered Users**\n\n"
    for idx, u in enumerate(users_page, start=page*ITEMS_PER_PAGE+1):
        username = f"@{u['username']}" if u.get("username") else "NoUsername"
        text += f"{idx}. {username} | ID: `{u['user_id']}`\n"

    # Build navigation buttons
    buttons = []
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"check_users:{page-1}"))
    
    total_pages = (len(users) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="no_action"))
    
    if has_next:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"check_users:{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton("↩ Back to Admin Panel", callback_data="admin_panel")])

    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.MARKDOWN)

# ================= CHECK CHANNELS =================
@Client.on_callback_query(filters.regex(r"^check_channels:(\d+)$"))
async def check_channels_cb(client: Client, cq: CallbackQuery):
    page = int(cq.matches[0].group(1))
    channels = database.get_all_channels()
    channels_page, has_next = paginate_list(channels, page)

    if not channels_page:
        await cq.message.edit_text(
            "📭 **No Channels Found**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩ Back to Admin Panel", callback_data="admin_panel")]
            ]),
            parse_mode=ParseMode.HTML
        )
        return
    
    text = "📋 **Submitted Channels**\n\n"
    for idx, ch in enumerate(channels_page, start=page*ITEMS_PER_PAGE+1):
        title = ch.get("title", "Unnamed Channel")
        username = f"@{ch.get('username', 'private')}" 
        channel_id = ch.get("channel_id", "N/A")
        status = ch.get("status", "UNKNOWN")
        subs = ch.get("subs_count", "N/A")
        
        text += (
            f"💼 **Channel {idx}:**\n"
            f"   • **Title:** {title}\n"
            f"   • **Username:** {username}\n"
            f"   • **ID:** `{channel_id}`\n"
            f"   • **Subscribers:** {subs}\n"
            f"   • **Status:** {status}\n\n"
        )

    # Build navigation buttons
    buttons = []
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"check_channels:{page-1}"))
    
    total_pages = (len(channels) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="no_action"))
    
    if has_next:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"check_channels:{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton("↩ Back to Admin Panel", callback_data="admin_panel")])

    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)

# ================= DELETE CHANNEL MENU =================
@Client.on_callback_query(filters.regex(r"^delete_channel_menu:(\d+)$"))
async def delete_channel_menu(client: Client, cq: CallbackQuery):
    page = int(cq.matches[0].group(1))
    channels = database.get_all_channels()
    channels_page, has_next = paginate_list(channels, page)

    if not channels_page:
        await cq.message.edit_text(
            "📭 **No Channels Found**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩ Back to Admin Panel", callback_data="admin_panel")]
            ]),
            parse_mode=ParseMode.HTML
        )
        return
    
    buttons = []
    for channel in channels_page:
        channel_id = channel.get("channel_id", "N/A")
        title = channel.get("title", "Unknown Channel")
        username = f"@{channel.get('username', 'private')}"
        
        # Shorten title if too long
        if len(title) > 20:
            title = title[:17] + "..."
        
        buttons.append([InlineKeyboardButton(
            f"🗑️ {title} ({username}) - ID: {channel_id}",
            callback_data=f"confirm_channel_delete:{channel_id}:{page}"
        )])
    
    # Navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"delete_channel_menu:{page-1}"))
    
    total_pages = (len(channels) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="no_action"))
    
    if has_next:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"delete_channel_menu:{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton("↩ Back to Admin Panel", callback_data="admin_panel")])
    
    await cq.message.edit_text(
        "🗑️ **Select Channel to Delete**\n\nChoose a channel to delete from the database:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.HTML
    )

# ================= CONFIRM CHANNEL DELETE =================
@Client.on_callback_query(filters.regex(r"^confirm_channel_delete:(-?\d+):(\d+)$"))
async def confirm_channel_delete(client: Client, cq: CallbackQuery):
    channel_id = int(cq.matches[0].group(1))
    page = int(cq.matches[0].group(2))
    
    channel_data = database.get_channel_by_id(channel_id)
    if not channel_data:
        await cq.answer("❌ Channel not found.", show_alert=True)
        return
    
    title = channel_data.get("title", "Unknown Channel")
    username = f"@{channel_data.get('username', 'private')}"
    status = channel_data.get("status", "UNKNOWN")
    owner_id = channel_data.get("user_id", "Unknown")
    
    await cq.message.edit_text(
        f"⚠️ **Confirm Channel Deletion**\n\n"
        f"**Channel:** {title}\n"
        f"**Username:** {username}\n"
        f"**ID:** `{channel_id}`\n"
        f"**Status:** {status}\n"
        f"**Owner ID:** `{owner_id}`\n\n"
        f"Are you sure you want to delete this channel from the database?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"delete_channel_yes:{channel_id}:{page}")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"delete_channel_menu:{page}")]
        ]),
        parse_mode=ParseMode.HTML
    )

# ================= EXECUTE CHANNEL DELETE =================
@Client.on_callback_query(filters.regex(r"^delete_channel_yes:(-?\d+):(\d+)$"))
async def execute_channel_delete(client: Client, cq: CallbackQuery):
    channel_id = int(cq.matches[0].group(1))
    page = int(cq.matches[0].group(2))
    
    channel_data = database.get_channel_by_id(channel_id)
    if not channel_data:
        await cq.answer("❌ Channel not found.", show_alert=True)
        return
    
    title = channel_data.get("title", "Unknown Channel")
    username = channel_data.get("username", "private")
    owner_id = channel_data.get("user_id")
    
    try:
        # Delete channel from database
        success = database.remove_channel(owner_id, channel_id)
        
        if success:
            # Notify the channel owner
            if owner_id:
                try:
                    await client.send_message(
                        owner_id,
                        f"🚫 **Your channel has been deleted by admin**\n\n"
                        f"**Channel:** {title}\n"
                        f"**Username:** @{username}\n"
                        f"**ID:** `{channel_id}`\n\n"
                        f"Your channel has been removed from the promotion system."
                    )
                except Exception as e:
                    print(f"Could not notify owner {owner_id}: {e}")
            
            # Notify all admins
            for admin_id in config.ADMINS:
                if admin_id != cq.from_user.id:  # Don't notify the admin who performed the action
                    try:
                        await client.send_message(
                            admin_id,
                            f"🔔 **Channel Deletion Report**\n\n"
                            f"**Deleted by:** {cq.from_user.mention}\n"
                            f"**Channel:** {title}\n"
                            f"**Username:** @{username}\n"
                            f"**ID:** `{channel_id}`\n"
                            f"**Owner ID:** `{owner_id}`"
                        )
                    except Exception as e:
                        print(f"Could not notify admin {admin_id}: {e}")
            
            await cq.message.edit_text(
                f"✅ **Channel Deleted Successfully**\n\n"
                f"**Channel:** {title}\n"
                f"**Username:** @{username}\n"
                f"**ID:** `{channel_id}`\n\n"
                f"✅ Owner has been notified.\n"
                f"✅ Admins have been notified.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 Back to Channels", callback_data=f"check_channels:{page}")],
                    [InlineKeyboardButton("↩ Admin Panel", callback_data="admin_panel")]
                ]),
                parse_mode=ParseMode.HTML
            )
        else:
            await cq.message.edit_text(
                "❌ **Failed to delete channel**\n\n"
                "Database error occurred.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 Back to Channels", callback_data=f"check_channels:{page}")],
                    [InlineKeyboardButton("↩ Admin Panel", callback_data="admin_panel")]
                ]),
                parse_mode=ParseMode.HTML
            )
            
    except Exception as e:
        await cq.message.edit_text(
            f"❌ **Error deleting channel:**\n\n{str(e)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Back to Channels", callback_data=f"check_channels:{page}")],
                [InlineKeyboardButton("↩ Admin Panel", callback_data="admin_panel")]
            ]),
            parse_mode=ParseMode.HTML
        )

# ================== BAN / UNBAN COMMANDS ==================
@Client.on_message(filters.command("banuser") & filters.user(config.ADMINS))
async def banuser_cmd(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /banuser [user_id]")
        return
    try:
        user_id = int(message.command[1])
        
        # Check if user is already banned
        if database.is_user_banned(user_id):
            await message.reply_text(f"❌ User `{user_id}` is already banned.")
            return
            
        database.ban_user(user_id)
        await message.reply_text(f"✅ User `{user_id}` has been banned.")
        
        # Notify the banned user if possible
        try:
            await client.send_message(
                user_id, 
                "🚫 **You have been banned from using this bot.**\n\n"
                "You will no longer be able to submit channels or use bot features."
            )
        except:
            pass  # User might have blocked the bot or privacy settings prevent messaging
            
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@Client.on_message(filters.command("unbanuser") & filters.user(config.ADMINS))
async def unbanuser_cmd(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /unbanuser [user_id]")
        return
    try:
        user_id = int(message.command[1])
        
        # Check if user is not banned
        if not database.is_user_banned(user_id):
            await message.reply_text(f"❌ User `{user_id}` is not banned.")
            return
            
        database.unban_user(user_id)
        await message.reply_text(f"✅ User `{user_id}` has been unbanned.")
        
        # Notify the unbanned user if possible
        try:
            await client.send_message(
                user_id, 
                "✅ **Your access to the bot has been restored.**\n\n"
                "You can now submit channels and use bot features again."
            )
        except:
            pass  # User might have blocked the bot or privacy settings prevent messaging
            
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@Client.on_message(filters.command("banchannel") & filters.user(config.ADMINS))
async def banchannel_cmd(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /banchannel [channel_id]")
        return
    try:
        channel_id = int(message.command[1])
        
        # Check if channel is already banned
        if database.is_channel_banned(channel_id):
            await message.reply_text(f"❌ Channel `{channel_id}` is already banned.")
            return
            
        database.ban_channel(channel_id)
        await message.reply_text(f"✅ Channel `{channel_id}` has been banned.")
        
        # Notify the channel owner if possible
        channel_data = database.get_channel_by_id(channel_id)
        if channel_data:
            try:
                await client.send_message(
                    channel_data["user_id"], 
                    f"🚫 **Your channel has been banned.**\n\n"
                    f"Channel ID: `{channel_id}`\n"
                    "This channel can no longer be used for promotions."
                )
            except:
                pass  # User might have blocked the bot or privacy settings prevent messaging
                
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@Client.on_message(filters.command("unbanchannel") & filters.user(config.ADMINS))
async def unbanchannel_cmd(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /unbanchannel [channel_id]")
        return
    try:
        channel_id = int(message.command[1])
        
        # Check if channel is not banned
        if not database.is_channel_banned(channel_id):
            await message.reply_text(f"❌ Channel `{channel_id}` is not banned.")
            return
            
        database.unban_channel(channel_id)
        await message.reply_text(f"✅ Channel `{channel_id}` has been unbanned.")
        
        # Notify the channel owner if possible
        channel_data = database.get_channel_by_id(channel_id)
        if channel_data:
            try:
                await client.send_message(
                    channel_data["user_id"], 
                    f"✅ **Your channel has been unbanned.**\n\n"
                    f"Channel ID: `{channel_id}`\n"
                    "This channel can now be used for promotions again."
                )
            except:
                pass  # User might have blocked the bot or privacy settings prevent messaging
                
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# ================== BAN / UNBAN CALLBACKS ==================
# Ban User
@Client.on_callback_query(filters.regex(r"^ban_user$"))
async def ban_user_cb(client: Client, cq: CallbackQuery):
    if cq.from_user.id not in config.ADMINS:
        await cq.answer("❌ Admin access required!", show_alert=True)
        return
    
    await cq.answer()
    await cq.message.edit_text(
        "❌ Usage: /banuser [user_id]\n\n"
        "Example: /banuser 123456789",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("↩ Back to Ban Menu", callback_data="ban_menu")]
        ])
    )

# Unban User
@Client.on_callback_query(filters.regex(r"^unban_user$"))
async def unban_user_cb(client: Client, cq: CallbackQuery):
    if cq.from_user.id not in config.ADMINS:
        await cq.answer("❌ Admin access required!", show_alert=True)
        return
    
    await cq.answer()
    await cq.message.edit_text(
        "❌ Usage: /unbanuser [user_id]\n\n"
        "Example: /unbanuser 123456789",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("↩ Back to Ban Menu", callback_data="ban_menu")]
        ])
    )

# Ban Channel
@Client.on_callback_query(filters.regex(r"^ban_channel$"))
async def ban_channel_cb(client: Client, cq: CallbackQuery):
    if cq.from_user.id not in config.ADMINS:
        await cq.answer("❌ Admin access required!", show_alert=True)
        return
    
    await cq.answer()
    await cq.message.edit_text(
        "❌ Usage: /banchannel [channel_id]\n\n"
        "Example: /banchannel -100123456789",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("↩ Back to Ban Menu", callback_data="ban_menu")]
        ])
    )
