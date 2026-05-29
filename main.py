import time
import dht
import network
import ssd1306
from machine import Pin, ADC, I2C
from umqtt.simple import MQTTClient

#   Sensores  
sensor_dht  = dht.DHT22(Pin(4))
ldr         = ADC(Pin(34)); ldr.atten(ADC.ATTN_11DB)
mq2         = ADC(Pin(35)); mq2.atten(ADC.ATTN_11DB)
mq2_digital = Pin(14, Pin.IN)
pir         = Pin(27, Pin.IN)

#   Atuadores                       
ac          = Pin(26, Pin.OUT)
luz_quintal = Pin(25, Pin.OUT)
alerta_gas  = Pin(33, Pin.OUT)
luz_garagem = Pin(32, Pin.OUT)

#   OLED    
i2c  = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

#   MQTT tópicos                    ─
BASE          = "home/julio"
T_TEMP        = BASE + "/sensor/temperature"
T_UMID        = BASE + "/sensor/humidity"
T_LDR         = BASE + "/sensor/ldr"
T_GAS         = BASE + "/sensor/gas"
T_PIR         = BASE + "/sensor/motion"
T_CMD_AC      = BASE + "/cmd/ac"
T_CMD_QUINTAL = BASE + "/cmd/quintal"
T_CMD_GAS     = BASE + "/cmd/gas_alert"
T_CMD_GARAGEM = BASE + "/cmd/garagem"

#   Limiares  
TEMP_MAX   = 28
LDR_NOITE  = 1000
MQ2_LIMITE = 2000

     
estado = {"ac": 0, "quintal": 0, "gas": 0, "garagem": 0}

#   Callback MQTT     
def on_message(topic, msg):
    t   = topic.decode()
    val = 1 if msg.decode().upper() == "ON" else 0

    if t == T_CMD_AC:
        ac.value(val); estado["ac"]= val
    elif t == T_CMD_QUINTAL:
        luz_quintal.value(val); estado["quintal"] = val
    elif t == T_CMD_GAS:
        alerta_gas.value(val);  estado["gas"] = val
    elif t == T_CMD_GARAGEM:
        luz_garagem.value(val); estado["garagem"] = val

    print(f"[MQTT] {t.split('/')[-1]} - {'ON' if val else 'OFF'}")

#   WiFi    
def conectar_wifi():
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    wifi.connect("Wokwi-GUEST", "")
    for _ in range(20):
        if wifi.isconnected():
            print(f"WiFi OK: {wifi.ifconfig()[0]}")
            return True
        time.sleep(0.5)
    print("WiFi: falhou")
    return False

  
def conectar_mqtt():
    
    c = MQTTClient("esp32_pfc_julio_2026", "broker.hivemq.com", port=1883, keepalive=60)
    c.set_callback(on_message)
    c.connect()
    for t in [T_CMD_AC, T_CMD_QUINTAL, T_CMD_GAS, T_CMD_GARAGEM]:
        c.subscribe(t.encode())
    print("MQTT OK - HiveMQ Nuvem")
    return c

#   OLED    
def atualizar_oled(temp, umid, ldr_val, gas_val, mov):
    oled.fill(0)
    oled.text("Casa Inteligente", 0, 0)
    oled.hline(0, 10, 128, 1)
    oled.text(f"T:{temp:.1f}C H:{umid:.0f}%", 0, 14)
    oled.text(f"LDR:{ldr_val:<5}", 0, 24)
    gas_str = "ALERTA!" if gas_val > MQ2_LIMITE else f"{gas_val:<5}"
    oled.text(f"Gas:{gas_str}", 0, 34)
    oled.text(f"PIR:{'SIM' if mov else 'NAO'}", 0, 44)
    oled.hline(0, 54, 128, 1)
    s = lambda k: "1" if estado[k] else "0"
    oled.text(f"AC:{s('ac')} QT:{s('quintal')} GS:{s('gas')} GR:{s('garagem')}", 0, 56)
    oled.show()

def pub(topic, msg):
    global mqtt
    if mqtt is None:
        return
    try:
        t = topic.encode() if isinstance(topic, str) else topic
        m = msg.encode()   if isinstance(msg,   str) else msg
        mqtt.publish(t, m)
    except Exception as e:
        print(f"[MQTT] falhou: {e}")
        mqtt = None

#   Boot
oled.fill(0)
oled.text("Iniciando...", 0, 28)
oled.show()

mqtt = None
if conectar_wifi():
    try:
        mqtt = conectar_mqtt()
    except Exception as e:
        print(f"MQTT erro: {e}")
        oled.fill(0)
        oled.text("Sem MQTT", 20, 24)
        oled.text("Sensores OK", 12, 36)
        oled.show()
        time.sleep(2)

print("  Automação Residencial  ")


while True:
    if mqtt:
        try:
            mqtt.check_msg()
        except Exception as e:
            print(f"[MQTT] check_msg: {e}")
            mqtt = None

    # DHT22 
    try:
        sensor_dht.measure()
        temp = sensor_dht.temperature()
        umid = sensor_dht.humidity()
    except:
        temp, umid = 0.0, 0.0

    if temp > TEMP_MAX:
        ac.value(1); estado["ac"] = 1
    else:
        ac.value(0); estado["ac"] = 0

    pub(T_TEMP, f"{temp:.1f}")
    pub(T_UMID, f"{umid:.1f}")

    # LDR 
    ldr_val = ldr.read()
    if ldr_val < LDR_NOITE:
        luz_quintal.value(1); estado["quintal"] = 1
    else:
        luz_quintal.value(0); estado["quintal"] = 0
    pub(T_LDR, str(ldr_val))

    # MQ2 - Alerta gás
    gas_val = mq2.read()
    if gas_val > MQ2_LIMITE or mq2_digital.value() == 0:
        alerta_gas.value(1); estado["gas"] = 1
        pub(T_GAS, b"ALERTA")
        print(f"[MQ2] !!! VAZAMENTO: {gas_val}")
    else:
        alerta_gas.value(0); estado["gas"] = 0
        pub(T_GAS, str(gas_val))

    # PIR
    mov = pir.value()
    luz_garagem.value(mov); estado["garagem"] = mov
    pub(T_PIR, b"ON" if mov else b"OFF")

    # OLED
    atualizar_oled(temp, umid, ldr_val, gas_val, mov)

    print(f"T:{temp:.1f} H:{umid:.0f} LDR:{ldr_val} Gas:{gas_val} PIR:{mov}")
    print(f"AC:{estado['ac']} QT:{estado['quintal']} GS:{estado['gas']} GR:{estado['garagem']}")
    print("-" * 40)
    time.sleep(10)