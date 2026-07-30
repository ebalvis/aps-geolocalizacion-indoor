# Programar el M5StickC en MicroPython (UIFlow 2.0)

Guía práctica para empezar desde cero con el M5StickC Plus 2 y el firmware
UIFlow 2.0. Para la referencia completa de la API, ver `Manual_UIFlow2_Completo.pdf`
en esta misma carpeta.

Los ejemplos usan `Widgets` y `M5.Lcd`, que son del MicroPython moderno del Plus 2. En
el Plus 1.1, con UIFlow 1.x, la pantalla se maneja con otra API (`lcd.font`, `lcd.print`)
y estos ejemplos no valen tal cual.

## 1. Preparar el dispositivo

1. Descarga e instala M5Burner (de M5Stack).
2. Conecta el M5StickC por USB. En M5Burner, busca el firmware UIFlow 2.0 para
   StickC Plus y grábalo (Burn). Pon el modo en USB / MicroPython.
3. Comprueba el puerto serie (COMx en Windows, /dev/ttyUSBx o /dev/ttyACMx en
   Linux o macOS).

## 2. Cargar y ejecutar código

Cualquiera de estas opciones vale:

- Thonny: elige el intérprete MicroPython (ESP32), abre el `.py`, y ejecútalo con
  F5. Para dejarlo permanente, guárdalo en el dispositivo como `main.py`.
- IDE web de UIFlow: modo Python, pega el código y ejecuta.
- Línea de comandos con `ampy`:
  ```bash
  pip install adafruit-ampy
  ampy --port COM5 put wifi_logger.py main.py
  ```

El archivo `main.py` de la flash se ejecuta solo al encender. `boot.py` se ejecuta
antes; normalmente no hace falta tocarlo.

## 3. Estructura típica de un programa

```python
import M5
from M5 import *

def setup():
    M5.begin()
    Widgets.fillScreen(0x111111)
    global etiqueta
    etiqueta = Widgets.Label("Hola", 3, 30, 1.0, 0xFFFFFF, 0x111111, Widgets.FONTS.DejaVu18)

def loop():
    M5.update()               # imprescindible: refresca botones y sensores
    if BtnA.wasPressed():
        etiqueta.setText("Boton A")

if __name__ == "__main__":
    setup()
    while True:
        loop()
```

## 4. Pantalla

```python
titulo = Widgets.Title("Mi app", 3, 0xFFFFFF, 0x005B99, Widgets.FONTS.DejaVu18)
lbl = Widgets.Label("texto", x, y, escala, color, fondo, Widgets.FONTS.DejaVu12)
lbl.setText("nuevo texto")
lbl.setColor(0x00FF00, 0x111111)   # color de letra y de fondo
Widgets.fillScreen(0x111111)       # limpiar
```

Los colores son enteros `0xRRGGBB`. La pantalla es de 135×240 píxeles en vertical, que es
como arranca; el firmware de las prácticas la gira a horizontal con
`M5.Display.setRotation(1)` y pasa a ser de 240×135. Conviene tenerlo presente:
conviene no pasarse con el tamaño del texto.

## 5. Botones

```python
M5.update()             # llamar en cada vuelta del bucle
BtnA.wasPressed()       # pulsación corta (True una sola vez)
BtnA.wasHold()          # mantener pulsado
BtnB.wasPressed()
```

## 6. Sensores: IMU y ambiental

```python
acc = Imu.getAccel()    # (ax, ay, az) en g
gyro = Imu.getGyro()    # (gx, gy, gz) en grados por segundo

import math
mag = math.sqrt(acc[0]**2 + acc[1]**2 + acc[2]**2)   # ~1.0 en reposo
```

El ENV III (presión, en el puerto Grove) se lee así:

```python
from hardware import I2C, Pin
from unit import ENVUnit
i2c0 = I2C(0, scl=Pin(33), sda=Pin(32), freq=100000)
env3 = ENVUnit(i2c=i2c0, type=3)
presion = env3.read_pressure()   # hPa
```

## 7. WiFi

```python
import network

# Escanear (sin conectar):
sta = network.WLAN(network.STA_IF)
sta.active(True)
for red in sta.scan():
    ssid, bssid, canal, rssi, auth, oculta = red
    # bssid es bytes; conviértelo con ":".join("{:02x}".format(b) for b in bssid)

# Conectar a una red:
sta.connect("MiSSID", "MiPassword")
while not sta.isconnected():
    pass
print(sta.ifconfig()[0])   # dirección IP

# Crear un punto de acceso propio (el M5 es el router):
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid="Mi-M5", authmode=0)   # red abierta; IP 192.168.4.1
```

## 8. Ficheros en la flash

```python
with open("/flash/datos.csv", "w") as f:
    f.write("hola\n")

import os
os.stat("/flash/datos.csv")[6]   # tamaño en bytes
os.statvfs("/flash")             # espacio libre
os.remove("/flash/datos.csv")
```

## 9. MQTT

```python
from umqtt import MQTTClient
import ssl

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.verify_mode = ssl.CERT_NONE
cliente = MQTTClient("mi_id", "broker.host", port=8883,
                     user="usuario", password="clave", keepalive=60, ssl=ctx)
cliente.connect()
cliente.publish("mi/topic", "mensaje")

# Recibir:
def al_recibir(topic, msg):
    print(topic, msg)
cliente.set_callback(al_recibir)
cliente.subscribe("mi/topic")
cliente.check_msg()     # no bloqueante; llamar en el bucle
```

## 10. Tiempo y errores frecuentes

- Mide intervalos con `time.ticks_ms()` y `time.ticks_diff(ahora, antes)`, no con
  restas directas: el contador se reinicia y una resta normal daría negativos.
- Usa `"{}".format(x)` para dar formato. Según la versión del firmware, las
  f-strings pueden no estar disponibles.
- Llama a `gc.collect()` antes de operaciones que consumen memoria (un escaneo
  WiFi, una conexión TLS). La RAM del ESP32 es limitada.
- Si el programa se cuelga, un `Ctrl+C` en el REPL lo para; si no responde, el
  botón de reset del lateral reinicia el dispositivo.

## Para profundizar

- `Manual_UIFlow2_Completo.pdf` (esta carpeta): referencia completa de la API.
- Las prácticas B1 a B7 (`practicas/`) parten de aquí y van sumando sensores y
  técnicas paso a paso.
