import machine
import dht
import network
import socket
import time
import ntptime

# --- НАСТРОЙКИ ---
ssid = 'LiveS1'
password = 'PonSer$6522'
sensor_pin = 2  # GPIO 2 (D4)

# 1. Настройка Wi-Fi (Гарантированно выключаем раздачу)
ap = network.WLAN(network.AP_IF)
ap.active(False)

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

print('Connecting to WiFi', end='')
cnt = 0
while not wlan.isconnected() and cnt < 20:
    print('.', end='')
    time.sleep(1)
    cnt += 1

if wlan.isconnected():
    print('\nConnected! IP:', wlan.ifconfig()[0])


# 2. Настройка датчика и переменных
sensor = dht.DHT11(machine.Pin(sensor_pin))
temp_max, temp_min = -99, 99
h_max, h_min = 0, 100
t_now, h_now = "--", "--"
first_run = True

last_sensor_read = 0
sensor_interval = 2000  # Опрос каждые 2 секунды
try:
    ntptime.settime()
        #print("Time synced")
except:
        # print("Time sync failed")
    pass


# 3. Функция генерации HTML
def get_html():
    UTC_OFFSET = 3 * 3600

    try:
        t_tuple = time.localtime(time.time() + UTC_OFFSET)
        time_now = "{:02d}:{:02d}".format(t_tuple[3], t_tuple[4])
        date_now = "{:02d}.{:02d}.{:d}".format(t_tuple[2], t_tuple[1], t_tuple[0])
    except:
        time_now, date_now = "--:--", "--.--.----"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Метеостанция</title>
        <style>
            body {{ font-family: sans-serif; text-align: center; background: #2c3e50; color: white; }}
            .box {{ background: #34495e; padding: 20px; border-radius: 10px; display: inline-block; margin-top: 50px; min-width: 250px; }}
            .val {{ font-size: 30px; color: #FFFFF0; font-weight: bold; }}
            .stat {{ font-size: 20px; color: #ff6347; font-weight: bold; }}
            .statt {{ font-size: 20px; color: #3498db; font-weight: bold; }}
        </style>
        <meta http-equiv="refresh" content="3">
    </head>
    <body>
        <div class="box">
            <h1>{time_now}</h1>
            <h3>{date_now}</h3>
            <hr>
            <h2>Метеостанция</h2>
            <p>Температура: <span class="val">{t_now} &deg;C</span></p>
            <p>Влажность: <span class="val">{h_now} %</span></p>
            <hr>
            <hr>
            <p>Температура:</p>
            <p>Мин: <span class="statt">{temp_min}</span> | Макс: <span class="stat">{temp_max}</span></p>
            <hr>
            <p>Влажность:</p>
             <p>Мин: <span class="statt">{h_min}</span> | Макс: <span class="stat">{h_max}</span></p>
        </div>
    </body>
    </html>
    """


# 4. Настройка сервера
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('', 80))
s.listen(5)
s.settimeout(0.5)

print("Server started!")

# 5. Главный цикл
while True:
    # --- ОПРОС ДАТЧИКА (БЕЗ ТАЙМЕРА) ---
    if time.ticks_ms() - last_sensor_read > sensor_interval:
        try:
            sensor.measure()
            t = sensor.temperature()
            h = sensor.humidity()

            if t != 0 or h != 0:  # Проверка на мусорные данные
                t_now, h_now = t, h
                if first_run:
                    temp_max = temp_min = t
                    h_max = h_min = h
                    first_run = False
                else:
                    if t > temp_max: temp_max = t
                    if t < temp_min: temp_min = t
                    if h > h_max: h_max = h
                    if h < h_min: h_min = h
        except Exception as e:
            print("Sensor error")
        last_sensor_read = time.ticks_ms()

    # --- ОБРАБОТКА ЗАПРОСОВ СЕРВЕРА ---
    try:
        conn, addr = s.accept()
        # Ждем немного данных от клиента
        request = conn.recv(1024)

        # Отправляем ответ
        response = get_html()
        conn.send('HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n')
        conn.sendall(response)
        conn.close()
    except OSError:
        # Сюда попадаем каждые 0.5 сек, если никто не зашел на сайт
        pass
