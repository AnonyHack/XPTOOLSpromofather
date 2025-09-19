# main.py
from pyrogram import Client
import config
import logging
import database  # MongoDB connection
from handlers.autocrossdel import promo_cleanup_worker  # Import the worker
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
LOGGER = logging.getLogger(__name__)

# ========== Health Check Server ==========
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_server():
    server = HTTPServer(('0.0.0.0', config.RENDER_PORT), HealthHandler)
    LOGGER.info(f"🌐 Health server started on port {config.RENDER_PORT}")
    server.serve_forever()

# Create Pyrogram Client
app = Client(
    "PromoFatherBot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    plugins=dict(root="handlers")  # Automatically load all handlers
)

async def main():
    await app.start()
    LOGGER.info("🚀 Promo Father Bot is starting...")

    # Start the auto-delete worker
    if config.AUTO_DELETE_ENABLED:
        asyncio.create_task(promo_cleanup_worker(app))
        LOGGER.info("🔄 Auto-delete worker started")
    else:
        LOGGER.info("⏸️ Auto-delete is disabled in config")

    # Keep the bot running
    await asyncio.Event().wait()

if __name__ == "__main__":
    # Start health check server in a separate thread
    threading.Thread(target=run_health_server, daemon=True).start()
    
    app.run(main())
