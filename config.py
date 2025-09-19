import re
from os import getenv
from dotenv import load_dotenv
from pyrogram import filters

# Load environment variables from .env file
load_dotenv()

# ───── Basic Bot Configuration ───── #
API_ID = int(getenv("API_ID"))
API_HASH = getenv("API_HASH")
BOT_TOKEN = getenv("BOT_TOKEN")

OWNER_ID = int(getenv("OWNER_ID", 5962658076))
# FIXED: ADMINS should be a list of integers
ADMINS = [int(admin_id) for admin_id in getenv("ADMINS", str(OWNER_ID)).split(",")]
OWNER_USERNAME = getenv("OWNER_USERNAME", "@Am_Itachiuchiha")
BOT_USERNAME = getenv("BOT_USERNAME", "PromosFatherBot")
BOT_NAME = getenv("BOT_NAME", "PromoFather") 
EVALOP = [int(eval_id) for eval_id in getenv("EVALOP", str(OWNER_ID)).split(",")]

# ───── Mongo & Logging ───── #
MONGO_DB_URI = getenv("MONGO_DB_URI")
MONGO_DB_NAME = getenv("MONGO_DB_NAME", "Promosfather")
LOGGER_ID = int(getenv("LOGGER_ID", -1001234567890))

# ───── Promo Configurations ───── #
MIN_CHANNELS_FOR_CROSS_PROMO = int(getenv("MIN_CHANNELS_FOR_CROSS_PROMO", "3"))
PROMO_IMAGE = "https://i.ibb.co/tpqjvwDV/promobanner2.jpg"  # Default promo image URL
# Eligibility settings
MIN_SUBSCRIBERS = 500  # 👈 You can change this anytime (e.g., 100, 10, 1000, etc.)

# Auto-delete settings
AUTO_DELETE_ENABLED = getenv("AUTO_DELETE_ENABLED", "True").lower() == "true"
AUTO_DELETE_CHECK_INTERVAL = int(getenv("AUTO_DELETE_CHECK_INTERVAL", "60"))  # seconds
NOTIFY_ON_MANUAL_DELETION = getenv("NOTIFY_ON_MANUAL_DELETION", "True").lower() == "true"

# ───── Heroku Configuration (Optional) ───── #
HEROKU_APP_NAME = getenv("HEROKU_APP_NAME")
HEROKU_API_KEY = getenv("HEROKU_API_KEY")

# ───── Support & Community ───── #
SUPPORT_CHANNEL = getenv("SUPPORT_CHANNEL", "https://t.me/Megahubbots")
SUPPORT_CHAT = getenv("SUPPORT_CHAT", "https://t.me/Am_Itachiuchiha")
SUBMISSION_GUIDE_URL = getenv("SUBMISSION_GUIDE_URL", "https://t.me/Promosfather/3")
ADMINS_GROUP_LINK = "https://t.me/+TjbntORY8JVkOWJk"  # Where users can join after channel 
UPDATES_CHANNEL_LINK = "https://t.me/Promosfather"  # Channel for updates

# ───── Bot Media Assets ───── #
START_MSG_VID = getenv("START_MSG_VID", "")
START_MSG_PHOTO = getenv("START_MSG_PHOTO", "https://i.ibb.co/JjYgkbsn/promologo.jpg")
HELP_IMG_URL = getenv("HELP_IMG_URL", "https://i.ibb.co/3Y89Scqw/promologo2.jpg")
PROMO_IMAGE = getenv("PROMO_IMAGE", "https://i.ibb.co/tpqjvwDV/promobanner2.jpg, https://i.ibb.co/k2Mt3hNb/promobanner1.jpg") # Promo banner image https://i.ibb.co/k2Mt3hNb/promobanner1.jpg

# ───── Runtime Structures ───── #
BANNED_USERS = filters.user()
adminlist, crosspromos, autoclean = {}, {}, {}

# ───── URL Validation ───── #
if SUPPORT_CHANNEL and not re.match(r"^https?://", SUPPORT_CHANNEL):
    raise SystemExit("[ERROR] - Invalid SUPPORT_CHANNEL URL. Must start with https://")

if SUPPORT_CHAT and not re.match(r"^https?://", SUPPORT_CHAT):
    raise SystemExit("[ERROR] - Invalid SUPPORT_CHAT URL. Must start with https://")

# config.py
RENDER_PORT = 10000  # Or set from env: int(os.getenv("RENDER_PORT", 10000))

# Debug print to check ADMINS is set correctly
print(f"ADMINS: {ADMINS}")
print(f"OWNER_ID: {OWNER_ID}")
print(f"AUTO_DELETE_ENABLED: {AUTO_DELETE_ENABLED}")
print(f"MIN_SUBSCRIBERS: {MIN_SUBSCRIBERS}")
print(f"START_MSG_VID: {START_MSG_VID}")
print(f"START_MSG_PHOTO: {START_MSG_PHOTO}")
print(f"SUPPORT_CHANNEL: {SUPPORT_CHANNEL}")
print(f"SUPPORT_CHAT: {SUPPORT_CHAT}")
print(f"SUBMISSION_GUIDE_URL: {SUBMISSION_GUIDE_URL}")
print(f"BOT_NAME: {BOT_NAME}")
print(f"BOT_USERNAME: {BOT_USERNAME}")
print(f"API_ID: {API_ID}")
print(f"API_HASH: {API_HASH}")
print(f"BOT_TOKEN: {'Set' if BOT_TOKEN else 'Not Set'}")
print(f"MONGO_DB_URI: {'Set' if MONGO_DB_URI else 'Not Set'}")
print(f"MONGO_DB_NAME: {MONGO_DB_NAME}")
print(f"RENDER_PORT: {RENDER_PORT}")
print(f"AUTO_DELETE_CHECK_INTERVAL: {AUTO_DELETE_CHECK_INTERVAL}")
print(f"NOTIFY_ON_MANUAL_DELETION: {NOTIFY_ON_MANUAL_DELETION}")
print(f"MIN_CHANNELS_FOR_CROSS_PROMO: {MIN_CHANNELS_FOR_CROSS_PROMO}")
print(f"MIN_SUBSCRIBERS: {MIN_SUBSCRIBERS}")
print(f"PROMO_IMAGE: {PROMO_IMAGE}")
print(f"OWNER_USERNAME: {OWNER_USERNAME}")




