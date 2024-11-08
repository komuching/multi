import asyncio
import random
import ssl
import json
import time
import uuid
from loguru import logger
from websockets_proxy import Proxy, proxy_connect

# Daftar User-Agent statis lengkap (30 User-Agent)
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

async def connect_to_wss(socks5_proxy, user_id):
    # Pilih User-Agent acak untuk proxy ini
    user_agent = random.choice(USER_AGENT_LIST)

    # Generate Device ID acak untuk setiap proxy
    device_id = str(uuid.uuid4())
    logger.info(f"[{user_id}] Device ID: {device_id} | Proxy: {socks5_proxy} | User-Agent: {user_agent}")

    while True:
        try:
            # Penundaan acak untuk menghindari deteksi bot
            await asyncio.sleep(random.uniform(1, 5))

            # Header dengan User-Agent
            custom_headers = {
                "User-Agent": user_agent
            }

            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # Pilihan URI WebSocket
            urilist = ["wss://proxy.wynd.network:4444/", "wss://proxy.wynd.network:4650/"]
            uri = random.choice(urilist)
            server_hostname = "proxy.wynd.network"
            proxy = Proxy.from_url(socks5_proxy)

            logger.info(f"[{user_id}] Connecting to {uri} using proxy {socks5_proxy}")

            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:

                # Kirim pesan PING setiap 15 detik
                async def send_ping():
                    while True:
                        ping_message = json.dumps(
                            {"id": str(uuid.uuid4()), "version": "4.28.2", "action": "PING", "data": {}}
                        )
                        logger.debug(f"[{user_id}] Sending PING: {ping_message}")
                        try:
                            await websocket.send(ping_message)

                            # Tunggu respons PONG dengan batas waktu 10 detik
                            try:
                                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                                message = json.loads(response)
                                if message.get("action") == "PONG":
                                    logger.debug(f"[{user_id}] PONG received successfully.")
                                else:
                                    logger.warning(f"[{user_id}] Unexpected response: {message}")
                            except asyncio.TimeoutError:
                                logger.warning(f"[{user_id}] PONG not received within timeout.")
                        except Exception as e:
                            logger.warning(f"[{user_id}] send_ping encountered an error: {e}")
                            break
                        await asyncio.sleep(15)  # Interval PING: 15 detik

                # Mulai tugas PING
                asyncio.create_task(send_ping())

                while True:
                    try:
                        response = await websocket.recv()
                        message = json.loads(response)
                        logger.info(f"[{user_id}] Received: {message}")

                        # Menangani AUTH
                        if message.get("action") == "AUTH":
                            auth_response = {
                                "id": message["id"],
                                "origin_action": "AUTH",
                                "result": {
                                    "browser_id": device_id,
                                    "user_id": user_id,
                                    "user_agent": custom_headers['User-Agent'],
                                    "timestamp": int(time.time()),
                                    "device_type": "desktop",  # Metadata desktop
                                    "version": "4.28.2",  # File version sesuai data aplikasi
                                    "product": "Grass",  # Nama produk sesuai informasi aplikasi
                                    "copyright": "© Grass Foundation, 2024. All rights reserved."
                                }
                            }
                            logger.debug(f"[{user_id}] Sending AUTH response: {auth_response}")
                            await websocket.send(json.dumps(auth_response))

                    except Exception as e:
                        logger.warning(f"[{user_id}] Error receiving message: {e}")
                        break
        except Exception as e:
            logger.error(f"[{user_id}] Connection error: {e}")
            logger.info(f"[{user_id}] Retrying with proxy: {socks5_proxy}")


async def main():
    # Membaca file user ID
    with open('user_ids.txt', 'r') as user_file:
        user_ids = user_file.read().splitlines()

    logger.info(f"Jumlah akun: {len(user_ids)}")

    # Membaca file proxy
    with open('proxies.txt', 'r') as proxy_file:
        proxies = proxy_file.read().splitlines()

    tasks = []
    proxy_count = len(proxies)
    user_count = len(user_ids)

    # Pastikan setiap proxy digunakan setidaknya sekali
    for i in range(max(proxy_count, user_count)):
        user_id = user_ids[i % user_count]
        proxy = proxies[i % proxy_count]
        tasks.append(asyncio.create_task(connect_to_wss(proxy, user_id)))

        # Tambahkan jeda acak antar koneksi
        await asyncio.sleep(random.uniform(3, 7))  # Delay antar koneksi (3-7 detik)

    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
