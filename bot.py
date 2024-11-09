import asyncio
import random
import ssl
import json
import time
import uuid
import re
from loguru import logger
from websockets_proxy import Proxy, proxy_connect

# Konfigurasi loguru untuk mencatat log ke layar dan file
logger.add("bot_debug.log", level="DEBUG", rotation="10 MB", retention="7 days")

# Daftar User-Agent statis
USER_AGENT_LIST = [
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/109.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Edge/113.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/113.0.0.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/113.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/109.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/109.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/109.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/113.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Edge/113.0.0.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/113.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/109.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/109.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/109.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/113.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/109.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Edge/113.0.0.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/113.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/109.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/109.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/113.0.0.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/109.0"
]

# Fungsi untuk memvalidasi format proxy
def validate_proxy_format(proxy):
    proxy_pattern = re.compile(r"^(http|https|socks5)://[^\s:@]+(:\d+)?$")
    return proxy_pattern.match(proxy)

# Fungsi untuk memuat ulang proxy dari file
async def refresh_proxies():
    logger.info("Muat ulang daftar proxy...")
    try:
        with open('proxies.txt', 'r') as proxy_file:
            proxies = proxy_file.read().splitlines()
        valid_proxies = [proxy for proxy in proxies if validate_proxy_format(proxy)]
        if len(valid_proxies) != len(proxies):
            logger.warning(f"Beberapa proxy memiliki format tidak valid dan diabaikan.")
        return valid_proxies
    except Exception as e:
        logger.error(f"Kesalahan saat memuat ulang proxy: {e}")
        return []

# Fungsi untuk memuat ulang UID dari file
async def refresh_user_ids():
    logger.info("Muat ulang daftar UID...")
    try:
        with open('user_ids.txt', 'r') as user_file:
            user_ids = user_file.read().splitlines()
        valid_user_ids = [uid for uid in user_ids if re.match(r"^[a-zA-Z0-9_-]+$", uid)]
        if len(valid_user_ids) != len(user_ids):
            logger.warning("Beberapa UID tidak valid dan diabaikan.")
        return valid_user_ids
    except Exception as e:
        logger.error(f"Kesalahan saat memuat ulang UID: {e}")
        return []

# Fungsi untuk mengirim laporan sesi terakhir
async def send_session_report(websocket, start_time, end_time, user_id):
    session_data = {
        "action": "SESSION_REPORT",
        "data": {
            "user_id": user_id,
            "start_time": start_time,
            "end_time": end_time
        }
    }
    logger.info(f"[{user_id}] Mengirim laporan sesi: {session_data}")
    try:
        await websocket.send(json.dumps(session_data))
    except Exception as e:
        logger.error(f"[{user_id}] Gagal mengirim laporan sesi: {e}")

# Fungsi untuk mengelola koneksi WebSocket
async def connect_to_wss(socks5_proxy, user_id, max_retries=5):
    user_agent = random.choice(USER_AGENT_LIST)
    device_id = str(uuid.uuid4())
    logger.info(f"[{user_id}] ID Perangkat: {device_id} | Proxy: {socks5_proxy} | User-Agent: {user_agent}")

    retries = 0

    while retries < max_retries:
        try:
            logger.debug(f"[{user_id}] Tidur sejenak sebelum mencoba ulang koneksi.")
            await asyncio.sleep(random.uniform(1, 5))

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

                logger.debug(f"[{user_id}] Berhasil terhubung ke {uri}")

                async def send_ping():
                    while True:
                        try:
                            ping_message = json.dumps(
                                {"id": str(uuid.uuid4()), "version": "4.28.2", "action": "PING", "data": {}}
                            )
                            logger.debug(f"[{user_id}] Mengirim PING: {ping_message}")
                            await websocket.send(ping_message)
                            await asyncio.sleep(5)
                        except Exception as e:
                            logger.warning(f"[{user_id}] Terjadi kesalahan saat mengirim PING: {e}")
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
                                    "copyright": "© Grass Foundation, 2024."
                                }
                            }
                            logger.debug(f"[{user_id}] Mengirim respons AUTH: {auth_response}")
                            await websocket.send(json.dumps(auth_response))
                    except asyncio.TimeoutError:
                        logger.warning(f"[{user_id}] Waktu habis saat menunggu respons. Beralih ke proxy berikutnya.")
                        break
                    except Exception as e:
                        logger.warning(f"[{user_id}] Kesalahan saat menerima pesan: {e}")
                        break

                ping_task.cancel()
                await ping_task
                break

        except asyncio.CancelledError:
            logger.warning(f"[{user_id}] Tugas dibatalkan. Keluar dengan baik.")
            break
        except Exception as e:
            retries += 1
            logger.error(f"[{user_id}] Kesalahan koneksi: {e}. Percobaan ulang {retries}/{max_retries}")
            if retries >= max_retries:
                logger.error(f"[{user_id}] Proxy {socks5_proxy} sekarang dianggap tidak aktif.")
                return False

    logger.debug(f"[{user_id}] Iterasi selesai. Mencoba ulang...")
    return True

# Fungsi utama
async def main():
    try:
        user_ids = await refresh_user_ids()
        proxies = await refresh_proxies()

        if not user_ids:
            logger.error("Daftar UID kosong. Bot tidak dapat berjalan.")
            return
        if not proxies:
            logger.error("Daftar proxy kosong. Bot masuk mode standby.")
            return

        active_proxies = proxies.copy()

        while True:
            if not active_proxies:
                logger.warning("Tidak ada proxy aktif. Standby selama 60 detik...")
                await asyncio.sleep(60)
                active_proxies = await refresh_proxies()
                continue

            semaphore = asyncio.Semaphore(10)
            tasks = [
                asyncio.create_task(connect_to_wss(proxy, user_ids[idx % len(user_ids)]))
                for idx, proxy in enumerate(active_proxies)
            ]

            await asyncio.gather(*tasks, return_exceptions=True)

    except Exception as e:
        logger.error(f"Kesalahan tak terduga di main: {e}")
    finally:
        logger.info("Tugas utama selesai atau dihentikan.")

# Entry point
if __name__ == '__main__':
    logger.info("Memulai bot...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot dihentikan oleh pengguna.")
    except Exception as e:
        logger.critical(f"Kesalahan tidak terduga: {e}")
    finally:
        logger.info("Bot berhasil dimatikan.")
