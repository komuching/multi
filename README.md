**Multi Grass**
Multi Grass adalah bot yang dirancang untuk mensimulasikan aktivitas ekstensi Chrome, dengan koneksi yang diatur agar tampak seperti interaksi ekstensi asli di browser Chrome. Setiap user ID dapat menggunakan beberapa proxy berbeda secara bersamaan dengan user-agent berbasis Chrome. Bot ini menggunakan WebSocket untuk berkomunikasi dengan server eksternal dan meniru perilaku yang alami.
   
**Fitur Utama**
User-Agent berbasis Chrome yang Unik: Setiap user ID menggunakan user-agent berbasis Chrome yang unik untuk meniru ekstensi asli.
Manajemen Proxy Dinamis: Setiap user ID dapat menggunakan hingga 5 proxy berbeda secara bersamaan.
Simulasi Aktivitas Tambahan: Selain PING, terdapat aktivitas tambahan seperti REQUEST_DATA dan FETCH_STATUS untuk meniru interaksi ekstensi yang lebih alami.
Reconnect Otomatis dengan Exponential Backoff: Jika terjadi kegagalan koneksi, bot akan mencoba reconnect menggunakan interval yang meningkat untuk menghindari pola reconnect yang berulang cepat.
  
Python 3.8 atau lebih baru: Pastikan Python sudah diinstal pada sistem.
Paket Python yang Diperlukan: Instalasi beberapa paket, termasuk asyncio, loguru, uuid, fake_useragent, dan websockets-proxy.  

---------------------------------------------------------------------------------------
---------------------------------------------------------------------------------------
Install:
```
sudo apt update && sudo apt upgrade -y
```
```
git clone https://github.com/komuching/multi.git
cd multi
```

```
sudo apt install pip -y
```
```
sudo apt install python3 python3-pip -y
```  
```
pip install requests loguru websockets==12.0 fake_useragent websockets_proxy asyncio loguru uuid fake_useragent websockets-proxy

```

  
```
pip install -r requirements.txt
```
------------------   

isi proxies.txt DAN user_ids.txt Sesuai Kebutuhan..   

---------------------
Mulai Bot
```
python bot.py
```

Credits: @Qodratjr (x)
Join: https://t.me/komucing
