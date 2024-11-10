import asyncio
import random
import ssl
import json
import time
import uuid
from loguru import logger
from websockets_proxy import Proxy, proxy_connect

# Konfigurasi loguru untuk mencatat log ke layar dan file
logger.add("bot_debug.log", level="DEBUG", rotation="10 MB", retention="7 days")

# Daftar User-Agent statis
USER_AGENT_LIST = [
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, seperti Gecko) Firefox/109.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, seperti Gecko) Chrome/113.0.0.0 Safari/537.36",
]

# Fungsi untuk mengonversi proxy HTTP ke SOCKS5
def convert_proxy_to_socks5(proxy):
    if proxy.startswith("http://"):
        logger.debug(f"Mengonversi proxy {proxy} ke SOCKS5")
        return proxy.replace("http://", "socks5://", 1)
    return proxy

# Fungsi validasi proxy
async def validate_proxy(proxy):
    try:
        logger.debug(f"Memeriksa proxy dengan format: {proxy}")
        proxy_object = Proxy.from_url(proxy)
        test_uri = "http://www.google.com"
        async with proxy_connect(test_uri, proxy=proxy_object):
            logger.info(f"Proxy {proxy} valid.")
            return True
    except Exception as e:
        logger.warning(f"Proxy {proxy} tidak valid: {e}")
        return False

# Fungsi koneksi WebSocket
async def connect_to_wss(socks5_proxy, user_id, retries=0, max_retries=5):
    user_agent = random.choice(USER_AGENT_LIST)
    device_id = str(uuid.uuid4())

    logger.info(f"[{user_id}] Inisialisasi koneksi | Proxy: {socks5_proxy} | Device ID: {device_id} | User-Agent: {user_agent}")

    while retries < max_retries:
        try:
            custom_headers = {"User-Agent": user_agent}
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            urilist = ["wss://proxy.wynd.network:4444/", "wss://proxy.wynd.network:4650/"]
            uri = random.choice(urilist)
            proxy = Proxy.from_url(socks5_proxy)

            logger.info(f"[{user_id}] Menghubungkan ke {uri} menggunakan proxy {socks5_proxy}")

            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname="proxy.wynd.network",
                                     extra_headers=custom_headers) as websocket:
                logger.debug(f"[{user_id}] Berhasil terhubung ke {uri} | Device ID: {device_id} | Proxy: {socks5_proxy}")

                async def send_ping():
                    while True:
                        try:
                            ping_message = json.dumps({"id": str(uuid.uuid4()), "version": "4.28.2", "action": "PING", "data": {}})
                            logger.debug(f"[{user_id}] Mengirim PING: {ping_message}")
                            await websocket.send(ping_message)
                            await asyncio.sleep(5)
                        except Exception as e:
                            logger.warning(f"[{user_id}] Kesalahan saat mengirim PING: {e}")
                            break

                ping_task = asyncio.create_task(send_ping())

                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=20)
                        message = json.loads(response)
                        logger.info(f"[{user_id}] Pesan diterima: {message}")

                        if message.get("action") == "AUTH":
                            auth_response = {
                                "id": message["id"],
                                "origin_action": "AUTH",
                                "result": {
                                    "browser_id": device_id,
                                    "user_id": user_id,
                                    "user_agent": custom_headers['User-Agent'],
                                    "timestamp": int(time.time()),
                                    "device_type": "desktop",
                                    "version": "4.28.2",
                                    "product": "Grass",
                                }
                            }
                            logger.info(f"[{user_id}] Mengirim respons AUTH: {auth_response}")
                            await websocket.send(json.dumps(auth_response))
                    except asyncio.TimeoutError:
                        logger.warning(f"[{user_id}] Waktu habis menunggu respons.")
                    except Exception as e:
                        logger.warning(f"[{user_id}] Kesalahan saat menerima pesan: {e}")
                        break

                ping_task.cancel()
                try:
                    await ping_task
                except asyncio.CancelledError:
                    logger.debug(f"[{user_id}] Tugas ping dibatalkan.")
                break

        except Exception as e:
            retries += 1
            logger.error(f"[{user_id}] Kesalahan koneksi: {e}. Percobaan ulang {retries}/{max_retries}")
            await asyncio.sleep(2)

    if retries >= max_retries:
        logger.error(f"[{user_id}] Proxy {socks5_proxy} dianggap tidak aktif.")
        return False
    return True

# Fungsi utama
async def main():
    try:
        with open('user_ids.txt', 'r') as user_file:
            user_ids = user_file.read().splitlines()

        with open('proxies.txt', 'r') as proxy_file:
            proxies = [convert_proxy_to_socks5(proxy) for proxy in proxy_file.read().splitlines()]

        if not user_ids or not proxies:
            logger.error("Daftar UID atau Proxy kosong.")
            return

        user_id = user_ids[0]
        active_proxies = []

        logger.info("Memvalidasi proxy...")
        for proxy in proxies:
            if await validate_proxy(proxy):
                active_proxies.append(proxy)

        if not active_proxies:
            logger.error("Tidak ada proxy valid yang tersedia.")
            return

        while True:
            now = time.time()
            retryable_proxies = [proxy for proxy, t in failed_proxies.items() if now - t >= 120]
            for proxy in retryable_proxies:
                failed_proxies.pop(proxy, None)
                active_proxies.append(proxy)
                logger.info(f"Menambahkan ulang proxy gagal: {proxy}")

            batch_size = min(10, len(active_proxies))
            for i in range(0, len(active_proxies), batch_size):
                batch = active_proxies[i:i + batch_size]
                tasks = [connect_to_wss(proxy, user_id) for proxy in batch]
                await asyncio.gather(*tasks, return_exceptions=True)

    except Exception as e:
        logger.error(f"Kesalahan di main: {e}")

if __name__ == '__main__':
    logger.info("Memulai bot...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot dihentikan oleh pengguna.")
