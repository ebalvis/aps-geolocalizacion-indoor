# -*- coding: utf-8 -*-
"""
m5stick_skeleton.py — Esqueleto del cliente M5StickC Plus 2 para la práctica final APS.

Plataforma: MicroPython moderno sobre M5StickC Plus 2.
Módulos externos: ENV III Unit (SHT30 + QMP6988) conectado al puerto Grove.

Vuestra tarea es completar los 8 TODOs marcados con "# TODO <N>:".
No modifiquéis:
  - las firmas de las funciones ya definidas
  - el formato del JSON enviado al servidor
  - la estructura del JSON que recibís como respuesta

Los TODO 1 a 7 son la versión 1: el dispositivo mide, publica y muestra lo que le
devuelve el servidor. Con ellos el sistema ya localiza por WiFi, y la IMU actúa
como filtro temporal —acumular medidas cuando se está quieto, descartarlas cuando
se anda—, que es lo que se describe en la comunicación de EDUTRENDS 2026.

El TODO 8 es la VERSIÓN 2 y es de otra naturaleza: convierte la IMU en sensor de
POSICIÓN. Detecta pasos, integra el rumbo con el giróscopo y estima el
desplazamiento (Δx, Δy) que viaja en el bloque "imu_pdr". Especificación:

  · detección de pasos por umbral adaptativo sobre la magnitud del acelerómetro,
    con periodo refractario para no contar dobles;
  · longitud de zancada dependiente de la frecuencia de paso, calibrada por
    usuario sobre un recorrido de longitud conocida;
  · rumbo por integración del giróscopo con corrección de deriva;
  · remuestreo a intervalo uniforme ANTES de filtrar: el ESP32 no entrega las
    muestras a periodo constante, y hacerlo sobre el eje de tiempos crudo mete un
    error que se confunde con deriva del sensor.

Detalle en "Parte 4 - Navegacion inercial PDR" del enunciado y en el CHANGELOG
del repositorio. Mientras no se implemente, el bloque "imu_pdr" viaja con ceros y
el resto del sistema funciona igual: el servidor ignora una predicción nula.

Flujo del programa (no lo cambiéis):
  setup() -> loop infinito: leer sensores -> construir JSON -> publicar ->
             esperar respuesta muestreando el PDR a ~50 Hz -> mostrar -> repetir

Autor: Eduardo Balvís — APS, Grado en IA, UVigo, curso 2025/2026.
"""

import M5
from M5 import *
from machine import I2C, Pin
import network
import ujson
import utime
import math

# umqtt.robust hace reconexión automática si se pierde el broker
from umqtt.robust import MQTTClient


# =========================================================================
# TODO 1 — CONFIGURACIÓN
# =========================================================================
# Rellenad con VUESTROS valores. Los del broker os los da el profesor en
# Moovi (sección 6.3 del enunciado). El EQUIPO es el identificador que os
# han asignado (e01, e02, ...).
#
# NO subáis este fichero con vuestras credenciales a ningún repositorio ni
# lo compartáis fuera del equipo. Si lo entregáis, dejad estos valores como
# están ahora, sin rellenar.

WIFI_SSID     = "___WIFI_SSID___"        # red del aula o compartida del móvil
WIFI_PASSWORD = "___WIFI_PASSWORD___"

MQTT_HOST     = "___MQTT_HOST___"        # p.ej. xxxxxxxx.s1.eu.hivemq.cloud
MQTT_PORT     = 8883                     # TLS obligatorio
MQTT_USER     = "___MQTT_USER___"
MQTT_PASSWORD = "___MQTT_PASSWORD___"
MQTT_SSL      = True

EQUIPO        = "___EQUIPO___"           # p.ej. "e01" — el asignado en Moovi

# Umbral de potencia por debajo del cual una red no se tiene en cuenta. Es el
# mismo en las tres piezas del sistema —registrador, cliente y servidor— y el
# que exige el criterio 1 de la evaluación: si aquí se sube y en el servidor
# no, cada uno trabaja con un conjunto distinto de antenas y las métricas
# dejan de ser comparables entre equipos.
RSSI_MIN      = -90                      # dBm

# Topics derivados (NO modificar la estructura). Son los mismos que usan el
# servidor, el simulador y el visualizador 3D: si los cambias aquí y no allí,
# la cadena se rompe sin dar ningún error.
TOPIC_BASE    = "indoor_geolocation/{}/location".format(EQUIPO)
TOPIC_DATA    = TOPIC_BASE + "/data"
TOPIC_RESULT  = TOPIC_BASE + "/result"

# Periodo de publicación (segundos). No bajar de 3s para no saturar el broker
PERIODO_S     = 3


# =========================================================================
# Estado global
# =========================================================================
mqtt_client    = None
i2c            = None
mag_buffer     = []            # ventana móvil de aceleración para suavizar el IMU
ultimo_result  = None          # último JSON recibido del servidor
imu_sensor     = None          # instancia IMU (se crea una vez, la comparten TODO 3 y 8)

# ── Estado PDR (navegación inercial — TODO 8) ─────────────────────────────
# Parámetros de detección de paso (ajustables tras probar caminando).
STEP_LEN_DEFAULT = 0.65        # m  — longitud de paso por defecto
STEP_THRESH      = 1.18        # g  — umbral de PICO de |aceleración| para iniciar paso
STEP_HYST        = 0.95        # g  — umbral de BAJADA (histéresis) para cerrar el paso
MIN_STEP_MS      = 250         # ms — intervalo mínimo entre pasos (máx ~4 pasos/s)

# Estado acumulado del PDR. dx/dy/steps se resetean en cada envío; heading NO.
pdr = {
    "heading":      0.0,       # rad — rumbo acumulado (relativo al arranque)
    "dx":           0.0,       # m   — desplazamiento acumulado en X desde el último envío
    "dy":           0.0,       # m   — desplazamiento acumulado en Y
    "steps":        0,         # nº de pasos desde el último envío
    "in_peak":      False,     # ¿estamos dentro de un pico de aceleración?
    "last_step_ms": 0,         # ticks del último paso válido
    "last_ms":      0,         # ticks de la última muestra (para Δt del giróscopo)
    "step_len":     STEP_LEN_DEFAULT,
}

# Direcciones I2C del módulo ENV III sobre bus Grove (GPIO 32 SDA, GPIO 33 SCL)
I2C_BUS_GROVE  = 1
I2C_SDA        = 32
I2C_SCL        = 33
ADDR_QMP6988   = 0x70          # barómetro (presión)
ADDR_SHT30     = 0x44          # temperatura + humedad (no la usamos)
ADDR_MPU6886   = 0x68          # IMU integrado del M5Stick


# =========================================================================
# TODO 2 — LEER PRESIÓN DEL ENV III (QMP6988)
# =========================================================================
# Leer la presión barométrica en hPa del sensor QMP6988 por I2C.
# Devuelve un float en hPa, o None si hay error.
#
# Pista para Plus 2: el driver env3 puede importarse así:
#
#     import unit
#     env3 = unit.get(unit.ENV3, unit.PORTA)   # Grove = PORTA
#     pressure_hpa = env3.pressure / 100.0      # el driver devuelve Pa
#
# Si el módulo 'unit' no está disponible, leed los registros QMP6988 a mano
# (hoja de datos QMP6988, registros 0xF7-0xFC). Preguntad en el foro.

def leer_presion_hpa():
    # TODO 2: implementar
    return 1013.25  # valor por defecto mientras no lo implementéis


# =========================================================================
# TODO 3 — LEER IMU MPU6886 Y CLASIFICAR ESTADO DE MOVIMIENTO
# =========================================================================
# Leer la aceleración 3D del MPU6886 integrado y clasificar el estado
# en "quieto" / "moviendo" / "rapido" según la magnitud de aceleración.
# Sección 6.8 del enunciado describe el algoritmo exacto.
#
# En MicroPython moderno (Plus 2):
#
#     from imu import IMU
#     imu_sensor = IMU()
#     ax, ay, az = imu_sensor.acceleration   # valores en g (1 g ≈ 9.81 m/s²)
#
# La magnitud en reposo es ~1 g (gravedad), por eso se resta 1.0:
#     mag = sqrt(ax**2 + ay**2 + az**2) - 1.0

def leer_estado_imu():
    global mag_buffer

    # TODO 3.a: leer aceleración ax, ay, az del IMU y calcular:
    #           mag = sqrt(ax^2 + ay^2 + az^2) - 1.0   (unidades: g)
    mag = 0.0  # <-- sustituir por la lectura real

    # TODO 3.b: suavizar con ventana móvil de 10 muestras.
    mag_buffer.append(abs(mag))
    if len(mag_buffer) > 10:
        mag_buffer.pop(0)
    mag_promedio = sum(mag_buffer) / len(mag_buffer)

    # TODO 3.c: clasificar. Ajustad los umbrales si es necesario tras probar.
    if mag_promedio < 0.3:
        return "quieto"
    elif mag_promedio < 1.5:
        return "moviendo"
    else:
        return "rapido"


# =========================================================================
# TODO 8 — PDR: DESPLAZAMIENTO CON GIRÓSCOPO + ACELERÓMETRO
# =========================================================================
# Navegación por estima peatonal. Se llama a ~50 Hz (en la espera del loop).
# En cada muestra:
#   - integra el rumbo con el giróscopo Z:   heading += gz(rad/s) * Δt
#   - detecta un PASO como un pico de |aceleración| con histéresis
#   - por cada paso acumula:  dx += L*sin(heading),  dy += L*cos(heading)
#
# En MicroPython moderno (Plus 2):
#     from imu import IMU
#     imu = IMU()
#     ax, ay, az = imu.acceleration   # g
#     gx, gy, gz = imu.gyro           # grados/s  (¡convertir a rad/s!)

def _get_imu():
    """Devuelve la instancia IMU, creándola una sola vez."""
    global imu_sensor
    if imu_sensor is None:
        from imu import IMU
        imu_sensor = IMU()
    return imu_sensor


def muestrear_pdr():
    """Lee el IMU una vez y actualiza el estado PDR. Llamar a alta frecuencia."""
    global pdr
    imu = _get_imu()
    now = utime.ticks_ms()
    dt  = utime.ticks_diff(now, pdr["last_ms"]) / 1000.0  # s
    pdr["last_ms"] = now
    if dt <= 0 or dt > 0.5:      # primera muestra o hueco grande: solo marcar tiempo
        return

    # TODO 8.a: leer aceleración (g) y giróscopo (grados/s)
    #   ax, ay, az = imu.acceleration
    #   gx, gy, gz = imu.gyro
    ax = ay = az = 0.0
    gx = gy = gz = 0.0

    # TODO 8.b: integrar el rumbo. gz viene en grados/s -> pasar a rad/s.
    #   pdr["heading"] += (gz * pi/180.0) * dt
    # (dejadlo comentado hasta leer gz de verdad)

    # TODO 8.c: magnitud de aceleración y detección de paso por histéresis.
    mag = math.sqrt(ax * ax + ay * ay + az * az)   # g  (~1 en reposo)
    dt_ms = utime.ticks_diff(now, pdr["last_step_ms"])
    if not pdr["in_peak"]:
        # Buscar el inicio de un paso: pico por encima del umbral
        if mag > STEP_THRESH and dt_ms > MIN_STEP_MS:
            pdr["in_peak"] = True
    else:
        # Esperar a que baje (fin del paso)
        if mag < STEP_HYST:
            pdr["in_peak"] = False
            # TODO 8.d: PASO VÁLIDO -> contar y acumular desplazamiento
            #   pdr["steps"] += 1
            #   pdr["dx"] += pdr["step_len"] * math.sin(pdr["heading"])
            #   pdr["dy"] += pdr["step_len"] * math.cos(pdr["heading"])
            #   pdr["last_step_ms"] = now
            pass


def obtener_pdr_reset():
    """Devuelve el desplazamiento acumulado y resetea dx/dy/steps (heading NO)."""
    global pdr
    d = {
        "dx_m":    round(pdr["dx"], 3),
        "dy_m":    round(pdr["dy"], 3),
        "steps":   pdr["steps"],
        "heading": round(pdr["heading"] % (2 * math.pi), 4),
    }
    pdr["dx"] = 0.0
    pdr["dy"] = 0.0
    pdr["steps"] = 0
    return d


# =========================================================================
# Escaneo WiFi (esto ya está hecho, no hace falta tocarlo)
# =========================================================================
def escanear_wifi(sta_if):
    """Devuelve lista de dicts [{'BSSID': 'aa:bb:...', 'potencia': -65}, ...]"""
    try:
        redes = sta_if.scan()
    except Exception as e:
        print("scan WiFi error:", e)
        return []

    resultado = []
    for red in redes:
        # red = (ssid, bssid_bytes, channel, rssi, authmode, hidden)
        bssid_bytes = red[1]
        bssid_str = ":".join("{:02x}".format(b) for b in bssid_bytes)
        rssi = red[3]
        if rssi >= RSSI_MIN:
            resultado.append({"BSSID": bssid_str, "potencia": rssi})
    return resultado


# =========================================================================
# TODO 4 — CONSTRUIR EL JSON A PUBLICAR
# =========================================================================
# Montar el dict con todos los campos requeridos por el servidor.
# El formato exacto está en la sección 6.6 del enunciado.
# Devolver un dict Python (se serializa con ujson.dumps al publicar).

def construir_mensaje_data(presion_hpa, estado_imu, wifi_scans, imu_pdr):
    # TODO 4: rellenar el dict con device, timestamp, presion, estado_imu,
    #         wifi_scans e imu_pdr (bloque PDR con dx_m, dy_m, steps, heading).
    mensaje = {
        "device":     EQUIPO,
        "timestamp":  utime.ticks_ms(),
        # "presion":    ...
        # "estado_imu": ...
        # "wifi_scans": ...
        "imu_pdr":    imu_pdr,   # Δx, Δy, pasos y rumbo del PDR (TODO 8)
    }
    return mensaje


# =========================================================================
# TODO 5 — PUBLICAR EN EL BROKER
# =========================================================================
# Usar mqtt_client.publish(topic, payload). El payload debe ser bytes
# o string; usad ujson.dumps para serializar el dict.

def publicar_mensaje(mensaje_dict):
    global mqtt_client
    if mqtt_client is None:
        return
    try:
        payload = ujson.dumps(mensaje_dict)
        # TODO 5: publicar payload en TOPIC_DATA
        # mqtt_client.publish(...)
        pass
    except Exception as e:
        print("publish error:", e)


# =========================================================================
# TODO 6 — CALLBACK MQTT: PARSEAR LA RESPUESTA DEL SERVIDOR
# =========================================================================
# Cuando el servidor publica en TOPIC_RESULT, umqtt nos lo entrega aquí.
# Hay que deserializar el JSON y guardarlo en 'ultimo_result' para que
# display_position lo pinte en pantalla.

def on_mqtt_message(topic, msg):
    global ultimo_result
    # TODO 6.a: decodificar msg (bytes) a string y parsearlo con ujson.loads
    # TODO 6.b: guardar el dict resultante en la variable global ultimo_result
    pass


# =========================================================================
# TODO 7 — DISPLAY: MOSTRAR LA POSICIÓN EN LA PANTALLA
# =========================================================================
# Usar la API M5.Lcd del MicroPython moderno (Plus 2).
#
# Funciones útiles:
#   M5.Lcd.fillScreen(color)          → limpiar pantalla (negro = 0x000000)
#   M5.Lcd.setTextColor(fg, bg)       → color texto  (ej. 0xFFFFFF, 0x000000)
#   M5.Lcd.setTextSize(n)             → tamaño: 1=pequeño, 2=mediano, 3=grande
#   M5.Lcd.drawString("texto", x, y)  → dibujar texto en (x, y)
#
# La pantalla es 240×135 px en horizontal. Colores útiles:
#   negro=0x000000  blanco=0xFFFFFF  verde=0x00FF00
#   amarillo=0xFFFF00  rojo=0xFF0000  naranja=0xFF8000
#
# Requisitos (sección 6.11 del enunciado):
#   - Mostrar nivel (planta), zona, x, y
#   - Estado con color diferente:
#       ok               → verde   (0x00FF00)
#       en_movimiento    → amarillo (0xFFFF00)
#       movimiento_rapido → rojo   (0xFF0000)
#   - Si hay 'aviso' (ej. "discrepancia_baro:..."), mostrarlo en pequeño

def display_position(x, y, planta, zona, estado, aviso=None):
    # TODO 7: implementar
    M5.Lcd.fillScreen(0x000000)
    M5.Lcd.setTextColor(0xFFFFFF, 0x000000)
    M5.Lcd.setTextSize(1)
    M5.Lcd.drawString("TODO 7: display", 10, 10)


# =========================================================================
# Setup (ya está hecho, no hay que tocarlo)
# =========================================================================
def setup():
    global mqtt_client, i2c

    # Inicialización obligatoria en Plus 2
    M5.begin()
    M5.Lcd.setRotation(3)   # landscape: USB-C a la derecha (240×135 px)

    # Pantalla inicial
    M5.Lcd.fillScreen(0x000000)
    M5.Lcd.setTextColor(0xFFFFFF, 0x000000)
    M5.Lcd.setTextSize(1)
    M5.Lcd.drawString("Arrancando...", 10, 10)

    # Aviso si el TODO 1 sigue sin rellenar. Sin esto, el fallo aparece mucho
    # despues y como un error de red, que despista.
    faltan = [n for n, v in (("WIFI_SSID", WIFI_SSID),
                             ("WIFI_PASSWORD", WIFI_PASSWORD),
                             ("MQTT_HOST", MQTT_HOST),
                             ("MQTT_USER", MQTT_USER),
                             ("MQTT_PASSWORD", MQTT_PASSWORD),
                             ("EQUIPO", EQUIPO)) if v.startswith("___")]
    if faltan:
        M5.Lcd.fillScreen(0x000000)
        M5.Lcd.setTextColor(0xFF5555, 0x000000)
        M5.Lcd.drawString("Falta el TODO 1", 10, 10)
        M5.Lcd.setTextColor(0xFFFFFF, 0x000000)
        M5.Lcd.drawString("Sin rellenar:", 10, 32)
        y = 48
        for nombre in faltan[:5]:
            M5.Lcd.drawString("- " + nombre, 10, y)
            y += 14
        print("Falta rellenar el TODO 1 de configuracion:", ", ".join(faltan))
        raise SystemExit

    # WiFi
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    if not sta_if.isconnected():
        M5.Lcd.drawString("WiFi connect...", 10, 30)
        sta_if.connect(WIFI_SSID, WIFI_PASSWORD)
        # Esperar conexión (máx 15 s)
        for _ in range(30):
            if sta_if.isconnected():
                break
            utime.sleep_ms(500)
    if sta_if.isconnected():
        M5.Lcd.drawString("WiFi OK " + sta_if.ifconfig()[0], 10, 50)
    else:
        M5.Lcd.drawString("WiFi FAIL", 10, 50)

    # I2C para los sensores ENV III e IMU
    i2c = I2C(I2C_BUS_GROVE, scl=Pin(I2C_SCL), sda=Pin(I2C_SDA), freq=400000)

    # MQTT
    client_id = "m5stick_" + EQUIPO
    mqtt_client = MQTTClient(
        client_id=client_id,
        server=MQTT_HOST,
        port=MQTT_PORT,
        user=MQTT_USER,
        password=MQTT_PASSWORD,
        ssl=MQTT_SSL,
        keepalive=60
    )
    mqtt_client.set_callback(on_mqtt_message)
    try:
        mqtt_client.connect()
        mqtt_client.subscribe(TOPIC_RESULT.encode())
        M5.Lcd.drawString("MQTT OK", 10, 70)
    except Exception as e:
        M5.Lcd.drawString("MQTT FAIL", 10, 70)
        print("MQTT connect error:", e)

    utime.sleep(1)
    return sta_if


# =========================================================================
# Loop principal (ya está hecho)
# =========================================================================
def loop(sta_if):
    while True:
        M5.update()  # imprescindible: procesa botones y hardware M5

        # 1. Procesar mensajes MQTT pendientes (no bloqueante)
        try:
            mqtt_client.check_msg()
        except Exception as e:
            print("check_msg error:", e)

        # 2. Leer sensores
        presion = leer_presion_hpa()
        estado  = leer_estado_imu()
        scans   = escanear_wifi(sta_if)
        imu_pdr = obtener_pdr_reset()   # Δx, Δy acumulados desde el último envío

        # 3. Construir y publicar mensaje
        mensaje = construir_mensaje_data(presion, estado, scans, imu_pdr)
        publicar_mensaje(mensaje)

        # 4. Mostrar en pantalla el último resultado que recibimos
        if ultimo_result is not None:
            display_position(
                ultimo_result.get("x"),
                ultimo_result.get("y"),
                ultimo_result.get("nivel"),
                ultimo_result.get("zona_estimada"),
                ultimo_result.get("estado"),
                ultimo_result.get("aviso")
            )

        # 5. Esperar PERIODO_S segundos MUESTREANDO EL PDR a ~50 Hz
        #    (así el desplazamiento se acumula entre envíos WiFi) y sin dejar
        #    de procesar los mensajes MQTT entrantes.
        t_fin = utime.ticks_add(utime.ticks_ms(), PERIODO_S * 1000)
        while utime.ticks_diff(t_fin, utime.ticks_ms()) > 0:
            muestrear_pdr()                 # TODO 8: acumula pasos y Δx, Δy
            try:
                mqtt_client.check_msg()
            except Exception:
                pass
            utime.sleep_ms(20)              # ~50 Hz


# =========================================================================
# Punto de entrada
# =========================================================================
if __name__ == "__main__":
    sta = setup()
    loop(sta)
