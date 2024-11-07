import asyncio
import random
import ssl
import json
import time
import uuid
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent
from aiohttp import ClientSession

# Membaca daftar proxy dari file eksternal
def load_proxies_from_file(filename="proxies.txt"):
    proxy_list = []
    try:
        with open(filename, "r") as file:
            proxy_list = [line.strip() for line in file if line.strip()]
        logger.info(f"Loaded {len(proxy_list)} proxies from {filename}")
    except FileNotFoundError:
        logger.error(f"File {filename} not found. Please create it and add your proxies.")
    return proxy_list

# Membaca daftar user ID dari file eksternal dan membuat device_id untuk setiap ID
def load_user_ids_from_file(filename="user_ids.txt"):
    user_fingerprints = {}
    try:
        with open(filename, "r") as file:
            for line in file:
                user_id = line.strip()
                if user_id:
                    user_fingerprints[user_id] = {
                        "device_id": str(uuid.uuid4()),
                        "user_agent": UserAgent().chrome  # Menghasilkan User-Agent Chrome acak
                    }
        logger.info(f"Loaded {len(user_fingerprints)} user IDs from {filename}")
    except FileNotFoundError:
        logger.error(f"File {filename} not found. Please create it and add your user IDs.")
    return user_fingerprints

# Memuat proxy_list dan user_fingerprints dari file eksternal
proxy_list = load_proxies_from_file()
user_fingerprints = load_user_ids_from_file()

used_proxies = set()  # Set untuk melacak proxy yang sedang digunakan
usage_stats = {user_id: {"reconnects": 0, "proxy": [], "connected_time": 0} for user_id in user_fingerprints.keys()}

class WebSocketManager:
    def __init__(self):
        self.session = ClientSession()  # Inisialisasi sesi di sini

    async def close_session(self):
        # Tutup sesi setelah semua koneksi selesai
        await self.session.close()

    async def connect_to_wss(self, user_id):
        device_id = user_fingerprints[user_id]["device_id"]
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        # Daftar URI WebSocket dengan alternatif tambahan
        uris = ["wss://proxy.wynd.network:4444/", "wss://proxy.wynd.network:4650/", "wss://proxy2.wynd.network:4444/"]

        proxies = await get_unique_proxies(user_id, 5)
        if not proxies:
            logger.error(f"[{user_id}] Tidak ada proxy yang tersedia. Menunggu...")
            return

        for proxy in proxies:
            headers = generate_extension_headers(user_id, proxy)
            for uri in uris:
                try:
                    usage_stats[user_id]["proxy"].append(proxy)
                    async with proxy_connect(uri, proxy=Proxy.from_url(proxy), ssl=ssl_context, extra_headers=headers) as websocket:
                        start_time = time.time()
                        logger.info(f"[{user_id}] Connected to {uri} with proxy: {proxy}, device_id: {device_id}")
                        await simulate_activity(websocket, user_id, start_time)
                        return  # Keluar dari fungsi jika koneksi berhasil
                except Exception as e:
                    logger.error(f"[{user_id}] Connection error with proxy {proxy} on {uri}: {e}")
                    await reconnect_with_backoff(user_id, proxy)

# Generate headers for the WebSocket connection
def generate_extension_headers(user_id, proxy):
    user_agent = user_fingerprints[user_id]["user_agent"]
    headers = {
        "User-Agent": user_agent,
        "Origin": f"chrome-extension://lkbnfiajjmbhnfledhphioinpickokdi",
        "Referer": f"chrome-extension://lkbnfiajjmbhnfledhphioinpickokdi/",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "none"
    }
    logger.info(f"[{user_id}] Using User-Agent '{user_agent}' for proxy '{proxy}'")
    return headers

async def get_unique_proxies(user_id, num_proxies):
    proxies = []
    attempts = 0
    while len(proxies) < num_proxies and attempts < len(proxy_list):
        proxy = random.choice(proxy_list)
        if proxy not in used_proxies:
            used_proxies.add(proxy)
            proxies.append(proxy)
        attempts += 1
        await asyncio.sleep(0.1)
    return proxies

def release_proxies(user_id):
    # Melepaskan proxy yang telah digunakan
    for proxy in usage_stats[user_id]["proxy"]:
        used_proxies.discard(proxy)
    usage_stats[user_id]["proxy"].clear()

async def reconnect_with_backoff(user_id, failed_proxy):
    delay = 5
    max_retries = 10
    retries = 0
    while retries < max_retries:
        proxies = await get_unique_proxies(user_id, 5)
        if proxies:
            logger.info(f"[{user_id}] Attempting reconnection with new proxies: {proxies}")
            usage_stats[user_id]["reconnects"] += 1
            for proxy in proxies:
                try:
                    await WebSocketManager().connect_to_wss(user_id)
                    return
                except Exception as e:
                    logger.error(f"[{user_id}] Reconnect error: {e}. Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                    retries += 1
                    delay *= 2
    logger.error(f"[{user_id}] Failed to reconnect after {max_retries} attempts.")

# Initialize connection with a slight delay
async def initialize_connection_with_jitter(user_id):
    jitter = random.uniform(1, 5)
    await asyncio.sleep(jitter)
    await WebSocketManager().connect_to_wss(user_id)

# Main function
async def main():
    ws_manager = WebSocketManager()
    try:
        tasks = [initialize_connection_with_jitter(user_id) for user_id in user_fingerprints.keys()]
        await asyncio.gather(*tasks)
    finally:
        await ws_manager.close_session()  # Menutup sesi saat semua tugas selesai

if __name__ == '__main__':
    logger.add("connection_logs.log", rotation="5 MB", retention="7 days", level="INFO")
    asyncio.run(main())
