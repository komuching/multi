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
        logger.info(f"Memuat {len(proxy_list)} proxy dari {filename}")
    except FileNotFoundError:
        logger.error(f"File {filename} tidak ditemukan. Harap buat file tersebut dan tambahkan proxy Anda.")
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
        logger.info(f"Memuat {len(user_fingerprints)} user ID dari {filename}")
    except FileNotFoundError:
        logger.error(f"File {filename} tidak ditemukan. Harap buat file tersebut dan tambahkan user ID Anda.")
    return user_fingerprints

# Memuat proxy_list dan user_fingerprints dari file eksternal
proxy_list = load_proxies_from_file()
user_fingerprints = load_user_ids_from_file()

used_proxies = set()  # Set untuk melacak proxy yang sedang digunakan
usage_stats = {user_id: {"reconnects": 0, "proxy": [], "connected_time": 0} for user_id in user_fingerprints.keys()}

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
    uri = random.choice([
        "wss://proxy.wynd.network:4444/", 
        "wss://proxy.wynd.network:4650/", 
        "wss://proxy2.wynd.network:4444"
    ])

    for proxy in proxies:
        headers = generate_extension_headers(user_id, proxy)
        try:
            usage_stats[user_id]["proxy"].append(proxy)
            async with proxy_connect(uri, proxy=Proxy.from_url(proxy), ssl=ssl_context, extra_headers=headers) as websocket:
                start_time = time.time()
                logger.info(f"[{user_id}] Terhubung: device_id={device_id}, proxy={proxy}")
                await simulate_activity(websocket, user_id, start_time)
        except Exception as e:
            logger.error(f"[{user_id}] Kesalahan koneksi dengan proxy {proxy}: {e}")
            await reconnect_with_backoff(user_id, proxy)

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
    logger.info(f"[{user_id}] Menggunakan User-Agent '{user_agent}' untuk proxy '{proxy}'")
    return headers

async def simulate_activity(websocket, user_id, start_time):
    try:
        active_duration = 7200  # 2 jam
        idle_duration = 180  # 3 menit sebelum reconnect
        end_time = start_time + active_duration
        
        while time.time() < end_time:
            # Mengirim PING setiap 10-20 detik
            await send_ping(websocket, user_id)
            await asyncio.sleep(random.uniform(10, 20))

            # Menerima dan menangani pesan dari server
            try:
                response = await websocket.recv()
                await handle_message(response, websocket, user_id)
            except Exception as e:
                logger.error(f"[{user_id}] Kesalahan saat menerima pesan: {e}")
                break

            # Simulasi aktivitas tambahan setiap 30-60 detik
            await simulate_additional_activity(websocket, user_id)
            await asyncio.sleep(random.uniform(30, 60))
            
            # Logging setiap 10 menit
            connected_duration = int(time.time() - start_time)
            usage_stats[user_id]["connected_time"] = connected_duration
            logger.info(f"[{user_id}] Terhubung selama {connected_duration} detik menggunakan proxy {usage_stats[user_id]['proxy']} dengan {usage_stats[user_id]['reconnects']} reconnect")
        
        await websocket.close()
        logger.info(f"[{user_id}] Terputus setelah 120 menit. Menyambung kembali setelah {idle_duration // 60} menit.")
        release_proxies(user_id)
        await asyncio.sleep(idle_duration)
        await reconnect_with_backoff(user_id)
    except Exception as e:
        logger.error(f"[{user_id}] Kesalahan selama aktivitas: {e}")
        await reconnect_with_backoff(user_id)

async def handle_message(response, websocket, user_id):
    """Menangani pesan yang diterima dari server."""
    try:
        message = json.loads(response)
        action = message.get("action")
        
        if action == "PONG":
            await send_pong(websocket, user_id, message["id"])
            logger.debug(f"[{user_id}] Mengirim PONG sebagai respons untuk PONG dari server")
        
        elif action == "REQUEST_DATA":
            await handle_request_data(websocket, user_id)
            logger.debug(f"[{user_id}] Menangani aksi REQUEST_DATA")

        elif action == "UPDATE_INFO":
            await handle_update_info(websocket, user_id)
            logger.debug(f"[{user_id}] Menangani aksi UPDATE_INFO")
        
        elif action == "AUTH":
            await send_auth_response(websocket, user_id)
            logger.debug(f"[{user_id}] Mengirim respons AUTH ke server")

        else:
            logger.warning(f"[{user_id}] Menerima aksi '{action}' yang tidak dikenal dari server")
    except json.JSONDecodeError:
        logger.error(f"[{user_id}] Gagal mendekode pesan: {response}")

async def send_auth_response(websocket, user_id):
    """Mengirim respons AUTH ke server."""
    auth_response = {
        "id": str(uuid.uuid4()),
        "action": "AUTH_RESPONSE",
        "result": {
            "browser_id": str(uuid.uuid4()),
            "user_id": user_id,
            "user_agent": user_fingerprints[user_id]["user_agent"],
            "timestamp": int(time.time()),
            "version": "1.0.0"
        }
    }
    await websocket.send(json.dumps(auth_response))
    logger.debug(f"[{user_id}] Mengirim AUTH_RESPONSE dengan browser_id {auth_response['result']['browser_id']}")

async def send_ping(websocket, user_id):
    ping_message = json.dumps({"id": str(uuid.uuid4()), "action": "PING"})
    await websocket.send(ping_message)
    logger.debug(f"[{user_id}] Mengirim PING")

async def send_pong(websocket, user_id, message_id):
    pong_message = json.dumps({"id": message_id, "action": "PONG"})
    await websocket.send(pong_message)
    logger.debug(f"[{user_id}] Mengirim PONG sebagai respons untuk pesan {message_id}")

async def handle_request_data(websocket, user_id):
    data_response = json.dumps({
        "id": str(uuid.uuid4()), 
        "action": "RESPONSE_DATA", 
        "data": {"info": "Sample data response"}
    })
    await websocket.send(data_response)
    logger.debug(f"[{user_id}] Mengirim RESPONSE_DATA sebagai respons untuk REQUEST_DATA")

async def handle_update_info(websocket, user_id):
    update_response = json.dumps({
        "id": str(uuid.uuid4()), 
        "action": "INFO_UPDATED", 
        "status": "Pembaharuan berhasil"
    })
    await websocket.send(update_response)
    logger.debug(f"[{user_id}] Mengirim INFO_UPDATED sebagai respons untuk UPDATE_INFO")

async def simulate_additional_activity(websocket, user_id):
    actions = ["REQUEST_DATA", "FETCH_STATUS", "UPDATE_INFO"]
    action = random.choice(actions)
    additional_message = json.dumps({"id": str(uuid.uuid4()), "action": action, "data": {}})
    await websocket.send(additional_message)
    logger.debug(f"[{user_id}] Mengirim permintaan {action}")

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
            logger.info(f"[{user_id}] Mencoba menyambung kembali dengan proxy baru: {proxies}")
            usage_stats[user_id]["reconnects"] += 1
            for proxy in proxies:
                try:
                    await connect_to_wss(user_id)
                    return
                except Exception as e:
                    logger.error(f"[{user_id}] Kesalahan reconnect: {e}. Mencoba lagi dalam {delay} detik...")
                    await asyncio.sleep(delay)
                    retries += 1
                    delay *= 2
    logger.error(f"[{user_id}] Gagal menyambung kembali setelah {max_retries} percobaan.")

async def initialize_connection_with_jitter(user_id):
    jitter = random.uniform(1, 5)
    await asyncio.sleep(jitter)
    await connect_to_wss(user_id)

async def main():
    tasks = [initialize_connection_with_jitter(user_id) for user_id in user_fingerprints.keys()]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    logger.add("connection_logs.log", rotation="5 MB", retention="7 days", level="INFO")
    asyncio.run(main())
