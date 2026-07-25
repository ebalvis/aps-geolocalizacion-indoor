#!/usr/bin/env python3
"""
server_skeleton.py — Esqueleto del servidor Python para la práctica final APS.

Plataforma: Python 3.10+ con paho-mqtt (pip install paho-mqtt).
Opcional: pandas para la carga de CSVs (pip install pandas).

Vuestra tarea es completar los 6 TODOs marcados con "# TODO <N>:".

El TODO 6 (fusión WiFi + PDR) combina el fix WiFi del k-NN con la predicción
de navegación inercial (imu_pdr) por ponderación de VARIANZA INVERSA, para que
la posición avance de forma suave entre correcciones. Ver "Parte 4 - Navegacion
inercial PDR" del enunciado.

Flujo del programa (no lo cambiéis):
  1. Cargar base_antenas.csv y base_fingerprints.csv en memoria (TODO 1)
  2. Opcionalmente cargar base_plantas.csv si existe
  3. Conectar al broker MQTT compartido del aula
  4. Suscribirse a indoor_geolocation/<equipo>/location/data
  5. Para cada mensaje recibido:
        - leer el estado_imu y gestionar el buffer (TODO 3)
        - agregar_buffer sobre las muestras acumuladas (TODO 2a)
        - estimar_posicion_knn (TODO 2b)
        - fusionar el fix WiFi con el PDR por varianza inversa (TODO 6)
        - verificador barométrico opcional (TODO 4)
        - publicar en indoor_geolocation/<equipo>/location/result (TODO 5)

El identificador que pases en --equipo es el mismo que hay que escribir en el
visualizador para ver tu marcador, y el mismo que lleva el firmware en GRUPO.

Uso:
    python server_skeleton.py --equipo G1 \
        --antenas base_antenas.csv \
        --fingerprints base_fingerprints.csv \
        [--plantas base_plantas.csv]

Autor: Eduardo Balvís — APS, Grado en IA, UVigo, curso 2025/2026.
"""

import argparse
import csv
import json
import ssl
import sys
import time
import math
from pathlib import Path
from collections import defaultdict

import paho.mqtt.client as mqtt


# =========================================================================
# Configuración del broker
# =========================================================================
# Las credenciales NO van en el código. Se leen del fichero .env de la raíz del
# repositorio, o de variables de entorno:
#
#   cp .env.example .env      y rellenar MQTT_HOST, MQTT_USER y MQTT_PASS
#
# Windows PowerShell:  $env:MQTT_HOST="..."; $env:MQTT_USER="..."; $env:MQTT_PASS="..."
# Linux / macOS:       export MQTT_HOST=...  MQTT_USER=...  MQTT_PASS=...
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass        # dotenv es opcional si usas variables de entorno

MQTT_HOST     = os.environ.get("MQTT_HOST", "")
MQTT_PORT     = int(os.environ.get("MQTT_PORT", "8883"))
MQTT_USER     = os.environ.get("MQTT_USER", "")
MQTT_PASSWORD = os.environ.get("MQTT_PASS", "")

_faltan = [n for n, v in (("MQTT_HOST", MQTT_HOST),
                          ("MQTT_USER", MQTT_USER),
                          ("MQTT_PASS", MQTT_PASSWORD)) if not v]
if _faltan:
    sys.exit("Falta configurar el broker: " + ", ".join(_faltan) +
             "\nCopia .env.example a .env y rellénalo, o define esas variables "
             "de entorno. Los datos del broker te los da el profesor.")

# Parámetros del algoritmo
N_BUFFER_MAX   = 5       # tamaño máximo del buffer de escaneos en estado 'quieto'
K_NN           = 3       # vecinos en k-NN
RSSI_MIN       = -85     # dBm, umbral mínimo para considerar una antena visible
MIN_BSSIDS     = 2       # solapamiento mínimo (BSSIDs comunes) con un fingerprint

# Parámetros de fusión WiFi + PDR (TODO 6)
MAE_WIFI          = 6.0  # m — error típico del fix WiFi (peso WiFi = 1/MAE^2)
SIGMA_PDR_PASO    = 0.15 # m — incertidumbre PDR que se acumula por paso


# =========================================================================
# Estado global del servidor
# =========================================================================
base_antenas      = {}   # dict: bssid -> {x, y, planta, zona, rssi_medio, ...}
base_fingerprints = []   # list: [{planta, punto, x, y, zona, rssi_por_bssid: {bssid: rssi_medio}}]
base_plantas      = []   # list: [{planta, presion_media}] (opcional; [] si no se usa)

buffer_scans      = []   # buffer temporal de mensajes recibidos (último escaneo primero)
pos_anterior      = None  # última posición fusionada {x, y} (para la predicción PDR)

EQUIPO            = None  # se rellena desde argparse
TOPIC_DATA        = None
TOPIC_RESULT      = None


# =========================================================================
# TODO 1 — CARGA DE LAS BASES DE DATOS DE H2
# =========================================================================
# Cargar los tres CSVs en las estructuras de memoria declaradas arriba.
# base_plantas es OPCIONAL: si el argumento es None, dejad la lista vacía.

def cargar_base_antenas(ruta):
    """
    Carga base_antenas.csv en base_antenas (dict: bssid -> dict con el resto de columnas).
    Se usa solo para el bonus de trilateración. El algoritmo principal (k-NN)
    usa base_fingerprints.
    """
    global base_antenas
    # TODO 1.a: abrir ruta con csv.DictReader y construir el dict
    # Pista: base_antenas[row['BSSID']] = {"x": float(row["x"]), "y": float(row["y"]),
    #                                      "planta": row["planta"], ...}
    print(f"[cargar] base_antenas: {len(base_antenas)} antenas cargadas")


def cargar_base_fingerprints(ruta):
    """
    Carga base_fingerprints.csv. El archivo está en formato largo
    (una fila por (punto, BSSID)). Debéis agregar por (planta, punto) para
    construir una lista donde cada elemento es un fingerprint completo:

        [{"planta": "Baixo", "punto": 1, "x": 2.0, "y": 3.5, "zona": "vestibulo",
          "rssi_por_bssid": {"aa:bb:...": -72.5, "f4:0e:...": -65.0, ...}},
         ...]
    """
    global base_fingerprints
    # TODO 1.b: leer el CSV y construir la lista agregando por (planta, punto)
    # Pista: usar collections.defaultdict(dict) indexado por (planta, punto)
    # para ir acumulando los BSSIDs de cada punto, y después aplanar a lista.
    print(f"[cargar] base_fingerprints: {len(base_fingerprints)} puntos cargados")


def cargar_base_plantas(ruta):
    """OPCIONAL. Si ruta es None, dejar base_plantas vacía y salir."""
    global base_plantas
    if ruta is None:
        print("[cargar] base_plantas: no proporcionado (verificador baro desactivado)")
        return
    # TODO 1.c: cargar si ruta existe
    print(f"[cargar] base_plantas: {len(base_plantas)} plantas cargadas")


# =========================================================================
# TODO 2 — AGREGAR BUFFER + K-NN PONDERADO
# =========================================================================
# Dos funciones puras (sin estado global) que implementan el núcleo del
# algoritmo. Están definidas en la sección 6.7 del enunciado.

def agregar_buffer(buffer):
    """
    Promedia el RSSI de cada BSSID a través de todos los escaneos del buffer.

    Entrada: buffer = [scan_dict, scan_dict, ...] donde cada scan_dict tiene
    la forma del mensaje recibido (con 'wifi_scans' dentro).

    Salida: lista de dicts [{'BSSID': 'aa:bb:...', 'potencia': -65.0}, ...]
    con el RSSI promediado.
    """
    # TODO 2.a: implementar la agregación
    #
    # Pasos:
    #   1. Crear un dict rssi_por_bssid: {bssid: [rssi1, rssi2, ...]}
    #   2. Para cada scan del buffer, recorrer scan['wifi_scans']
    #   3. Promediar las listas
    #   4. Devolver la lista de dicts
    return []


def estimar_posicion_knn(scan_agregado, fingerprints, k=K_NN):
    """
    k-NN ponderado por distancia inversa en espacio RSSI.

    Entrada:
      - scan_agregado: lista [{'BSSID', 'potencia'}, ...] del escaneo actual
      - fingerprints: lista de fingerprints de base_fingerprints
      - k: número de vecinos a considerar

    Salida:
      dict con 'x', 'y', 'nivel', 'zona_estimada' (o 'zona_estimada'='desconocida'
      si no se encuentra ningún fingerprint con solapamiento suficiente)
    """
    # TODO 2.b: implementar k-NN ponderado
    #
    # Pasos:
    #   1. Filtrar scan_agregado por RSSI >= RSSI_MIN, construir dict
    #      rssi_actual = {bssid: potencia}
    #   2. Para cada fingerprint fp en fingerprints:
    #        - bssids_comunes = set(rssi_actual) & set(fp['rssi_por_bssid'])
    #        - si len(comunes) < MIN_BSSIDS: saltar
    #        - calcular distancia euclidiana en RSSI sobre los comunes:
    #             sumsq = sum((rssi_actual[b] - fp['rssi_por_bssid'][b])**2 for b in comunes)
    #             d = sqrt(sumsq / len(comunes))
    #        - guardar (d, fp)
    #   3. Ordenar por d ascendente, coger los k primeros
    #   4. Calcular pesos = 1/(d+0.1), promediar x,y ponderados por peso
    #   5. Devolver dict con x, y redondeados, nivel = planta del fp más cercano,
    #      zona_estimada = zona del fp más cercano
    return {"zona_estimada": "desconocida", "x": None, "y": None, "nivel": None}


# =========================================================================
# TODO 6 — FUSIÓN WiFi + PDR POR VARIANZA INVERSA
# =========================================================================
# Combina el fix WiFi (absoluto, ruidoso) con la predicción PDR (suave, con
# deriva). Idea: cada estimación pesa según el inverso de su varianza.
#   w_wifi = 1 / MAE_WIFI^2                          (confianza fija del WiFi)
#   sigma_pdr = SIGMA_PDR_PASO * sqrt(nº pasos)      (crece con los pasos)
#   w_pdr  = 1 / sigma_pdr^2
#   x_fus  = (w_wifi*x_wifi + w_pdr*x_pdr) / (w_wifi + w_pdr)
# donde la predicción PDR es (pos_anterior + Δ) con Δ = imu_pdr[dx_m, dy_m].

def fusionar_wifi_pdr(fix_wifi, pos_prev, imu_pdr):
    """
    fix_wifi : {"x", "y"} del k-NN, o None si no hubo estimación.
    pos_prev : {"x", "y"} última posición fusionada, o None.
    imu_pdr  : {"dx_m", "dy_m", "steps"} del mensaje, o None.
    Devuelve (x, y, metodo) con metodo in {"WiFi","PDR","fusion","sin_datos"}.
    """
    tiene_wifi = fix_wifi is not None and fix_wifi.get("x") is not None
    tiene_pdr  = (pos_prev is not None and imu_pdr is not None and "dx_m" in imu_pdr)

    if not tiene_wifi and not tiene_pdr:
        return None, None, "sin_datos"
    if tiene_wifi and not tiene_pdr:
        return fix_wifi["x"], fix_wifi["y"], "WiFi"

    # Predicción PDR: donde estábamos + lo que dice el desplazamiento inercial
    x_pdr = pos_prev["x"] + imu_pdr["dx_m"]
    y_pdr = pos_prev["y"] + imu_pdr["dy_m"]
    if not tiene_wifi:
        return x_pdr, y_pdr, "PDR"

    # TODO 6: fusión por varianza inversa
    #   1. n = max(1, imu_pdr.get("steps", 1))
    #   2. sigma_pdr = max(SIGMA_PDR_PASO * sqrt(n), 0.5)
    #   3. w_wifi = 1/MAE_WIFI**2 ; w_pdr = 1/sigma_pdr**2 ; w = w_wifi + w_pdr
    #   4. x = (w_wifi*fix_wifi["x"] + w_pdr*x_pdr) / w   (idem y)
    #   5. return x, y, "fusion"
    #
    # Mientras no lo implementéis, se devuelve solo el WiFi (sin fusión):
    return fix_wifi["x"], fix_wifi["y"], "WiFi"


# =========================================================================
# TODO 3 — PROCESAR MENSAJE: GESTIÓN DEL BUFFER SEGÚN ESTADO_IMU
# =========================================================================
# Lógica de filtrado temporal descrita en la sección 6.9 del enunciado:
#   - 'rapido'  -> vaciar buffer, devolver estado='movimiento_rapido'
#   - 'moviendo' -> vaciar buffer y añadir solo el scan actual, devolver
#                   estado='en_movimiento'
#   - 'quieto'  -> añadir al buffer (máx N_BUFFER_MAX), promediar y aplicar k-NN,
#                  devolver estado='ok'

def procesar_mensaje(scan):
    global buffer_scans
    estado_imu = scan.get("estado_imu", "quieto")

    # TODO 3.a: caso 'rapido' - vaciar buffer, devolver dict con estado='movimiento_rapido'
    # if estado_imu == "rapido":
    #     buffer_scans = []
    #     return {..., "estado": "movimiento_rapido", "aviso": "en movimiento rapido"}

    # TODO 3.b: caso 'moviendo' - reset buffer a [scan], luego seguir con la estimación
    # if estado_imu == "moviendo":
    #     buffer_scans = [scan]

    # TODO 3.c: caso 'quieto' - append al buffer con tope N_BUFFER_MAX
    # else:
    #     buffer_scans.append(scan)
    #     if len(buffer_scans) > N_BUFFER_MAX:
    #         buffer_scans.pop(0)

    # Llamar a agregar + k-NN
    scan_agregado = agregar_buffer(buffer_scans)
    resultado = estimar_posicion_knn(scan_agregado, base_fingerprints, k=K_NN)

    # ── Fusión WiFi + PDR (TODO 6) ─────────────────────────────────────────
    # Combina el fix WiFi con la predicción inercial y actualiza pos_anterior.
    global pos_anterior
    fix_wifi = None
    if resultado.get("x") is not None and resultado.get("y") is not None:
        fix_wifi = {"x": resultado["x"], "y": resultado["y"]}
    x_fus, y_fus, metodo_pos = fusionar_wifi_pdr(
        fix_wifi, pos_anterior, scan.get("imu_pdr"))
    if x_fus is not None:
        resultado["x"] = round(x_fus, 2)
        resultado["y"] = round(y_fus, 2)
        resultado["metodo_pos"] = metodo_pos     # WiFi / PDR / fusion
        pos_anterior = {"x": x_fus, "y": y_fus}

    # Añadir metadatos
    resultado["estado"] = "ok" if estado_imu == "quieto" else "en_movimiento"
    resultado["timestamp"] = scan.get("timestamp")
    resultado["aviso"] = None

    # TODO 4 — VERIFICADOR BARÓMETRO (OPCIONAL)
    # Si base_plantas no está vacía y scan tiene 'presion', buscar la planta
    # más cercana en presión. Si no coincide con resultado['nivel'], rellenar
    # resultado['aviso'] = f"discrepancia_baro: {planta_pres}"
    #
    # if base_plantas and "presion" in scan and resultado.get("nivel") is not None:
    #     planta_pres = min(base_plantas,
    #                       key=lambda p: abs(p["presion_media"] - scan["presion"]))["planta"]
    #     if planta_pres != resultado["nivel"]:
    #         resultado["aviso"] = f"discrepancia_baro: {planta_pres}"

    return resultado


# =========================================================================
# MQTT: conexión y callbacks
# =========================================================================
def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0 or reason_code == "Success":
        print(f"[mqtt] conectado a {MQTT_HOST}:{MQTT_PORT}")
        client.subscribe(TOPIC_DATA)
        print(f"[mqtt] suscrito a {TOPIC_DATA}")
    else:
        print(f"[mqtt] fallo de conexión: {reason_code}")


def on_message(client, userdata, msg):
    try:
        payload_str = msg.payload.decode("utf-8")
        scan = json.loads(payload_str)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        print(f"[mqtt] mensaje inválido descartado: {e}")
        return

    print(f"[data] recibido scan: estado_imu={scan.get('estado_imu')}, "
          f"{len(scan.get('wifi_scans', []))} APs")

    # Procesar y publicar resultado
    resultado = procesar_mensaje(scan)

    # TODO 5 — PUBLICAR EL RESULTADO
    # publicar resultado (como JSON) en TOPIC_RESULT
    # Pista: client.publish(topic, payload_str) donde payload_str = json.dumps(resultado)
    #
    # try:
    #     payload_out = json.dumps(resultado)
    #     client.publish(TOPIC_RESULT, payload_out)
    #     print(f"[result] publicado: estado={resultado.get('estado')}, "
    #           f"nivel={resultado.get('nivel')}, zona={resultado.get('zona_estimada')}")
    # except Exception as e:
    #     print(f"[mqtt] error publicando: {e}")


# =========================================================================
# Main
# =========================================================================
def parse_args():
    ap = argparse.ArgumentParser(description="Servidor de geolocalización indoor (APS)")
    ap.add_argument("--equipo", required=True,
                    help="Identificador de equipo asignado (p.ej. 'e01')")
    ap.add_argument("--antenas", required=True, type=Path,
                    help="Ruta a base_antenas.csv")
    ap.add_argument("--fingerprints", required=True, type=Path,
                    help="Ruta a base_fingerprints.csv")
    ap.add_argument("--plantas", type=Path, default=None,
                    help="Ruta a base_plantas.csv (opcional)")
    return ap.parse_args()


def main():
    global EQUIPO, TOPIC_DATA, TOPIC_RESULT

    args = parse_args()
    EQUIPO       = args.equipo
    # Mismos canales que usan el firmware, el simulador y el visualizador. Si
    # los cambias aquí, cámbialos también allí o la cadena se rompe en silencio.
    TOPIC_DATA   = f"indoor_geolocation/{EQUIPO}/location/data"
    TOPIC_RESULT = f"indoor_geolocation/{EQUIPO}/location/result"

    print(f"[server] equipo = {EQUIPO}")
    print(f"[server] topic data   = {TOPIC_DATA}")
    print(f"[server] topic result = {TOPIC_RESULT}")

    # Cargar bases (TODO 1)
    cargar_base_antenas(args.antenas)
    cargar_base_fingerprints(args.fingerprints)
    cargar_base_plantas(args.plantas)

    if not base_fingerprints:
        print("[server] ERROR: base_fingerprints está vacía. Imposible estimar posición.", file=sys.stderr)
        sys.exit(2)

    # Conectar al broker
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"server_{EQUIPO}_{int(time.time())}"
    )
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    except Exception as e:
        print(f"[server] ERROR conectando a MQTT: {e}", file=sys.stderr)
        sys.exit(3)

    print("[server] escuchando mensajes. Ctrl+C para salir.")
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[server] parada limpia por Ctrl+C")
        client.disconnect()


if __name__ == "__main__":
    main()
