from umqtt.simple import MQTTClient
import network, time

# ========= WiFi =========
SSID = "CHT1781"
PASSWORD = "87437143"

# ========= MQTT =========
BROKER = "broker.emqx.io"   # ⚠️ 改成 EMQX IP
PORT = 1883
CLIENT_ID = "esp32_test_01"
TOPIC = b"test/component"

# WiFi connect
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)
while not wlan.isconnected():
    time.sleep(0.5)

print("WiFi success connected:", wlan.ifconfig())

# MQTT connect
client = MQTTClient(
    client_id=CLIENT_ID,
    server=BROKER,
    port=PORT,
    keepalive=60
)
client.connect()
print("MQTT connected")

# Publish loop
while True:
    msg = "alive_time={}".format(time.ticks_ms())
    client.publish(TOPIC, msg)
    print("Publish:", msg)
    time.sleep(5)
