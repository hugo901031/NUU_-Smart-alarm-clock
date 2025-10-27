import uasyncio as asyncio
from machine import Pin, I2C, PWM
from aiot_tools import WebApp, now_time, render_template
from ssd1306 import SSD1306_I2C
import time, utime, json, os
import network
from bitmap_font_tool import set_font_path, draw_text

# ----------------------------
# 🕓 OLED 初始化
# ----------------------------
i2c = I2C(0, scl=Pin(38), sda=Pin(40))
oled = SSD1306_I2C(128, 64, i2c)
set_font_path('./lib/fonts/fusion_bdf.12')
# ----------------------------
# 🎵 音階表與樂曲
# ----------------------------
NOTE_FREQS = {
    'C4': 262, 'D4': 294, 'E4': 330, 'F4': 349, 'G4': 392,
    'A4': 440, 'B4': 494, 'C5': 523, 'REST': 0
}

NOTES_STAR = [
    ('C4', 400), ('C4', 400), ('G4', 400), ('G4', 400),
    ('A4', 400), ('A4', 400), ('G4', 800), ('REST', 200),
    ('F4', 400), ('F4', 400), ('E4', 400), ('E4', 400),
    ('D4', 400), ('D4', 400), ('C4', 800)
]

NOTES_SKYCASTLE = [
    ('E4', 400), ('F4', 400), ('G4', 800),
    ('A4', 400), ('G4', 400), ('F4', 400), ('E4', 400),
    ('D4', 800), ('C4', 1200)
]


# ----------------------------
# wifi
# ----------------------------

def wifi_auto(ssid="YourWiFiName", password="YourWiFiPassword",
              ap_ssid="ESP32-Alarm", ap_pass="12345678"):
    """
    1️⃣ 先嘗試連上家中 Wi-Fi (STA 模式)
    2️⃣ 若 10 秒內連不上，改開 AP 模式 (Access Point)
    傳回實際使用的 IP
    """
    sta = network.WLAN(network.STA_IF)
    ap = network.WLAN(network.AP_IF)

    # 關閉 AP，先嘗試 STA
    ap.active(False)
    sta.active(True)
    sta.connect(ssid, password)

    print("嘗試連線 Wi-Fi:", ssid)
    for i in range(10):
        if sta.isconnected():
            print("已連上 Wi-Fi:", sta.ifconfig())
            return sta.ifconfig()[0]
        print(".", end="")
        time.sleep(1)

    # 若失敗則開啟 AP 模式
    print("\n無法連上 Wi-Fi，改開 AP 模式")
    sta.active(False)
    ap.active(True)
    ap.config(essid=ap_ssid, password=ap_pass)
    print("AP 模式啟動 SSID:", ap_ssid)
    print("IP:", ap.ifconfig()[0])
    return ap.ifconfig()[0]

# ----------------------------
# 🔊 喇叭函式
# ----------------------------
def speaker_init(pin=14):
    spk = PWM(Pin(pin, Pin.OUT))
    spk.duty(0)
    spk.freq(1000)
    return spk

def speaker_deinit(spk):
    spk.duty(0)
    spk.deinit()
    return None

def play_song(spk, notes):
    
    global is_ringing
    for note, duration in notes:
        if not is_ringing:  # 👈 中途關閉偵測
            break

        freq = NOTE_FREQS.get(note, 0)
        if freq == 0:
            spk.duty(0)
        else:
            spk.freq(freq)
            spk.duty(512)

        utime.sleep_ms(duration)

    spk.duty(0)
    print("🎵 播放結束（或被中斷）")

async def ring_task():
    #global is_ringing
    #is_ringing = True
    print("🔔 鬧鐘觸發，開始播放！")
    play_song(speaker, NOTES_STAR)
    #is_ringing = False
    

# ----------------------------
# ⏰ 鬧鐘管理
# ----------------------------
ALARM_FILE = "alarms.json"


# === 檔案存取 ===
def load_alarms():
    
    """開機時載入 alarms.json"""
    if ALARM_FILE in os.listdir():
        try:
            with open(ALARM_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print("⚠️ 載入鬧鐘失敗:", e)
            return []
    else:
        # 檔案不存在時建立空清單
        with open(ALARM_FILE, "w") as f:
            json.dump([], f)
        return []
        
    

def save_alarms(data):
    """儲存鬧鐘清單到 alarms.json"""
    try:
        with open(ALARM_FILE, "w") as f:
            json.dump(data, f)
            print("儲存鬧鐘成功:")
    except Exception as e:
        print("儲存鬧鐘失敗:", e)
        
def add_alarm(a):
    alarms.append(a)
    save_alarms(alarms)
    update_oled()

def delete_alarm(i):
    if 0 <= i < len(alarms):
        del alarms[i]
        save_alarms(alarms)
        update_oled()

def toggle_alarm(i):
    if 0 <= i < len(alarms):
        alarms[i]["enabled"] = not alarms[i].get("enabled", True)
        save_alarms(alarms)
        update_oled()

    
alarms = load_alarms()
speaker = speaker_init(14)
is_ringing = False


# ----------------------------
# 🕹 Web 控制 (手機/電腦)
# ----------------------------


app = WebApp("ESP32 智慧鬧鐘")

@app.route("/")
def index(req):
    alarm_html = ""
    for i, a in enumerate(alarms):
        alarm_html += f"<li>{a['y']}/{a['m']}/{a['d']} {a['h']}:{a['min']}</li>\n"
    return render_template("hw3_clock_v3.html", time=now_time(), alarms=alarm_html)


@app.route("/add")
def add(req):
    y,m,d,h,min = (req.args.get(k) for k in ["y","m","d","h","min"])
    alarms.append(dict(y=int(y), m=int(m), d=int(d), h=int(h), min=int(min)))
    save_alarms(alarms)
    return "<meta http-equiv='refresh' content='0;url=/' />"

@app.route("/del")
def delete(req):
    idx = int(req.args.get("i", -1))
    if 0 <= idx < len(alarms):
        del alarms[idx]
        save_alarms(alarms)
    return "<meta http-equiv='refresh' content='0;url=/' />"

@app.route("/api/alarms/reset")
def api_reset(req):
    """清空所有鬧鐘"""
    global alarms
    alarms = []
    save_alarms(alarms)
    print("🧹 所有鬧鐘已清空")
    return {"ok": True, "alarms": alarms}

@app.route("/api/alarms")
def api_alarms(req):
    """管理鬧鐘資料 (GET 取得全部, POST 新增或切換, DELETE 單筆或全部刪除)"""
    global alarms
    import ujson

    if req.method == "GET":
        print("📤 回傳 alarms =", alarms)
        return json.dumps({"alarms": alarms})

    elif req.method == "POST":
        try:
            data = ujson.loads(req.body)

            # ✅ 處理 toggle 指令
            if "toggle" in data:
                idx = int(data["toggle"])
                if 0 <= idx < len(alarms):
                    alarms[idx]["enabled"] = not alarms[idx].get("enabled", True)
                    print(f"🔁 切換鬧鐘 {idx+1} 為 {alarms[idx]['enabled']}")
                    save_alarms(alarms)
                return {"ok": True, "alarms": alarms}

            # ✅ 一般新增鬧鐘
            y = int(data.get("y", data.get("year", 0)))
            m = int(data.get("m", data.get("month", 0)))
            d = int(data.get("d", data.get("day", 0)))
            h = int(data.get("h", data.get("hour", 0)))
            minute = int(data.get("min", data.get("minute", 0)))
            new_alarm = {
                "y": y, "m": m, "d": d, "h": h, "min": minute,
                "enabled": data.get("enabled", True)
            }
            alarms.append(new_alarm)
            alarms = sorted(alarms, key=lambda a: (a['y'], a['m'], a['d'], a['h'], a['min']))
            save_alarms(alarms)
            print("✅ 新增鬧鐘：", new_alarm)
            return {"ok": True, "alarms": alarms}

        except Exception as e:
            print("⚠️ POST 錯誤：", e)
            return {"ok": False, "err": str(e)}

    elif req.method == "DELETE":
        try:
            data = ujson.loads(req.body or "{}")

            # ✅ 重置全部
            if data.get("all"):
                print("🧹 重置所有鬧鐘")
                alarms = []
                save_alarms(alarms)
                return {"ok": True, "alarms": alarms}

            # ✅ 刪除單筆
            i = int(data.get("i", -1))
            if 0 <= i < len(alarms):
                print("🗑 刪除鬧鐘：", alarms[i])
                del alarms[i]
                save_alarms(alarms)

            return {"ok": True, "alarms": alarms}

        except Exception as e:
            print("⚠️ DELETE 錯誤：", e)
            return {"ok": False, "err": str(e)}

        
@app.route("/api/time")
def api_time(req):
    return now_time()

@app.route("/api/ring/test")
def test(req):
    global is_ringing
    is_ringing = True
    asyncio.create_task(ring_task())  # ✅ 背景播放
    return {"ok": True, "msg": "Ringing"}

@app.route("/api/ring/stop")
def stop(req):
    global is_ringing
    is_ringing = False
    print("🔔 鬧鐘關閉！")
    speaker.duty(0)
    return "<meta http-equiv='refresh' content='0;url=/' />"

# ----------------------------
# 🕒 OLED 顯示與鬧鐘監聽
# ----------------------------


async def play_song_async(spk, notes):
    global is_ringing
    for note, duration in notes:
        if not is_ringing:
            print("🛑 停止播放")
            break
        freq = NOTE_FREQS.get(note, 0)
        if freq == 0:
            spk.duty(0)
        else:
            spk.freq(freq)
            spk.duty(512)
        await asyncio.sleep_ms(duration)
    spk.duty(0)
    print("🎵 播放結束")

async def ring_task():
    global is_ringing
    is_ringing = True
    print("🔔 鬧鐘觸發，開始連續播放！")

    try:
        while is_ringing:
            await play_song_async(speaker, NOTES_STAR)
    except Exception as e:
        print("⚠️ 播放錯誤:", e)

    speaker.duty(0)
    print("🛑 鬧鐘已停止")
    
    

async def oled_task():
    """持續更新 OLED 畫面：顯示時間 + 鬧鐘 + 鈴聲狀態"""
    global alarms, is_ringing
    while True:
        try:
            #print("OLED更新")
            oled.fill(0)
            t = utime.localtime(utime.time())  # 加上時區偏移 (+8 小時)
            time_str = "%04d-%02d-%02d %02d:%02d:%02d" % (t[0], t[1], t[2], t[3], t[4], t[5])
            draw_text(oled, time_str, 0, 0)
            
            # 顯示鬧鐘清單（最多三筆）
            if not alarms:
                draw_text(oled, "無鬧鐘", 0, 16)
            else:
                #print(alarms)
                for i, a in enumerate(alarms[:3]):
                    #mark = "✔" if a.get("enabled", True) else "✖"
                    txt = f"鬧鐘 ：{a['m']:02d}/{a['d']:02d} {a['h']:02d}:{a['min']:02d}"
                    draw_text(oled, txt, 0, 16 + i * 12)

            # 若正在響鈴
            if is_ringing:
                draw_text(oled, "RINGING!", 0, 56)

            oled.show()
            await asyncio.sleep(1)

        except Exception as e:
            print("⚠️ OLED 更新錯誤:", e)
            await asyncio.sleep(2)

async def alarm_task():
    global is_ringing

    last_triggered = set()  # ✅ 記錄已觸發的鬧鐘（防止重複響）
    print("🕒 鬧鐘監聽啟動")

    while True:
        t = utime.localtime()
        now = (t[0], t[1], t[2], t[3], t[4])  # (年,月,日,時,分)

        # 檢查每一組鬧鐘
        for i, a in enumerate(alarms):
            if not a.get("enabled", True):
                continue  # 跳過停用的鬧鐘

            alarm_time = (a["y"], a["m"], a["d"], a["h"], a["min"])
            if alarm_time == now and i not in last_triggered:
                print(f"🔔 鬧鐘 {i+1} 觸發！ {alarm_time}")
                last_triggered.add(i)

                # ✅ 使用非阻塞任務播放音樂
                asyncio.create_task(ring_task())

        await asyncio.sleep(1)

# ----------------------------
# 🚀 主程式入口
# ----------------------------
async def main():
    ip = wifi_auto("CHT1781", "87437143")
    print("ESP32 智慧鬧鐘啟動中...")
    await asyncio.gather(
        app.start(80),
        oled_task(),
        alarm_task()
    )

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()

