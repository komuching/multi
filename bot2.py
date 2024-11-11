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
from urllib.parse import urlparse

# Fungsi untuk membuat Sec-WebSocket-Key acak
def generate_websocket_key():
    key = base64.b64encode(uuid.uuid4().bytes).decode('utf-8')
    return key

# Fungsi untuk menghasilkan Device ID acak berdasarkan proxy
def generate_device_id(socks5_proxy):
    return str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))

# Fungsi untuk menghasilkan Browser ID acak
def generate_browser_id():
    return str(uuid.uuid4())

# Fungsi untuk menghasilkan User-Agent acak berdasarkan platform (Mac, Windows, Linux)
def generate_user_agent():
    platforms = ["windows", "linux", "mac"]
    platform = random.choice(platforms)
    
    try:
        user_agent = UserAgent(os=platform, platforms="pc", browsers="chrome")
        return user_agent.random
    except Exception as e:
        logger.warning(f"Error occurred during getting browser: {e}, using fallback User-Agent.")
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Fungsi untuk mem-parsing string proxy
def parse_proxy(proxy):
    parsed = urlparse(proxy)
    if parsed.scheme not in ["http", "https", "socks5"]:
        raise ValueError(f"Unsupported proxy scheme: {parsed.scheme}")

    if not parsed.hostname or not parsed.port or not parsed.username or not parsed.password:
        raise ValueError("Invalid proxy format. Please provide a complete proxy URL with username, password, host, and port.")

    return {
        "scheme": parsed.scheme,
        "username": parsed.username,
        "password": parsed.password,
        "host": parsed.hostname,
        "port": int(parsed.port)  # Convert port to integer
    }

async def connect_to_wss(socks5_proxy, user_id):
    try:
        proxy_info = parse_proxy(socks5_proxy)
        logger.info(f"Parsed Proxy Info: {proxy_info}")
    except ValueError as e:
        logger.error(f"[{user_id}] Invalid proxy: {e}")
        return

    device_id = generate_device_id(socks5_proxy)
    browser_id = generate_browser_id()
    random_user_agent = generate_user_agent()

    logger.info(f"[{user_id}] Device ID: {device_id} | Browser ID: {browser_id} | Proxy: {socks5_proxy}")

    retry_count = 0
    max_retries = 5

    while True:
        try:
            await asyncio.sleep(random.uniform(1, 5))

            custom_headers = {
                "User-Agent": random_user_agent,
                "Origin": "chrome-extension://ilehaonighjijnmpnagapkhpcdbhclfg",
                "Referer": "chrome-extension://ilehaonighjijnmpnagapkhpcdbhclfg",
                "Sec-WebSocket-Version": "13",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9",
                "Upgrade": "websocket",
                "Connection": "Upgrade",
                "Pragma": "no-cache",
                "Cache-Control": "no-cache",
                "Sec-WebSocket-Key": generate_websocket_key(),
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

            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:

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
                        await asyncio.sleep(5)

                asyncio.create_task(send_ping())

                while True:
                    try:
                        response = await websocket.recv()
                        message = json.loads(response)
                        logger.info(f"[{user_id}] Received: {message}")
                        
                        if message.get("action") == "AUTH":
                            auth_response = {
                                "id": message["id"],
                                "origin_action": "AUTH",
                                "result": {
                                    "browser_id": browser_id,
                                    "user_id": user_id,
                                    "user_agent": custom_headers['User-Agent'],
                                    "timestamp": int(time.time()),
                                    "device_type": "extension",
                                    "version": "4.26.2",
                                    "extension_id": "lkbnfiajjmbhnfledhphioinpickokdi"
                                }
                            }
                            logger.debug(f"[{user_id}] Sending AUTH response: {auth_response}")
                            await websocket.send(json.dumps(auth_response))
                        
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
            await asyncio.sleep(random.uniform(3, 7))

async def main():
    # Membaca file user ID
    with open('user_ids.txt', 'r') as user_file:
        user_ids = user_file.read().splitlines()
    
    logger.info(f"Jumlah akun: {len(user_ids)}")
    
    # Membaca file proxy dengan validasi
    with open('proxies.txt', 'r') as proxy_file:
        proxies = []
        for line in proxy_file:
            stripped_line = line.strip()
            if stripped_line:
                proxies.append(stripped_line)
            else:
                logger.warning("Ditemukan entri proxy kosong di file 'proxies.txt'. Abaikan entri ini.")
    
    tasks = []
    proxy_count = len(proxies)
    user_count = len(user_ids)
    
    for i in range(max(proxy_count, user_count)):
        user_id = user_ids[i % user_count]
        proxy = proxies[i % proxy_count]
        tasks.append(asyncio.create_task(connect_to_wss(proxy, user_id)))
        
        await asyncio.sleep(random.uniform(3, 7))
    
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
