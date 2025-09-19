# utils/crosstempl.py
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

# -----------------------------
# CROSS-PROMO TEMPLATES
# -----------------------------

def get_promo_templates():
    """Return list of available promo templates"""
    return [
        {"id": "template1", "name": "🚀 Standard Promo", "description": "Clean and professional"},
        {"id": "template2", "name": "🔥 Viral Style", "description": "Eye-catching and engaging"},
        {"id": "template3", "name": "💎 Premium Look", "description": "Elegant and sophisticated"},
        {"id": "template4", "name": "🎯 Direct Call", "description": "Action-oriented and direct"},
        {"id": "template5", "name": "🌟 Community Focus", "description": "Friendly and community-driven"},
        {"id": "template6", "name": "📱 Grid Style Promo", "description": "Modern grid layout with channel pairs"}
    ]

def generate_promo_message(template_id, channels, category=None, bot_name="PromoFather"):
    """Generate promo message based on template"""
    templates = {
        "template1": _template_standard,
        "template2": _template_viral,
        "template3": _template_premium,
        "template4": _template_direct,
        "template5": _template_community,
        "template6": _template_grid_style
    }
    
    return templates.get(template_id, _template_standard)(channels, category, bot_name)

def generate_promo_buttons(channels, bot_username):
    """Generate buttons for the promo message in a grid layout with Add Your Channel button"""
    buttons = []
    row = []
    
    # Button icons for different channel types
    icons = ["📺", "📢", "🌟", "🔥", "💎", "🚀", "🎯", "📰", "🎬", "⚽", "💻", "💸"]
    
    for i, channel in enumerate(channels):
        username = channel.get('username')
        title = channel.get('title', 'Unknown Channel')
        
        if username and username != 'private':
            # Use a different icon for each button
            icon = icons[i % len(icons)]
            button = InlineKeyboardButton(f"{icon} {title}", url=f"https://t.me/{username}")
            
            # Add button to current row
            row.append(button)
            
            # Start a new row after every 2 buttons
            if len(row) >= 2:
                buttons.append(row)
                row = []
    
    # Add any remaining buttons
    if row:
        buttons.append(row)
    
    # Add the "Add Your Channel" button below all channel buttons
    if bot_username:
        buttons.append([InlineKeyboardButton("➕ Add Your Channel", url=f"https://t.me/{bot_username}")])
    
    return InlineKeyboardMarkup(buttons) if buttons else None

# -----------------------------
# INDIVIDUAL TEMPLATES
# -----------------------------

def _template_standard(channels, category=None, bot_name="PromoFather"):
    """Standard professional template"""
    message = (
        "🎯 JOIN THESE CHANNELS NOW! 🎯\n\n"
        "Stop scrolling and start engaging with these amazing communities!\n\n"
    )
    
    message += (
        "⏰ Limited time opportunity!\n"
        "🚀 Join these channels RIGHT NOW!\n\n"
        f"💪 *Made by {bot_name}*"
    )
    
    return message

def _template_viral(channels, category=None, bot_name="PromoFather"):
    """Viral-style engaging template"""
    message = (
        "🎯 JOIN THESE CHANNELS NOW! 🎯\n\n"
        "Stop scrolling and start engaging with these amazing communities!\n\n"
    )
    
    message += (
        "⏰ Limited time opportunity!\n"
        "🚀 Join these channels RIGHT NOW!\n\n"
        f"💪 *Made by {bot_name}*"
    )
    
    return message

def _template_premium(channels, category=None, bot_name="PromoFather"):
    """Premium elegant template"""
    message = (
        "🎯 JOIN THESE CHANNELS NOW! 🎯\n\n"
        "Stop scrolling and start engaging with these amazing communities!\n\n"
    )
    
    message += (
        "⏰ Limited time opportunity!\n"
        "🚀 Join these channels RIGHT NOW!\n\n"
        f"💪 *Made by {bot_name}*"
    )
    
    return message

def _template_direct(channels, category=None, bot_name="PromoFather"):
    """Direct call-to-action template"""
    message = (
        "🎯 JOIN THESE CHANNELS NOW! 🎯\n\n"
        "Stop scrolling and start engaging with these amazing communities!\n\n"
    )
    
    message += (
        "⏰ Limited time opportunity!\n"
        "🚀 Join these channels RIGHT NOW!\n\n"
        f"💪 *Made by {bot_name}*"
    )
    
    return message

def _template_community(channels, category=None, bot_name="PromoFather"):
    """Community-focused friendly template"""
    message = (
        "🎯 JOIN THESE CHANNELS NOW! 🎯\n\n"
        "Stop scrolling and start engaging with these amazing communities!\n\n"
    )
    
    message += (
        "⏰ Limited time opportunity!\n"
        "🚀 Join these channels RIGHT NOW!\n\n"
        f"💪 *Made by {bot_name}*"
    )
    
    return message

def _template_grid_style(channels, category=None, bot_name="PromoFather"):
    """Grid-style template with channel pairs"""
    separator = "━━━━━━━━━━━━━━━━━━━━━━━━"
    
    message = "📜 𝗔𝗽𝗽 𝗛𝗮𝗰𝗸𝗶𝗻𝗴  ✅ 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗠𝗼𝗱𝘀 📜\n"
    message += f"{separator}\n\n"
    
    # Create pairs of channels
    for i in range(0, len(channels), 2):
        if i < len(channels):
            ch1 = channels[i]
            title1 = ch1.get('title', 'Unknown Channel')
            username1 = ch1.get('username', 'private')
            
            # Format the title to fit the grid style
            if len(title1) > 15:
                title1 = title1[:12] + "..."
            
            if i + 1 < len(channels):
                ch2 = channels[i + 1]
                title2 = ch2.get('title', 'Unknown Channel')
                username2 = ch2.get('username', 'private')
                
                # Format the title to fit the grid style
                if len(title2) > 15:
                    title2 = title2[:12] + "..."
                
                # Add the pair to the message
                message += f"🆕️ {title1}    ⭐️ {title2}\n"
                message += f"👉 @𝗝𝗼𝗶𝗻 𝗡𝗼𝘄            👉  @𝗝𝗼𝗶𝗻 𝗡𝗼𝘄 \n"
                message += f"{separator}\n\n"
            else:
                # Single channel if odd number
                message += f"🆕️ {title1}\n"
                message += f"👉 @𝗝𝗼𝗶𝗻 𝗡𝗼𝘄 \n"
                message += f"{separator}\n\n"
    
    message += f"💪 *Made by {bot_name}*"
    
    return message

# -----------------------------
# SPECIAL BUTTONS FOR GRID TEMPLATE
# -----------------------------

def generate_grid_promo_buttons(channels, bot_username):
    """Generate special buttons for the grid template where each 'Join Now' text is clickable"""
    buttons = []
    
    # Create buttons for each channel
    for i, channel in enumerate(channels):
        username = channel.get('username')
        if username and username != 'private':
            # Add button for each channel with "Join Now" text
            buttons.append([InlineKeyboardButton(f"@𝗝𝗼𝗶𝗻 𝗡𝗼𝘄", url=f"https://t.me/{username}")])
    
    # Add the "Add Your Channel" button below all channel buttons
    if bot_username:
        buttons.append([InlineKeyboardButton("➕ Add Your Channel", url=f"https://t.me/{bot_username}")])
    
    return InlineKeyboardMarkup(buttons) if buttons else None

# -----------------------------
# TEMPLATE SELECTION KEYBOARD
# -----------------------------

# -----------------------------
# TEMPLATE SELECTION KEYBOARD
# -----------------------------

def get_template_selection_keyboard():
    """Generate keyboard for template selection"""
    templates = get_promo_templates()
    buttons = []
    
    for template in templates:
        buttons.append([
            InlineKeyboardButton(
                template["name"], 
                callback_data=f"promo_template:{template['id']}"
            )
        ])
    
    # Add the "Write Promo" button
    buttons.append([InlineKeyboardButton("✍️ Write Promo", callback_data="write_promo")])
    buttons.append([InlineKeyboardButton("↩ Back", callback_data="promo_back_categories")])
    
    return InlineKeyboardMarkup(buttons)