
# 🕓 ESP32 智慧鬧鐘系統

本專案實作一個 ESP32-S2 控制的智慧鬧鐘系統，結合 OLED 顯示、網頁控制、非同步播放音樂等功能，透過前後端協作實現遠端鬧鐘管理。

## 📦 專案功能總覽

- 🖥 前端網頁控制面板（HTML + JS）
- 📡 ESP32 Web Server（MicroPython）
- 🔊 支援多首鬧鐘音樂選擇
- ⏰ 多組鬧鐘設定/啟用/刪除
- 📺 OLED 實時顯示時間與鬧鐘
- 🧠 非同步音樂播放（uasyncio）

---

## 🔧 軟體架構

### 前端（Web UI）
- 使用者透過手機/電腦進入控制面板
- 可進行：
  - 查看目前時間
  - 設定鬧鐘時間、選擇鈴聲
  - 測試鈴聲
  - 停止鈴聲
  - 重置所有鬧鐘

### 後端（ESP32 with MicroPython）
- 使用 aiot_tools 提供 WebApp 框架
- 提供以下 API：

| API 路徑 | 方法 | 功能 |
|---------|------|------|
| `/api/time` | GET | 回傳目前時間字串 |
| `/api/alarms` | GET | 取得所有鬧鐘資料 |
| `/api/alarms` | POST | 新增/切換鬧鐘 |
| `/api/alarms` | DELETE | 刪除單筆或全部鬧鐘 |
| `/api/ring/test` | POST | 測試播放音樂 |
| `/api/ring/stop` | POST | 停止播放音樂 |

- 音樂透過 PWM 控制喇叭播放
- OLED 實時更新時間與鬧鐘狀態
- 鬧鐘觸發後會播放對應音樂

---

## 🔌 硬體架構

| 元件 | 說明 |
|------|------|
| ESP32-S2 Mini | 主控制板 |
| OLED 螢幕 (I2C) | 顯示時間與鬧鐘列表 |
| 被動蜂鳴器 | 透過 PWM 播放旋律 |
| Wi-Fi | 提供 Web API 控制介面 |

接腳範例：
- OLED：`SCL=38`、`SDA=40`
- Speaker：接 `Pin(14)`

---

## 🚀 使用方式

### 1. 設備與檔案準備
- 將 MicroPython 燒錄至 ESP32
- 上傳以下檔案至板子：
  - `hw3_clock_v2.py`
  - `hw3_clock_v3.html`
  - `lib/` 目錄（包含字型與 SSD1306 驅動）
  - `aiot_tools.py`（自訂 WebApp 工具）

### 2. 執行主程式
```python
import hw3_clock_v2
```

### 3. 開啟瀏覽器進入控制面板
連線至 ESP32 顯示的 IP，例如：http://192.168.4.1

### 4. 操作功能
- 新增鬧鐘，選擇時間與音樂
- 停用/啟用特定鬧鐘
- 測試播放與停止鈴聲

---

## 🎵 支援的音樂

- `NOTES_STAR`：小星星
- `NOTES_SKYCASTLE`：天空之城
- `NOTES_HAPPYBIRTHDAY`：生日快樂

---

## 🧠 備註與限制

- 鬧鐘使用非同步 `uasyncio` 偵測時間，每秒輪詢比對
- 喇叭為 PWM 被動蜂鳴器（非 MP3）
- 鬧鐘播放時不能同時播放第二首
- 自動記憶鬧鐘設定（存於 `alarms.json`）

---

## 📅 最後更新

2025-10-28