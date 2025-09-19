# database.py
import config
from pymongo import MongoClient
from datetime import datetime

# -----------------------------
# MongoDB Connection
# -----------------------------
if config.MONGO_DB_URI:
    client = MongoClient(config.MONGO_DB_URI)
    db = client[config.MONGO_DB_NAME]  # Use DB name from config
    print(f"[DB] Connected to MongoDB: {config.MONGO_DB_NAME}")
else:
    # fallback in-memory store for dev
    db = {"submissions": [], "promos": [], "banned_users": [], "banned_channels": [], "users": []}
    print("[DB] Warning: MongoDB URI not found. Using in-memory store.")

# -----------------------------
# Save user information
# -----------------------------
def save_user(user_id: int, username: str):
    if isinstance(db, dict):  # in-memory
        # Check if user already exists
        for user in db.get("users", []):
            if user["user_id"] == user_id:
                # Update username if changed
                user["username"] = username
                return
        # Add new user
        if "users" not in db:
            db["users"] = []
        db["users"].append({"user_id": user_id, "username": username})
    else:
        # Create users collection if it doesn't exist
        if "users" not in db.list_collection_names():
            db.create_collection("users")
        # Upsert user data
        db.users.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "username": username}},
            upsert=True
        )

# -----------------------------
# Check if user exists
# -----------------------------
def user_exists(user_id: int):
    if isinstance(db, dict):
        return any(user["user_id"] == user_id for user in db.get("users", []))
    else:
        if "users" in db.list_collection_names():
            return db.users.count_documents({"user_id": user_id}) > 0
        return False

# -----------------------------
# Get all users (updated to use users collection)
# -----------------------------
def get_all_users():
    if isinstance(db, dict):
        return db.get("users", [])
    else:
        if "users" in db.list_collection_names():
            return list(db.users.find({}, {"_id": 0}))
        return []

# -----------------------------
# Save a channel submission
# -----------------------------
def save_submission(data: dict):
    if isinstance(db, dict):  # in-memory
        db["submissions"].append(data)
    else:
        db.submissions.insert_one(data)

# -----------------------------
# Update status (APPROVED / DENIED)
# -----------------------------
def update_status(channel_id: int, status: str):
    if isinstance(db, dict):  # in-memory
        for ch in db["submissions"]:
            if ch["channel_id"] == channel_id:
                ch["status"] = status
                ch["updated_at"] = datetime.utcnow()
                return True
        return False
    else:
        result = db.submissions.update_one(
            {"channel_id": channel_id},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0

# -----------------------------
# Get channels for a user
# -----------------------------
def get_user_channels(user_id: int, status_filter=None):
    if isinstance(db, dict):  # in-memory
        channels = [ch for ch in db["submissions"] if ch["user_id"] == user_id]
    else:
        query = {"user_id": user_id}
        if status_filter:
            query["status"] = status_filter
        channels = list(db.submissions.find(query).sort("added_at", -1))
    return channels

# -----------------------------
# Count channels for a user
# -----------------------------
def count_user_channels(user_id: int):
    if isinstance(db, dict):
        return len([ch for ch in db["submissions"] if ch["user_id"] == user_id])
    else:
        return db.submissions.count_documents({"user_id": user_id})

# -----------------------------
# Remove a channel
# -----------------------------
def remove_channel(user_id: int, channel_id: int):
    if isinstance(db, dict):
        before = len(db["submissions"])
        db["submissions"] = [
            ch for ch in db["submissions"]
            if not (ch["user_id"] == user_id and ch["channel_id"] == channel_id)
        ]
        return len(db["submissions"]) < before
    else:
        result = db.submissions.delete_one({"user_id": user_id, "channel_id": channel_id})
        return result.deleted_count > 0

# -----------------------------
# Helper: Get channel by ID
# -----------------------------
def get_channel_by_id(channel_id: int):
    if isinstance(db, dict):
        for ch in db["submissions"]:
            if ch["channel_id"] == channel_id:
                return ch
        return None
    else:
        return db.submissions.find_one({"channel_id": channel_id})

# -----------------------------
# PROMO FUNCTIONS
# -----------------------------
def get_channels_by_category(category: str):
    if isinstance(db, dict):
        return [c for c in db["submissions"] if c.get("category") == category and c.get("status") == "APPROVED"]
    else:
        return list(db.submissions.find({"category": category, "status": "APPROVED"}))
    
def get_promo_by_id(promo_id: str):
    if isinstance(db, dict):
        for promo in db["promos"]:
            if promo.get("promo_id") == promo_id:
                return promo
        return None
    else:
        return db.promos.find_one({"promo_id": promo_id})

def generate_promo_id():
    import time
    import random
    return f"PROMO_{int(time.time())}_{random.randint(1000, 9999)}"

def save_promo_post(channel: str, message_id: int, duration: int):
    promo_data = {
        "channel": channel,
        "message_id": message_id,
        "duration": duration,
        "created_at": datetime.utcnow(),
        "promo_id": generate_promo_id()
    }
    if isinstance(db, dict):
        db["promos"].append(promo_data)
        return promo_data["promo_id"]
    else:
        result = db.promos.insert_one(promo_data)
        return promo_data["promo_id"]

def get_scheduled_promos():
    if isinstance(db, dict):
        return db["promos"]
    else:
        return list(db.promos.find({}))

def remove_promo_post(channel: str, message_id: int):
    if isinstance(db, dict):
        db["promos"] = [p for p in db["promos"] if not (p["channel"] == channel and p["message_id"] == message_id)]
    else:
        db.promos.delete_one({"channel": channel, "message_id": message_id})

# -----------------------------
# BAN/UNBAN FUNCTIONS
# -----------------------------
def ban_user(user_id: int):
    if isinstance(db, dict):
        if user_id not in db["banned_users"]:
            db["banned_users"].append(user_id)
    else:
        # Create banned_users collection if it doesn't exist
        if "banned_users" not in db.list_collection_names():
            db.create_collection("banned_users")
        db.banned_users.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "banned_at": datetime.utcnow()}},
            upsert=True
        )

def unban_user(user_id: int):
    if isinstance(db, dict):
        if user_id in db["banned_users"]:
            db["banned_users"].remove(user_id)
    else:
        if "banned_users" in db.list_collection_names():
            db.banned_users.delete_one({"user_id": user_id})

def is_user_banned(user_id: int):
    if isinstance(db, dict):
        return user_id in db["banned_users"]
    else:
        if "banned_users" in db.list_collection_names():
            return db.banned_users.count_documents({"user_id": user_id}) > 0
        return False

def ban_channel(channel_id: int):
    if isinstance(db, dict):
        if channel_id not in db["banned_channels"]:
            db["banned_channels"].append(channel_id)
    else:
        # Create banned_channels collection if it doesn't exist
        if "banned_channels" not in db.list_collection_names():
            db.create_collection("banned_channels")
        db.banned_channels.update_one(
            {"channel_id": channel_id},
            {"$set": {"channel_id": channel_id, "banned_at": datetime.utcnow()}},
            upsert=True
        )

def unban_channel(channel_id: int):
    if isinstance(db, dict):
        if channel_id in db["banned_channels"]:
            db["banned_channels"].remove(channel_id)
    else:
        if "banned_channels" in db.list_collection_names():
            db.banned_channels.delete_one({"channel_id": channel_id})

def is_channel_banned(channel_id: int):
    if isinstance(db, dict):
        return channel_id in db["banned_channels"]
    else:
        if "banned_channels" in db.list_collection_names():
            return db.banned_channels.count_documents({"channel_id": channel_id}) > 0
        return False

def get_banned_users():
    if isinstance(db, dict):
        return db["banned_users"]
    else:
        if "banned_users" in db.list_collection_names():
            return list(db.banned_users.find({}, {"_id": 0}))
        return []

def get_banned_channels():
    if isinstance(db, dict):
        return db["banned_channels"]
    else:
        if "banned_channels" in db.list_collection_names():
            return list(db.banned_channels.find({}, {"_id": 0}))
        return []

# -----------------------------
# GET ALL CHANNELS
# -----------------------------
def get_all_channels():
    if isinstance(db, dict):
        return db["submissions"]
    else:
        return list(db.submissions.find({}, {"_id": 0}))