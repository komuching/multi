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

# Fungsi untuk membuat User-Agent secara acak
def generate_user_agent():
    os_list = [
        "Windows NT 10.0; Win64; x64",
        "Macintosh; Intel Mac OS X 10_15_7",
        "X11; Ubuntu; Linux x86_64"
    ]
    browsers = [
        "Mozilla/5.0 ({os}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36",
        "Mozilla/5.0 ({os}) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/{version}.0",
        "Mozilla/5.0 ({os}) AppleWebKit/537.36 (KHTML, like Gecko) Edge/{version}.0.0.0"
    ]
    os_choice = random.choice(os_list)
    browser_template = random.choice(browsers)
    browser_version = random.randint(90, 115)  # Random browser version between 90 and 115
    return browser_template.format(os=os_choice, version=browser_version)

# Fungsi koneksi WebSocket
async def connect_to_wss(socks5_proxy, user_id, retries=0, max_retries=5):
    user_agent = generate_user_agent()
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

                # Kirim PING
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
    while True:  # Restart loop utama jika terjadi error besar
        try:
            with open('user_ids.txt', 'r') as user_file:
                user_ids = user_file.read().splitlines()

            with open('proxies.txt', 'r') as proxy_file:
                proxies = proxy_file.read().splitlines()

            if not user_ids or not proxies:
                logger.error("Daftar UID atau Proxy kosong. Bot berhenti.")
                return

            user_id = user_ids[0]  # Fokus pada satu user_id

            while True:
                batch_size = 10  # Ubah sesuai kebutuhan
                for i in range(0, len(proxies), batch_size):
                    batch = proxies[i:i + batch_size]
                    tasks = [connect_to_wss(proxy, user_id) for proxy in batch]
                    await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Kesalahan fatal di loop utama: {e}. Bot akan mencoba restart.")
            await asyncio.sleep(5)  # Tunggu sebelum mencoba ulang

if __name__ == '__main__':
    logger.info("Memulai bot...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot dihentikan oleh pengguna.")
