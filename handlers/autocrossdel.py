# handlers/autocrossdel.py
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pyrogram.enums import ParseMode
import asyncio
import database
import config
import time
from datetime import datetime, timedelta

# Import admin panel from admin.py
from handlers.admin import get_admin_panel

# Store promo IDs for tracking
promo_tracking = {}

# Generate unique promo ID
def generate_promo_id():
    return f"PROMO_{int(time.time())}_{hash(str(time.time())) % 10000}"

# Auto-delete worker
async def promo_cleanup_worker(client: Client):
    """Auto-delete expired promos"""
    if not config.AUTO_DELETE_ENABLED:
        print("[AUTO-DELETE] Auto-delete is disabled in config")
        return
    
    print("[AUTO-DELETE] Auto-delete worker started")
    while True:
        try:
            promos = database.get_scheduled_promos()
            current_time = datetime.utcnow()
            
            for promo in promos:
                try:
                    # Check if promo should be deleted
                    created_at = promo.get("created_at")
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    
                    expires_at = created_at + timedelta(seconds=promo["duration"])
                    
                    if current_time >= expires_at:
                        # Delete the promo
                        try:
                            await client.delete_messages(promo["channel"], promo["message_id"])
                            print(f"[AUTO-DELETE] Deleted expired promo from {promo['channel']}")
                            
                            # Notify admin if configured
                            if config.NOTIFY_ON_MANUAL_DELETION:
                                for admin_id in config.ADMINS:
                                    try:
                                        await client.send_message(
                                            admin_id,
                                            f"🕒 **Auto-Deleted Promo**\n\n"
                                            f"• Channel: {promo['channel']}\n"
                                            f"• Message ID: {promo['message_id']}\n"
                                            f"• Duration: {promo['duration']//3600} hours\n"
                                            f"• Expired at: {expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                                            parse_mode=ParseMode.HTML
                                        )
                                    except:
                                        pass
                            
                        except Exception as e:
                            print(f"[AUTO-DELETE] Error deleting message: {e}")
                        
                        # Remove from database
                        database.remove_promo_post(promo["channel"], promo["message_id"])
                        
                except Exception as e:
                    print(f"[AUTO-DELETE] Error processing promo: {e}")
            
            await asyncio.sleep(config.AUTO_DELETE_CHECK_INTERVAL)
            
        except Exception as e:
            print(f"[AUTO-DELETE] Worker error: {e}")
            await asyncio.sleep(60)

# Manual delete command
@Client.on_message(filters.command("deletepromo") & filters.user(config.ADMINS))
async def delete_promo_command(client: Client, message: Message):
    """Delete a promo manually by ID"""
    args = message.text.split()
    if len(args) < 2:
        await message.reply_text(
            "❌ **Usage:** /deletepromo <promo_id>\n\n"
            "Use /listpromos to see active promotions with their IDs.",
            parse_mode=ParseMode.HTML
        )
        return
    
    promo_id = args[1]
    promo_data = database.get_promo_by_id(promo_id)
    
    if not promo_data:
        await message.reply_text(
            "❌ Promo ID not found. Use /listpromos to see active promotions.",
            parse_mode=ParseMode.HTML
        )
        return
    
    try:
        # Delete the message
        await client.delete_messages(promo_data["channel"], promo_data["message_id"])
        
        # Remove from database
        database.remove_promo_post(promo_data["channel"], promo_data["message_id"])
        
        await message.reply_text(
            f"✅ **Promo Deleted Successfully**\n\n"
            f"• Promo ID: `{promo_id}`\n"
            f"• Channel: {promo_data['channel']}\n"
            f"• Message ID: {promo_data['message_id']}",
            parse_mode=ParseMode.HTML
        )
        
        # Log the manual deletion
        print(f"[MANUAL-DELETE] Admin {message.from_user.id} deleted promo {promo_id}")
        
    except Exception as e:
        await message.reply_text(
            f"❌ **Error deleting promo:**\n\n{str(e)}",
            parse_mode=ParseMode.HTML
        )

# List active promos
@Client.on_message(filters.command("listpromos") & filters.user(config.ADMINS))
async def list_promos_command(client: Client, message: Message):
    """List all active promotions"""
    promos = database.get_scheduled_promos()
    
    if not promos:
        await message.reply_text(
            "📭 **No Active Promotions**\n\nThere are no active cross-promotions running.",
            parse_mode=ParseMode.HTML
        )
        return
    
    promo_list = []
    for promo in promos:
        created_at = promo.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                created_at = datetime.utcnow()
        
        expires_at = created_at + timedelta(seconds=promo["duration"])
        time_left = expires_at - datetime.utcnow()
        hours_left = max(0, int(time_left.total_seconds() // 3600))
        
        promo_list.append(
            f"• **ID:** `{promo.get('promo_id', 'N/A')}`\n"
            f"  **Channel:** {promo['channel']}\n"
            f"  **Message ID:** {promo['message_id']}\n"
            f"  **Time Left:** {hours_left} hours\n"
            f"  **Expires:** {expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        )
    
    await message.reply_text(
        "📋 **Active Promotions**\n\n" + "\n".join(promo_list),
        parse_mode=ParseMode.HTML
    )