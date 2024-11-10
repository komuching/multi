import asyncio
import random
import ssl
import json
import time
import uuid
from loguru import logger
from websockets_proxy import Proxy, proxy_connect

# Konfigurasi loguru untuk mencatat log ke layar dan file
logger.add("bot_debug.log", level="DEBUG", rotation="10 MB", retention="7 days")  # Retention dalam bahasa Inggris

# Daftar User-Agent statis (30 User-Agent)
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
                        logger.warning(f"[{user_id}] Waktu habis saat menunggu respons.")
                        break
                    except Exception as e:
                        logger.warning(f"[{user_id}] Kesalahan saat menerima pesan: {e}")
                        break

                ping_task.cancel()
                try:
                    await ping_task
                except asyncio.CancelledError:
                    logger.debug(f"[{user_id}] Tugas ping dibatalkan dengan aman.")
                break

        except asyncio.CancelledError:
            logger.warning(f"[{user_id}] Tugas dibatalkan.")
            break
        except Exception as e:
            retries += 1
            logger.error(f"[{user_id}] Kesalahan koneksi: {e}. Percobaan ulang {retries}/{max_retries}")
            if retries >= max_retries:
                logger.error(f"[{user_id}] Proxy {socks5_proxy} dianggap tidak aktif.")
                return False

    return True

# Fungsi utama
async def main():
    try:
        with open('user_ids.txt', 'r') as user_file:
            user_ids = user_file.read().splitlines()
        logger.info(f"Jumlah akun: {len(user_ids)}")

        with open('proxies.txt', 'r') as proxy_file:
            proxies = proxy_file.read().splitlines()

        if not user_ids:
            logger.error("Daftar UID kosong.")
            return
        if not proxies:
            logger.error("Daftar proxy kosong.")
            return

        active_proxies = proxies.copy()
        failed_proxies = {}

        while True:
            # Membersihkan proxy gagal jika waktu sudah lewat 2 menit
            now = time.time()
            retryable_proxies = [proxy for proxy, t in failed_proxies.items() if now - t >= 120]

            # Mencoba ulang proxy gagal
            for proxy in retryable_proxies:
                failed_proxies.pop(proxy, None)
                active_proxies.append(proxy)
                logger.info(f"Menambahkan ulang proxy gagal: {proxy}")

            # Jika tidak ada proxy aktif, isi ulang dari proxy utama
            if not active_proxies:
                logger.warning("Semua proxy gagal. Memuat ulang daftar proxy...")
                active_proxies = proxies.copy()

            # Membatasi jumlah koneksi paralel
            semaphore = asyncio.Semaphore(10)

            tasks = [
                asyncio.create_task(connect_to_wss(proxy, user_ids[0]))  # Fokus pada satu user_id
                for proxy in active_proxies
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)
            for idx, result in enumerate(results):
                proxy = active_proxies[idx]
                if isinstance(result, Exception):
                    logger.error(f"Proxy {proxy} gagal.")
                    failed_proxies[proxy] = time.time()
                    active_proxies.remove(proxy)

    except Exception as e:
        logger.error(f"Kesalahan di main: {e}")
    finally:
        logger.info("Tugas utama selesai.")

# Entry point
if __name__ == '__main__':
    logger.info("Memulai bot...")
    try:
        while True:
            try:
                asyncio.run(main())
            except Exception as e:
                logger.error(f"Kesalahan di loop utama: {e}. Restart...")
    except KeyboardInterrupt:
        logger.info("Bot dihentikan.")
