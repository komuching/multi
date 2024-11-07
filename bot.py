import asyncio
import random
import ssl
import json
import time
import uuid
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent

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
                    user_fingerprints[user_id] = {"device_id": str(uuid.uuid4())}
        logger.info(f"Loaded {len(user_fingerprints)} user IDs from {filename}")
    except FileNotFoundError:
        logger.error(f"File {filename} not found. Please create it and add your user IDs.")
    return user_fingerprints

# Memuat proxy_list dan user_fingerprints dari file eksternal
proxy_list = load_proxies_from_file()
user_fingerprints = load_user_ids_from_file()

used_proxies = set()  # Set untuk melacak proxy yang sedang digunakan

# Statistik penggunaan untuk setiap user_id
usage_stats = {user_id: {"reconnects": 0, "proxy": [], "connected_time": 0} for user_id in user_fingerprints.keys()}

# Konfigurasi User-Agent dasar untuk hanya menggunakan Chrome
user_agent = UserAgent()

# Fungsi untuk membuat header acak khusus Chrome
def generate_extension_headers(user_id, proxy):
    unique_user_agent = user_agent.chrome  # Menghasilkan User-Agent Chrome secara acak
    headers = {
        "User-Agent": unique_user_agent,
        "Origin": f"chrome-extension://lkbnfiajjmbhnfledhphioinpickokdi",
        "Referer": f"chrome-extension://lkbnfiajjmbhnfledhphioinpickokdi/",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "none"
    }
    # Log User-Agent yang digunakan untuk kombinasi user_id dan proxy
    logger.info(f"[{user_id}] Using User-Agent '{unique_user_agent}' for proxy '{proxy}'")
    return headers

async def connect_to_wss(user_id):
    # Mendapatkan hingga 5 proxy unik untuk setiap user_id
    proxies = await get_unique_proxies(user_id, 5)
    if not proxies:
        logger.error(f"[{user_id}] Tidak ada proxy yang tersedia. Menunggu...")
        return

    device_id = user_fingerprints[user_id]["device_id"]
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    uri = random.choice(["wss://proxy.wynd.network:4444/", "wss://proxy.wynd.network:4650/"])

    for proxy in proxies:
        headers = generate_extension_headers(user_id, proxy)  # Set User-Agent unik untuk setiap proxy
        try:
            usage_stats[user_id]["proxy"].append(proxy)
            async with proxy_connect(uri, proxy=Proxy.from_url(proxy), ssl=ssl_context, extra_headers=headers) as websocket:
                start_time = time.time()
                logger.info(f"[{user_id}] Connected: device_id={device_id}, proxy={proxy}")
                await simulate_activity(websocket, user_id, start_time)
        except Exception as e:
            logger.error(f"[{user_id}] Connection error with proxy {proxy}: {e}")
            await reconnect_with_backoff(user_id, proxy)

async def simulate_activity(websocket, user_id, start_time):
    try:
        # Durasi aktivitas untuk 120 menit (7200 detik)
        active_duration = 7200  # 2 jam
        idle_duration = 180  # Istirahat selama 3 menit sebelum reconnect
        end_time = start_time + active_duration
        
        while time.time() < end_time:
            # Mengirim PING setiap 10-20 detik
            await send_ping(websocket, user_id)
            await asyncio.sleep(random.uniform(10, 20))
            
            # Simulasi aktivitas tambahan setiap 30-60 detik
            await simulate_additional_activity(websocket, user_id)
            await asyncio.sleep(random.uniform(30, 60))
            
            # Logging setiap 10 menit
            connected_duration = int(time.time() - start_time)
            usage_stats[user_id]["connected_time"] = connected_duration
            logger.info(f"[{user_id}] Connected for {connected_duration} seconds using proxies {usage_stats[user_id]['proxy']} with {usage_stats[user_id]['reconnects']} reconnects")
        
        # Setelah aktif selama 2 jam, tutup koneksi dan jeda 3 menit sebelum reconnect
        await websocket.close()
        logger.info(f"[{user_id}] Disconnected after 120 minutes. Reconnecting after {idle_duration // 60} minutes.")
        release_proxies(user_id)
        await asyncio.sleep(idle_duration)
        await reconnect_with_backoff(user_id)  # Reconnect dengan proxy baru
    except Exception as e:
        logger.error(f"[{user_id}] Error during activity: {e}")
        await reconnect_with_backoff(user_id)

async def send_ping(websocket, user_id):
    ping_message = json.dumps({"id": str(uuid.uuid4()), "action": "PING"})
    await websocket.send(ping_message)
    logger.debug(f"[{user_id}] Sent PING")

async def simulate_additional_activity(websocket, user_id):
    # Simulasi aktivitas tambahan untuk membuat koneksi terlihat lebih alami
    actions = ["REQUEST_DATA", "FETCH_STATUS", "UPDATE_INFO"]
    action = random.choice(actions)
    additional_message = json.dumps({"id": str(uuid.uuid4()), "action": action, "data": {}})
    await websocket.send(additional_message)
    logger.debug(f"[{user_id}] Sent {action} request")

async def get_unique_proxies(user_id, num_proxies):
    # Mendapatkan hingga num_proxies yang unik untuk setiap user_id
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
    # Lepaskan semua proxy yang digunakan oleh user_id setelah sesi selesai
    for proxy in usage_stats[user_id]["proxy"]:
        used_proxies.discard(proxy)
    usage_stats[user_id]["proxy"].clear()

async def reconnect_with_backoff(user_id, failed_proxy):
    delay = 5  # Delay awal untuk koneksi ulang
    max_retries = 10
    retries = 0
    
    while retries < max_retries:
        proxies = await get_unique_proxies(user_id, 5)
        if proxies:
            logger.info(f"[{user_id}] Attempting reconnection with new proxies: {proxies}")
            usage_stats[user_id]["reconnects"] += 1
            for proxy in proxies:
                try:
                    await connect_to_wss(user_id)
                    return
                except Exception as e:
                    logger.error(f"[{user_id}] Reconnect error: {e}. Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                    retries += 1
                    delay *= 2  # Exponential backoff untuk retry
    logger.error(f"[{user_id}] Failed to reconnect after {max_retries} attempts.")

async def initialize_connection_with_jitter(user_id):
    jitter = random.uniform(1, 5)  # Delay awal antara 1-5 detik
    await asyncio.sleep(jitter)
    await connect_to_wss(user_id)

async def main():
    tasks = [initialize_connection_with_jitter(user_id) for user_id in user_fingerprints.keys()]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    logger.add("connection_logs.log", rotation="5 MB", retention="7 days", level="INFO")
    asyncio.run(main())
