import asyncio
import random
import ssl
import json
import time
import uuid
from loguru import logger
from websockets_proxy import Proxy, proxy_connect

# Daftar User-Agent statis (baru, 30 User-Agent)
USER_AGENT_LIST = [
    # User-Agent list here...
]

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
    logger.info(f"[{user_id}] Sending session report: {session_data}")
    try:
        await websocket.send(json.dumps(session_data))
    except Exception as e:
        logger.error(f"[{user_id}] Failed to send session report: {e}")

async def connect_to_wss(socks5_proxy, user_id, max_retries=5):
    user_agent = random.choice(USER_AGENT_LIST)
    device_id = str(uuid.uuid4())
    logger.info(f"[{user_id}] Device ID: {device_id} | Proxy: {socks5_proxy} | User-Agent: {user_agent}")

    session_start_time = time.time()
    retries = 0

    while retries < max_retries:
        try:
            logger.debug(f"[{user_id}] Sleeping before reconnecting.")
            await asyncio.sleep(random.uniform(1, 5))

            custom_headers = {"User-Agent": user_agent}
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

                logger.debug(f"[{user_id}] Successfully connected to {uri}")
                session_end_time = time.time()
                await send_session_report(websocket, session_start_time, session_end_time, user_id)
                session_start_time = time.time()

                async def send_ping():
                    while True:
                        ping_message = json.dumps(
                            {"id": str(uuid.uuid4()), "version": "4.28.2", "action": "PING", "data": {}}
                        )
                        logger.debug(f"[{user_id}] Sending PING: {ping_message}")
                        try:
                            await websocket.send(ping_message)
                        except Exception as e:
                            logger.warning(f"[{user_id}] send_ping encountered an error: {e}")
                            break
                        await asyncio.sleep(10)

                ping_task = asyncio.create_task(send_ping())

                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=20)
                        message = json.loads(response)
                        logger.info(f"[{user_id}] Received: {message}")

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
                                    "copyright": "© Grass Foundation, 2024. All rights reserved."
                                }
                            }
                            logger.debug(f"[{user_id}] Sending AUTH response: {auth_response}")
                            await websocket.send(json.dumps(auth_response))
                    except asyncio.TimeoutError:
                        logger.warning(f"[{user_id}] Timeout waiting for response. Skipping to next proxy.")
                        break
                    except Exception as e:
                        logger.warning(f"[{user_id}] Error receiving message: {e}")
                        break

                ping_task.cancel()
                await ping_task
                break

        except asyncio.CancelledError:
            logger.warning(f"[{user_id}] Task was cancelled. Exiting gracefully.")
            break
        except Exception as e:
            retries += 1
            logger.error(f"[{user_id}] Connection error: {e}. Retry {retries}/{max_retries}")
            if retries >= max_retries:
                logger.error(f"[{user_id}] Max retries reached. Task aborted.")
                break

        logger.debug(f"[{user_id}] Loop iteration completed. Reconnecting...")

async def main():
    try:
        with open('user_ids.txt', 'r') as user_file:
            user_ids = user_file.read().splitlines()
        logger.info(f"Jumlah akun: {len(user_ids)}")

        with open('proxies.txt', 'r') as proxy_file:
            proxies = proxy_file.read().splitlines()

        tasks = []
        proxy_count = len(proxies)
        user_count = len(user_ids)

        logger.debug(f"Preparing tasks for proxies and users.")
        semaphore = asyncio.Semaphore(10)  # Batasi jumlah koneksi simultan

        async def limited_connect(proxy, user_id):
            async with semaphore:
                await connect_to_wss(proxy, user_id)

        for i in range(max(proxy_count, user_count)):
            user_id = user_ids[i % user_count]
            proxy = proxies[i % proxy_count]
            tasks.append(asyncio.create_task(limited_connect(proxy, user_id)))
            await asyncio.sleep(random.uniform(3, 7))

        await asyncio.gather(*tasks, return_exceptions=True)

    except Exception as e:
        logger.error(f"Unhandled exception in main: {e}")
    finally:
        logger.info("Main task completed or terminated.")

if __name__ == '__main__':
    logger.add("bot_debug.log", level="DEBUG", rotation="10 MB", retention="7 days")
    logger.info("Starting bot...")
    try:
        asyncio.run(main())
    except asyncio.CancelledError:
        logger.info("Bot terminated due to cancelled tasks.")
    except KeyboardInterrupt:
        logger.info("Bot terminated by user.")
    except Exception as e:
        logger.critical(f"Unhandled exception in asyncio: {e}")
    finally:
        logger.info("Bot shutdown completed.")
