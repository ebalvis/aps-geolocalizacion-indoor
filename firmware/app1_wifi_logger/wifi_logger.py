"""
App 1 - Registrador WiFi por puntos (herramienta completa del alumno)
====================================================================
Para M5StickC Plus 1.1 / Plus 2 con firmware UIFlow 2.0 (MicroPython).

Cada grabación es un PUNTO de referencia: te colocas en un punto, grabas unos
segundos de escaneos WiFi, y paras. El número de punto sube solo y se ve en
pantalla. Todos los puntos se acumulan en un mismo CSV (/flash/wifi_log.csv),
que después se descarga. Cada fila lleva el número de punto:

  punto, time_ns, seconds_elapsed, rssi_dbm, freq_mhz, capabilities, BSSID, SSID

Descarga (tres formas, desde el menú):
  - WiFi local        : el M5 se conecta a la red del aula y sirve una web.
  - Punto de acceso   : el M5 crea su propia red y sirve en http://192.168.4.1
  - USB por serie     : comando desde el PC (ver pantalla).

Controles (por FLANCO de pulsación, clic corto):
  Pantalla PARADO : A = grabar punto        B = menú de descarga
  Pantalla REC    : A = parar
  Menú            : A = cambiar opción       B = elegir
  Descargando     : B = salir
"""
import os
import gc
import time
import socket
import network
import binascii
import machine

import M5
from M5 import *

# ENV III opcional (presión). No es necesario para el registro WiFi.
try:
    from hardware import I2C, Pin
    from unit import ENVUnit
    _ENV_OK = True
except Exception:
    _ENV_OK = False


# ===================== CONFIGURACIÓN =====================
LOG_FILE      = "/flash/wifi_log.csv"
SCAN_INTERVAL = 3000     # ms entre escaneos durante la grabación
RSSI_MIN      = -90      # dBm; descarta redes por debajo de este nivel.
                         # Mismo umbral en todo el sistema: registrador,
                         # cliente y servidor. Ver docs/protocolo-mqtt.md.

# Para la opción "WiFi local": red del aula con salida a internet.
WIFI_SSID     = "TU_SSID_WIFI"
WIFI_PASS     = "TU_PASSWORD_WIFI"

AP_SSID_BASE  = "APS-Logger"   # el punto de acceso será APS-Logger-XXXX
AP_PASSWORD   = ""             # "" = red abierta
FLASH_MIN_KB  = 40
CABECERA      = "punto,time,seconds_elapsed,level,frequency,capabilities,BSSID,SSID"
# ========================================================


# --- estado ---
env3         = None
estado       = "idle"     # idle | rec | menu
log_file     = None
sample_count = 0
n_ultimo     = 0
punto        = 0          # número de punto de referencia (una grabación = un punto)
t_start      = 0
ultimo_scan  = 0
sta_scan     = None
menu_idx     = 0

OPCIONES = ["Volver", "WiFi local", "Punto de acceso", "USB por serie",
            "Borrar todo"]

# --- widgets ---
title0 = l1 = l2 = l3 = None


# ===================== WiFi =====================

_AUTH = {0: "[OPEN]", 1: "[WEP]", 2: "[WPA-PSK]", 3: "[WPA2-PSK]",
         4: "[WPA/WPA2]", 5: "[WPA2-EAP]", 6: "[WPA2/3]", 7: "[WPA3-SAE]"}


def canal_a_freq(ch):
    if 1 <= ch <= 14:
        return 2407 + ch * 5
    if 32 <= ch <= 177:
        return 5000 + ch * 5
    return 2412


def bssid_txt(b):
    return ":".join("{:02x}".format(x) for x in b)


def activar_scan():
    network.WLAN(network.AP_IF).active(False)
    sta = network.WLAN(network.STA_IF)
    if not sta.active():
        sta.active(True)
        time.sleep_ms(300)
    return sta


# ===================== FLASH =====================

def flash_libre_kb():
    try:
        s = os.statvfs("/flash")
        return (s[0] * s[3]) // 1024
    except Exception:
        return -1


def tam_archivo():
    try:
        return os.stat(LOG_FILE)[6]
    except Exception:
        return 0


def ultimo_punto_en_fichero():
    """Mayor número de punto ya guardado (para continuar la campaña tras reiniciar)."""
    p = 0
    try:
        with open(LOG_FILE) as f:
            f.readline()   # cabecera
            for linea in f:
                try:
                    v = int(linea.split(",")[0])
                    if v > p:
                        p = v
                except Exception:
                    pass
    except Exception:
        pass
    return p


# ===================== PANTALLA =====================

def limpiar():
    Widgets.fillScreen(0x111111)


def ui_idle():
    l1.setColor(0xFF6666, 0x111111)
    l1.setText("PARADO")
    l2.setColor(0xFFFFFF, 0x111111)
    l2.setText("Puntos grabados: {}".format(punto))
    l3.setText("A: grabar   B: descargar")


def ui_rec():
    l1.setColor(0x33DD33, 0x111111)
    l1.setText("REC  Punto {}".format(punto))
    l2.setColor(0xFFFFFF, 0x111111)
    l2.setText("{} APs / {} muestras".format(n_ultimo, sample_count))
    l3.setText("A: parar")


def ui_menu():
    l1.setColor(0xE1AD66, 0x111111)
    l1.setText("Descargar por:")
    l2.setColor(0xFFFFFF, 0x111111)
    l2.setText("> " + OPCIONES[menu_idx])
    l3.setText("A: cambiar   B: elegir")


def refrescar_ui():
    if estado == "idle":
        ui_idle()
    elif estado == "rec":
        ui_rec()
    elif estado == "menu":
        ui_menu()


# ===================== GRABACIÓN =====================

def iniciar():
    global estado, log_file, sample_count, n_ultimo, t_start, ultimo_scan, sta_scan, punto
    gc.collect()
    sta_scan = activar_scan()
    nuevo = tam_archivo() == 0
    log_file = open(LOG_FILE, "a")            # AÑADIR: acumula todos los puntos
    if nuevo:
        log_file.write(CABECERA + "\n")
    punto += 1                                # una grabación = el siguiente punto
    sample_count = 0
    n_ultimo = 0
    t_start = time.ticks_ms()
    ultimo_scan = time.ticks_ms() - SCAN_INTERVAL
    estado = "rec"


def parar():
    global estado, log_file
    if log_file:
        try:
            log_file.flush()
            log_file.close()
        except Exception:
            pass
        log_file = None
    estado = "idle"


def escanear():
    global sample_count, n_ultimo
    gc.collect()
    try:
        redes = sta_scan.scan()
    except Exception:
        return 0
    t_ns = time.ticks_ms() * 1000000
    seg = time.ticks_diff(time.ticks_ms(), t_start) / 1000.0
    n = 0
    for r in redes:
        rssi = int(r[3])
        if rssi < RSSI_MIN:
            continue
        ssid = r[0].decode("utf-8", "ignore") if r[0] else "(oculta)"
        log_file.write("{},{},{:.2f},{},{},{},{},{}\n".format(
            punto, t_ns, seg, rssi, canal_a_freq(int(r[2])),
            _AUTH.get(int(r[4]), "[?]"), bssid_txt(r[1]), ssid))
        n += 1
    log_file.flush()
    sample_count += n
    n_ultimo = n
    return n


def borrar_todo():
    global punto
    try:
        os.remove(LOG_FILE)
    except Exception:
        pass
    punto = 0


# ===================== SERVIDOR HTTP =====================

def _html():
    try:
        info = "{} KB".format(os.stat(LOG_FILE)[6] // 1024)
    except Exception:
        info = "sin archivo"
    return ("HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\n"
            "<!doctype html><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<body style='font-family:sans-serif;margin:24px;background:#f3f2f2'>"
            "<h2>Registrador WiFi (APS)</h2><p>Archivo: {}</p>"
            "<p><a href='/download' style='padding:14px 26px;border:1px solid "
            "#b68235;color:#7d5411;text-decoration:none'>Descargar wifi_log.csv</a></p>"
            "<p><a href='/delete' style='color:#a33'>Borrar todo</a></p></body>").format(info)


def servir_http(ip, etiqueta):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("", 80))
    srv.listen(1)
    srv.settimeout(0.2)

    l1.setColor(0x00AEEF, 0x111111)
    l1.setText("DESCARGA")
    l2.setText(etiqueta)
    l3.setText("http://" + ip + "  (B: salir)")

    while True:
        M5.update()
        if BtnB.wasPressed():
            break
        try:
            cl, _ = srv.accept()
        except OSError:
            continue
        try:
            req = cl.recv(1024).decode("utf-8", "ignore")
            if "GET /delete" in req:
                borrar_todo()
                cl.send("HTTP/1.1 302 Found\r\nLocation: /\r\n\r\n")
            elif "GET /download" in req or "wifi_log.csv" in req:
                try:
                    tam = os.stat(LOG_FILE)[6]
                except Exception:
                    cl.send("HTTP/1.1 404 Not Found\r\n\r\n")
                    cl.close()
                    continue
                cl.send("HTTP/1.1 200 OK\r\nContent-Type: text/csv\r\n"
                        "Content-Disposition: attachment; filename=\"wifi_log.csv\"\r\n"
                        "Content-Length: {}\r\n\r\n".format(tam))
                with open(LOG_FILE, "r") as f:
                    while True:
                        d = f.read(1024)
                        if not d:
                            break
                        cl.send(d)
            else:
                cl.send(_html())
        except Exception:
            pass
        finally:
            try:
                cl.close()
            except Exception:
                pass
    srv.close()


# ===================== OPCIONES DE DESCARGA =====================

def _mensaje(a, b, c):
    l1.setColor(0xFFFFFF, 0x111111)
    l1.setText(a)
    l2.setText(b)
    l3.setText(c)


def _esperar_b():
    while True:
        M5.update()
        if BtnB.wasPressed():
            return
        time.sleep_ms(20)


def descargar_wifi_local():
    if WIFI_SSID.startswith("TU_"):
        _mensaje("Configura WIFI_SSID", "y WIFI_PASS en el codigo", "B: volver")
        _esperar_b()
        return
    network.WLAN(network.AP_IF).active(False)
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    if not sta.isconnected():
        _mensaje("Conectando WiFi", WIFI_SSID, "")
        sta.connect(WIFI_SSID, WIFI_PASS)
        t = 0
        while not sta.isconnected():
            time.sleep_ms(400)
            t += 1
            l3.setText("{}s...".format(t * 4 // 10))
            if t > 30:
                _mensaje("WiFi fallo", "", "B: volver")
                _esperar_b()
                sta.active(False)
                return
    servir_http(sta.ifconfig()[0], "WiFi: " + WIFI_SSID)
    try:
        sta.disconnect()
    except Exception:
        pass


def descargar_ap():
    network.WLAN(network.STA_IF).active(False)
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    uid = binascii.hexlify(machine.unique_id()).decode()[-4:]
    ssid = "{}-{}".format(AP_SSID_BASE, uid)
    try:
        if AP_PASSWORD:
            ap.config(essid=ssid, password=AP_PASSWORD)
        else:
            ap.config(essid=ssid, authmode=0)
    except Exception:
        ap.config(essid=ssid)
    time.sleep_ms(400)
    servir_http(ap.ifconfig()[0], "Red: " + ssid)
    ap.active(False)


def descargar_usb():
    _mensaje("Conecta el M5 al PC", "y ejecuta en el PC:",
             "descargar_wifi_log.bat")
    _esperar_b()


def ejecutar_opcion():
    global estado
    op = OPCIONES[menu_idx]
    if op == "WiFi local":
        descargar_wifi_local()
    elif op == "Punto de acceso":
        descargar_ap()
    elif op == "USB por serie":
        descargar_usb()
    elif op == "Borrar todo":
        borrar_todo()
        _mensaje("Todo borrado", "punto = 0", "B: volver")
        _esperar_b()
    activar_scan()
    estado = "idle"


# ===================== SETUP / LOOP =====================

def setup():
    global title0, l1, l2, l3, env3, punto
    M5.begin()
    M5.Display.setRotation(1)     # horizontal (240x135): en vertical el texto se salía
    limpiar()
    title0 = Widgets.Title("WiFi Logger", 3, 0xFFFFFF, 0x7D5411, Widgets.FONTS.DejaVu18)
    l1 = Widgets.Label("", 6, 34, 1.0, 0xFF6666, 0x111111, Widgets.FONTS.DejaVu18)
    l2 = Widgets.Label("", 6, 68, 1.0, 0xFFFFFF, 0x111111, Widgets.FONTS.DejaVu12)
    l3 = Widgets.Label("", 6, 98, 1.0, 0x999999, 0x111111, Widgets.FONTS.DejaVu12)
    if _ENV_OK:
        try:
            env3 = ENVUnit(i2c=I2C(0, scl=Pin(33), sda=Pin(32), freq=100000), type=3)
        except Exception:
            env3 = None
    punto = ultimo_punto_en_fichero()
    activar_scan()
    refrescar_ui()


def loop():
    global estado, menu_idx, ultimo_scan
    M5.update()

    if estado == "idle":
        if BtnA.wasPressed():
            iniciar()
            refrescar_ui()
        elif BtnB.wasPressed():
            estado = "menu"
            menu_idx = 0
            refrescar_ui()

    elif estado == "rec":
        # Parar por FLANCO: la transición de pulsación se detecta aunque ocurra
        # durante un escaneo, y no rearranca al mantener el botón.
        if BtnA.wasPressed():
            parar()
            refrescar_ui()
        else:
            ahora = time.ticks_ms()
            if time.ticks_diff(ahora, ultimo_scan) >= SCAN_INTERVAL:
                ultimo_scan = ahora
                escanear()
                M5.update()                    # releer el botón tras el escaneo
                if BtnA.wasPressed():
                    parar()
                refrescar_ui()
                if estado == "rec" and flash_libre_kb() < FLASH_MIN_KB:
                    parar()
                    _mensaje("FLASH LLENA", "", "B: menu")

    elif estado == "menu":
        if BtnA.wasPressed():
            menu_idx = (menu_idx + 1) % len(OPCIONES)
            refrescar_ui()
        elif BtnB.wasPressed():
            ejecutar_opcion()
            refrescar_ui()

    time.sleep_ms(20)


if __name__ == "__main__":
    try:
        setup()
        while True:
            loop()
    except (Exception, KeyboardInterrupt) as e:
        if log_file:
            try:
                log_file.close()
            except Exception:
                pass
        print("Error:", e)
