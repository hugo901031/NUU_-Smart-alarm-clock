from machine import Pin, PWM, RTC
#from umqtt.robust import MQTTClient
import network, urequests, ujson
import time, ntptime, utime
import sys, select
import uasyncio as asyncio
import socket


# 初始化 Wi-Fi 連線指示燈
led = Pin(15, Pin.OUT)
led.value(0)

# 你的 Wi-Fi 名稱與密碼
SSID = '你的 Wi-Fi 名稱'
PASSWORD = '你的 Wi-Fi 密碼'

# 你的 GitHub 個人存取權杖（PAT）
GITHUB_TOKEN = "你的 PAT"

# 定義 AIO 的 MQTT 使用者名稱和金鑰
AIO_USER = '你的 AIO 使用者名稱'
AIO_KEY = '你的 AIO 金鑰'

# 星期名稱對應表（可選中文或英文）
WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]
#WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# 定義音符頻率串列 (單位 Hz)，0 表示靜音
NOTES = [262, 330, 294, 196, 0,
         262, 294, 330, 262, 0,
         330, 262, 294, 196, 0,
         196, 294, 330, 262, 0]

# ============================================================
# 🧩 render_template() — 簡易 HTML 模板渲染
# ============================================================
def render_template(file, **kwargs):
    """
    讀取指定 HTML 檔案，將內容中 {key} 替換成 kwargs 的值。
    例如 render_template("index.html", time="10:30", alarms="...")

    HTML 範例：
        <p>目前時間：{time}</p>
        <ul>{alarms}</ul>
    """
    try:
        with open(file, "r") as f:
            html = f.read()
    except Exception as e:
        return "<h1>404 File Not Found</h1><p>%s</p>" % e

    # 簡單字串替換
    for key, value in kwargs.items():
        html = html.replace("{" + key + "}", str(value))
        
    return html

def now_time(tz=8, sync=False):
    """
    傳回目前時間字串 (YYYY-MM-DD HH:MM:SS)
    參數：
      tz   ：時區偏移，預設台灣 UTC+8
      sync ：若為 True，會嘗試同步 NTP 時間（需 Wi-Fi）
    """
    # 若要求同步且有 Wi-Fi 連線
    if sync:
        try:
            sta = network.WLAN(network.STA_IF)
            if ntptime and sta.isconnected():
                ntptime.host = "pool.ntp.org"
                ntptime.settime()
                print("⏰ 已從 NTP 更新時間")
        except Exception as e:
            print("⚠️ NTP 同步失敗：", e)

    # 取得當前 UTC 時間 + 時區偏移
    try:
        t = list(utime.localtime(utime.time()))
        return "%04d-%02d-%02d %02d:%02d:%02d" % (t[0], t[1], t[2], t[3], t[4], t[5])
    except Exception as e:
        print("⚠️ 取得時間失敗：", e)
        return "0000-00-00 00:00:00"
    

class WebRequest:
    """封裝簡易的 HTTP 請求物件"""
    def __init__(self, method, path, args, body=""):
        self.method = method
        self.path = path
        self.args = args
        self.body = body


class WebApp:
    def __init__(self, title="MicroPython WebApp"):
        self.title = title
        self.routes = {}

    def route(self, path):
        def wrapper(func):
            self.routes[path] = func
            return func
        return wrapper

    async def start(self, port=80):
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', port))
        s.listen(5)
        s.setblocking(False)

        sta = network.WLAN(network.STA_IF)
        ap = network.WLAN(network.AP_IF)
        print("STA:", sta.ifconfig())
        print("AP:", ap.ifconfig())
        print("🌐 WebApp running on http://%s:%d/" % (sta.ifconfig()[0], port))

        while True:
            try:
                client, addr = s.accept()  # non-blocking 模式下，若無連線會丟 OSError
                asyncio.create_task(self.handle_client(client))
            except OSError:
                # 沒有連線就先讓出控制權
                await asyncio.sleep(0.05)
            except Exception as e:
                sys.print_exception(e)
                await asyncio.sleep(0.5)

    async def handle_client(self, client):
        try:
            client.settimeout(3)

            # 嘗試接收資料（HTTP 請求）
            try:
                req = client.recv(1024)
            except OSError as e:
                # 若 timeout 或 socket 被中斷
                if e.args[0] == 116:  # ETIMEDOUT
                    client.close()
                    return
                raise e

            if not req:
                client.close()
                return

            # ---- 解析 HTTP ----
            req = req.decode("utf-8", "ignore")
            line = req.split("\r\n")[0]
            parts = line.split(" ")
            method = parts[0]
            path = parts[1] if len(parts) > 1 else "/"
            
            body = ""
            if "\r\n\r\n" in req:
                _, body = req.split("\r\n\r\n", 1)

            # ---- 查詢參數解析 ----
            args = {}
            if "?" in path:
                base, query = path.split("?", 1)
                path = base
                for kv in query.split("&"):
                    if "=" in kv:
                        k, v = kv.split("=", 1)
                        args[k] = v

            # ---- 建立請求物件 ----
            request = WebRequest(method, path, args, body)

            # ---- 路由分派 ----
            if path in self.routes:
                result = self.routes[path](request)
                if isinstance(result, (dict, list)):
                    content = (
                        "HTTP/1.1 200 OK\r\n"
                        "Content-Type: application/json\r\n"
                        "Connection: close\r\n\r\n"
                        + str(result)
                    )
                else:
                    content = (
                        "HTTP/1.1 200 OK\r\n"
                        "Content-Type: text/html\r\n"
                        "Connection: close\r\n\r\n"
                        + str(result)
                    )
            else:
                content = (
                    "HTTP/1.1 404 NOT FOUND\r\n"
                    "Content-Type: text/html\r\n"
                    "Connection: close\r\n\r\n"
                    "<h1>404 Not Found</h1>"
                )

            # ---- 傳送資料 ----
            try:
                client.send(content.encode())
            except OSError:
                pass  # 若客戶端中斷，忽略即可

        except Exception as e:
            print("⚠️ handle_client error:", e)

        finally:
            client.close()
            await asyncio.sleep(0)

    
# 控制 RGB LED 燈色，預設關燈
def rgb_led(r=0, g=0, b=0, rpin=37, gpin=35, bpin=33):
    # RGB LED 腳位 (數位輸出)
    rled = Pin(rpin, Pin.OUT)
    gled = Pin(gpin, Pin.OUT)
    bled = Pin(bpin, Pin.OUT)
    
    # 設定 RGB LED 電位高低
    rled.value(r)
    gled.value(g)
    bled.value(b)
    
    return rled, gled, bled


# 使用 PWM（脈衝寬度調變）控制 RGB LED 的顏色與亮度，前四參數值輸入範圍 0~255
def set_rgb_bright(red, green, blue, brightness, rpin=37, gpin=35, bpin=33):
    # 初始化 PWM 物件，設定頻率為 1000Hz，初始占空比為 0
    rled = PWM(Pin(rpin), freq=1000, duty=0)
    gled = PWM(Pin(gpin), freq=1000, duty=0)
    bled = PWM(Pin(bpin), freq=1000, duty=0)
    
    # 將 RGB 值與亮度縮放至 PWM 占空比範圍 (0~1023)
    # 公式：(color/255) * 1023 * (brightness/255)
    adjusted_r = int((red/255) * 1023 * (brightness/255))
    adjusted_g = int((green/255) * 1023 * (brightness/255))
    adjusted_b = int((blue/255) * 1023 * (brightness/255))
    
    # 設定 PWM 占空比，控制 LED 顏色與亮度
    rled.duty(adjusted_r)
    gled.duty(adjusted_g)
    bled.duty(adjusted_b)


# 連線 Wi-Fi
def connect_wifi(ssid=SSID, password=PASSWORD):   
    # 建立工作站模式的無線網路介面
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    
    # 等待 Wi-Fi 連線，直到連線成功
    while not wlan.isconnected():
        pass
    print("----Wi-Fi 連線成功----")
    print(f"伺服器位址：{wlan.ifconfig()[0]}")
    
    # 連上 Wi-Fi 後亮起內建 LED
    led.value(1)


# 發送 POST 請求到 LLM API
def call_llm(system, prompt, model="openai/gpt-4.1-mini", bearer_token=GITHUB_TOKEN):
    print("----發送 API 請求----")
    
    response = urequests.post(
        "https://models.github.ai/inference/chat/completions",  # API 端點 URL
        headers={
            "Content-Type": "application/json",  # 設定請求內容類型為 JSON
            "Authorization": "Bearer " + bearer_token  # 設定認證標頭，使用 Bearer Token
        },
        data=ujson.dumps({  # 將請求資料轉為 JSON 格式並編碼為 UTF-8
            "messages": [  # API 請求的訊息結構
                {"role": "system", "content": system},  # 系統訊息，定義助手的角色和任務
                {"role": "user", "content": prompt}  # 使用者訊息，包含具體的提示內容
            ],
            "temperature": 1,  # 控制生成內容的隨機性，1 表示標準隨機性
            "top_p": 1,  # 控制生成內容的多樣性，1 表示不限制
            "model": model  # 指定使用的 LLM 模型
        }).encode('utf-8')  # 將 JSON 資料編碼為 UTF-8 格式
    )
    
    if response.status_code == 200:  # 檢查 API 請求是否成功
        result = response.json()  # 將回應內容解析為 JSON 格式
        answer = result["choices"][0]["message"]["content"].strip()  # 提取回應內容並移除多餘空白
        print(f"LLM 回應：{answer}")
    else:
        print(f"API 請求失敗，狀態碼：{response.status_code}")
    response.close()  # 關閉 HTTP 連線，釋放資源
    
    # 回傳 LLM 生成的文字
    return answer


# 設定 NTP 時間（本地時區為 UTC+8）
def set_time(timezone=8):
    # 嘗試從 NTP 伺服器同步 UTC 時間
    try:
        ntptime.settime()
        print("----NTP 時間同步成功----")
    except:
        print("----NTP 同步失敗----")
        
    # 將時間調整為本地時區
    utc_offset = timezone * 3600  # 小時轉為秒
    current_time = time.time() + utc_offset  # 當前 UTC 時間 (單位：秒) 加上時區偏移
    tm = time.localtime(current_time)  # 將本地時間 (單位：秒) 轉為本地時間元組
    
    # 設定系統的 RTC 時間，格式為 (年, 月, 日, 星期, 時, 分, 秒, 微秒)
    RTC().datetime((tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], tm[5], 0))


# 取得格式化的本地當前日期、星期、時間
def get_time():
    # 取得本地當前時間
    now = time.localtime()  
    # 格式化日期成 YYYY/MM/DD
    date_str = '{:04d}/{:02d}/{:02d}'.format(now[0], now[1], now[2])
    # 格式化時間成 HH:MM:SS
    time_str = '{:02d}:{:02d}:{:02d}'.format(now[3], now[4], now[5])
    # 根據星期索引取得對應的星期名稱，now[6] 是星期值 (0~6)
    weekday_str = WEEKDAYS[now[6]]

    return date_str, weekday_str, time_str


# 從 Google Apps Script 提供的 API 獲取股市新聞資料
def get_stock_news(topic, num):
    print("----Yahoo 股市新聞查詢中----")
    # Google Apps Script 的 API 網址，用於請求股市新聞資料
    url = (
        "https://script.google.com/macros/s/"
        "AKfycbxBGGlGz0dqV5k7BqyQxmkBKObkUMMhg_-"
        "BtxbRG8zX8nf21502qGlvpgPrnanm5zl6/exec"
    )
    # 發送 HTTP GET 請求，網址後附加查詢參數 "?topic=" 和 "&num="，分別傳入主題和新聞數量
    response = urequests.get(url + "?topic=" + topic + "&num=" + str(num))
    print(f"狀態碼：{response.status_code}")  # HTTP 回應的狀態碼 (200 表示成功)
    news_list = response.json()  # 將回應的 JSON 文字轉換為 Python 物件
    response.close()  # 關閉 HTTP 回應物件，釋放資源
    
    # 回傳抓取到的股市新聞資料
    return news_list


# 初始化揚聲器，預設靜音
def speaker_init(pin=6):
    speaker = PWM(Pin(pin, Pin.OUT))  # 揚聲器腳位 (輸出 PWM 訊號)
    speaker.duty(0)  # 將 PWM 占空比設為 0，即靜音
    speaker.freq(1000)  # 預設頻率
    
    return speaker


# 靜音並釋放揚聲器
def speaker_deinit(speaker):
    speaker.duty(0)  # 將 PWM 占空比設為 0，即靜音
    speaker.deinit()  # 釋放 PWM
    speaker = None  # 重置揚聲器為 None
    
    return speaker

    
# 播放音符，根據索引從音符串列中選擇頻率
def play_note(speaker, index, notes=NOTES):
    # 若當前音符為 0，則靜音揚聲器
    if notes[index % len(notes)] == 0:
        speaker.duty(0)  # 將 PWM 占空比設為 0，即靜音
    else:
        speaker.duty(512)  # 將 PWM 占空比設為 512 (約 50%)，即最大音量
        speaker.freq(notes[index % len(notes)])  # 設定 PWM 頻率為指定音符的頻率
        

# 初始化 MQTT 客戶端
def mqtt_client(aio_user=AIO_USER, aio_key=AIO_KEY):
    client = MQTTClient(client_id='',  # 用於識別裝置
                        server='io.adafruit.com',  # AIO 的 MQTT 伺服器位址
                        user=aio_user,
                        password=aio_key)
    return client


# 將位元組串列轉換為十六進位格式字串
def to_hex_string(byte_list):
    # 使用串列推導式將每個位元組轉為兩位十六進位格式，並連接成一個字串
    hex_str = ''.join([f'{byte:02X}' for byte in byte_list])
    
    return hex_str


# 獲取使用者非 ASCII 字元 (如中文) 的輸入
def u_input(prompt_msg):
    p = select.poll()  # 建立偵測物件
    p.register(
        sys.stdin,  # 偵測標準輸入
        select.POLLIN  # 偵測是否有資料待讀取
    ) 
    if p.poll(0):  # 若有資料待讀取
        sys.stdin.readline()  # 先清空已輸入資料 
    print(prompt_msg, end='')  # 顯示提示訊息，不換行
    user_input = sys.stdin.readline()  # 讀取輸入
    sys.stdout.write(user_input)
    
    return user_input.strip()  # 去除首尾空白
