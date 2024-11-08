import asyncio
import random
import ssl
import json
import time
import uuid
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent

# Metadata ekstensi yang harus konsisten
EXTENSION_ID = "lkbnfiajjmbhnfledhphioinpickokdi"
EXTENSION_VERSION = "4.26.2"

# Mengatur User-Agent secara acak untuk koneksi
user_agent = UserAgent()
platforms = ["Windows", "Linux", "Mac"]

async def connect_to_wss(socks5_proxy, user_id):
    # ID perangkat unik untuk setiap proxy
    device_id = str(uuid.uuid4())
    # Random platform untuk User-Agent
    platform = random.choice(platforms)
    random_user_agent = user_agent.random

    logger.info(f"[{user_id}] Device ID: {device_id} | Platform: {platform}")
    
    while True:
        try:
            # Penundaan acak sebelum koneksi untuk menghindari deteksi bot
            await asyncio.sleep(random.uniform(1, 5)) 

            custom_headers = {
                "User-Agent": random_user_agent,
                "Origin": f"chrome-extension://{EXTENSION_ID}"
            }

            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            urilist = ["wss://proxy.wynd.network:4444/", "wss://proxy.wynd.network:4650/"]
            uri = random.choice(urilist)
            server_hostname = "proxy.wynd.network"
            proxy = Proxy.from_url(socks5_proxy)
            
            logger.info(f"[{user_id}] Connecting to {uri} using proxy {socks5_proxy}")
            
            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:
                
                # Kirim pesan PING setiap 20 detik
                async def send_ping():
                    while True:
                        ping_message = json.dumps(
                            {"id": str(uuid.uuid4()), "version": EXTENSION_VERSION, "action": "PING", "data": {}}
                        )
                        logger.debug(f"[{user_id}] Sending PING: {ping_message}")
                        try:
                            await websocket.send(ping_message)
                        except Exception as e:
                            logger.warning(f"[{user_id}] send_ping encountered an error: {e}")
                            break
                        await asyncio.sleep(20)  # Interval PING: 20 detik

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
                                    "device_type": "extension",
                                    "version": EXTENSION_VERSION,
                                    "extension_id": EXTENSION_ID
                                }
                            }
                            logger.debug(f"[{user_id}] Sending AUTH response: {auth_response}")
                            await websocket.send(json.dumps(auth_response))
                        
                        # Menangani PONG
                        elif message.get("action") == "PONG":
                            pong_response = {"id": message["id"], "origin_action": "PONG"}
                            logger.debug(f"[{user_id}] Sending PONG: {pong_response}")
                            await websocket.send(json.dumps(pong_response))
                    
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
