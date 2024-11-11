import asyncio
import random
import ssl
import json
import time
import uuid
import base64
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent
import aiohttp

# Fungsi untuk membuat Sec-WebSocket-Key acak
def generate_websocket_key():
    # Menghasilkan string acak untuk Sec-WebSocket-Key
    key = base64.b64encode(uuid.uuid4().bytes).decode('utf-8')
    return key

# Fungsi untuk menghasilkan Device ID acak berdasarkan proxy
def generate_device_id(socks5_proxy):
    return str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))

# Fungsi untuk menghasilkan Browser ID acak
def generate_browser_id():
    return str(uuid.uuid4())  # Menghasilkan UUID acak untuk Browser ID

# Fungsi untuk menghasilkan User-Agent acak berdasarkan platform (Mac, Windows, Linux)
def generate_user_agent():
    platforms = ["windows", "linux", "mac"]
    platform = random.choice(platforms)
    
    user_agent = UserAgent(os=platform, platforms="pc", browsers="chrome")
    return user_agent.random

# Fungsi untuk menghubungkan ke WebSocket dengan timeout dan retry mekanisme
async def connect_to_wss(socks5_proxy, user_id):
    # Menghasilkan Device ID, Browser ID, dan WebSocket Key acak untuk setiap proxy
    device_id = generate_device_id(socks5_proxy)
    browser_id = generate_browser_id()
    random_user_agent = generate_user_agent()

    logger.info(f"[{user_id}] Device ID: {device_id} | Browser ID: {browser_id} | Proxy: {socks5_proxy}")

    retry_count = 0
    max_retries = 5  # Maksimum retry jika terjadi kesalahan

    while retry_count < max_retries:
        try:
            await asyncio.sleep(random.uniform(1, 5))  # Penundaan acak untuk menghindari deteksi bot

            custom_headers = {
                "User-Agent": random_user_agent,
                "Origin": "chrome-extension://ilehaonighjijnmpnagapkhpcdbhclfg",  # ID ekstensi Chrome
                "Referer": "chrome-extension://ilehaonighjijnmpnagapkhpcdbhclfg",  # Referer dari ekstensi
                "Sec-WebSocket-Version": "13",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9",  # Menghapus id-ID
                "Upgrade": "websocket",
                "Connection": "Upgrade",
                "Pragma": "no-cache",
                "Cache-Control": "no-cache",
                "Sec-WebSocket-Key": generate_websocket_key(),  # Generate acak untuk setiap koneksi
                "Sec-WebSocket-Extensions": "permessage-deflate; client_max_window_bits"
            }

            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            urilist = ["wss://proxy.wynd.network:4444/", "wss://proxy.wynd.network:4650/", "wss://proxy2.wynd.network:4444/", "wss://proxy2.wynd.network:4650/"]
            uri = random.choice(urilist)
            server_hostname = "proxy.wynd.network" if "proxy.wynd.network" in uri else "proxy2.wynd.network"
            proxy = Proxy.from_url(socks5_proxy)

            logger.info(f"[{user_id}] Connecting to {uri} using proxy {socks5_proxy}")

            # Timeout pengaturan untuk koneksi WebSocket
            timeout = aiohttp.ClientTimeout(total=10)  # 10 detik untuk total timeout koneksi
            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers, timeout=timeout) as websocket:

                async def send_ping():
                    while True:
                        ping_message = json.dumps(
                            {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}}
                        )
                        logger.debug(f"[{user_id}] Sending PING: {ping_message}")
                        try:
                            await websocket.send(ping_message)
                        except Exception as e:
                            logger.warning(f"[{user_id}] send_ping encountered an error: {e}")
                            break
                        await asyncio.sleep(5)  # Interval PING diturunkan menjadi 5 detik

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
                                    "browser_id": browser_id,  # Menggunakan Browser ID acak
                                    "user_id": user_id,
                                    "user_agent": custom_headers['User-Agent'],
                                    "timestamp": int(time.time()),
                                    "device_type": "extension",  # Metadata disamakan dengan Script 1
                                    "version": "4.26.2",  # Sama seperti Script 1
                                    "extension_id": "lkbnfiajjmbhnfledhphioinpickokdi"  # Sama seperti Script 1
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
            retry_count += 1
            logger.info(f"[{user_id}] Retrying ({retry_count}/{max_retries}) with proxy: {socks5_proxy}")
            if retry_count == max_retries:
                logger.error(f"[{user_id}] Max retries reached. Stopping.")
                break
            await asyncio.sleep(random.uniform(3, 7))  # Delay sebelum mencoba lagi

async def main():
    tasks = []
    # Membaca file user ID
    with open('user_ids.txt', 'r') as user_file:
        user_ids = user_file.read().splitlines()
    
    logger.info(f"Jumlah akun: {len(user_ids)}")
    
    # Membaca file proxy
    with open('proxies.txt', 'r') as proxy_file:
        proxies = proxy_file.read().splitlines()
    
    # Pastikan setiap proxy digunakan setidaknya sekali
    for i in range(max(len(proxies), len(user_ids))):
        user_id = user_ids[i % len(user_ids)]
        proxy = proxies[i % len(proxies)]
        tasks.append(connect_to_wss(proxy, user_id))  # Menambahkan setiap koneksi ke list tugas
    
    # Menjalankan semua task secara bersamaan
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
