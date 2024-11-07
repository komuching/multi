async def simulate_activity(websocket, user_id, start_time):
    try:
        # Durasi aktivitas untuk 120 menit (7200 detik)
        active_duration = 7200  # 2 jam
        idle_duration = 180  # Istirahat selama 3 menit sebelum reconnect
        end_time = start_time + active_duration
        
        while time.time() < end_time:
            # Mengirim PING setiap 10-20 detik
            await send_ping(websocket, user_id)
            await asyncio.sleep(random.uniform(10, 20))

            # Menunggu respons dari server
            response = await websocket.recv()
            message = json.loads(response)
            if message.get("action") == "PONG":
                await send_pong(websocket, user_id, message["id"])
                logger.debug(f"[{user_id}] Sent PONG in response to server's PONG")

            # Simulasi aktivitas tambahan setiap 30-60 detik
            await simulate_additional_activity(websocket, user_id)
            await asyncio.sleep(random.uniform(30, 60))
            
            # Logging setiap 10 menit
            connected_duration = int(time.time() - start_time)
            usage_stats[user_id]["connected_time"] = connected_duration
            logger.info(f"[{user_id}] Connected for {connected_duration} seconds using proxies {usage_stats[user_id]['proxy']} with {usage_stats[user_id]['reconnects']} reconnects")
        
        # Setelah aktif selama 2 jam, tutup koneksi dan jeda 3 menit sebelum reconnect
        await websocket.close()
        logger.info(f"[{user_id}] Disconnected after 120 minutes. Reconnecting after {idle_duration // 60} minutes.")
        release_proxies(user_id)
        await asyncio.sleep(idle_duration)
        await reconnect_with_backoff(user_id)  # Reconnect dengan proxy baru
    except Exception as e:
        logger.error(f"[{user_id}] Error during activity: {e}")
        await reconnect_with_backoff(user_id)

async def send_ping(websocket, user_id):
    ping_message = json.dumps({"id": str(uuid.uuid4()), "action": "PING"})
    await websocket.send(ping_message)
    logger.debug(f"[{user_id}] Sent PING")

async def send_pong(websocket, user_id, message_id):
    # Mengirim PONG sebagai respons untuk menjaga koneksi tetap hidup
    pong_message = json.dumps({"id": message_id, "action": "PONG"})
    await websocket.send(pong_message)
    logger.debug(f"[{user_id}] Sent PONG in response to message {message_id}")
