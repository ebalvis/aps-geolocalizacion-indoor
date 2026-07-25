"""
Simulador de posiciones.

Publica una ruta simulada por MQTT, sin necesidad de hardware, para poder ver el
visualizador 3D funcionando. El marcador recorre los pasillos declarados en
config.yaml, de ida y vuelta, con un pequeño ruido lateral que imita el caminar
y pausas ocasionales.

Uso:
    pip install -r requirements.txt
    cp config.example.yaml config.yaml
    cp .env.example .env          # y pon las credenciales de tu broker
    python simulator/test_mqtt_g0.py

El grupo se cambia con la variable de entorno G0_GROUP. La ruta, la velocidad y
la planta de arranque salen de la sección `simulador:` de config.yaml, y las
plantas por las que va rotando, de `plantas:`.

Formato del mensaje publicado: docs/protocolo-mqtt.md
"""
import json
import math
import os
import random
import ssl
import sys
import time
from pathlib import Path

import paho.mqtt.client as mqtt
import yaml

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*a, **kw):
        pass

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

CONFIG_PATH = Path(os.environ.get("APS_CONFIG", ROOT / "config.yaml"))


def exigir(var):
    """Lee una variable de entorno obligatoria y explica qué hacer si falta,
    en vez de reventar con un KeyError pelado."""
    valor = os.environ.get(var)
    if not valor:
        sys.exit(f"Falta la variable {var}.\n"
                 f"Copia .env.example a .env y rellena las credenciales de tu "
                 f"broker MQTT:\n    cp .env.example .env")
    return valor


MQTT_HOST = exigir("MQTT_HOST")
MQTT_USER = exigir("MQTT_USER")
MQTT_PASS = exigir("MQTT_PASS")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 8883))
GRUPO = os.environ.get("G0_GROUP", "G0")
TOPIC = f"indoor_geolocation/{GRUPO}/location/result"

METODOS = ["A", "B", "C"]

# Ruta y plantas por defecto, por si no hay config.yaml: un cuadrado de 20 m y
# una sola planta. Sirve para comprobar que la cadena MQTT funciona.
RUTA_DEF = [(0.0, 0.0), (20.0, 0.0), (20.0, 20.0), (0.0, 20.0)]

cfg = {}
if CONFIG_PATH.is_file():
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
else:
    print(f"AVISO: no existe {CONFIG_PATH.name}, se usa una ruta de ejemplo.")

sim = cfg.get("simulador", {}) or {}
PLANTAS = [p["id"] for p in (cfg.get("plantas") or []) if p.get("id")] or ["1P"]
PASILLO = [(float(p[0]), float(p[1])) for p in (sim.get("ruta") or RUTA_DEF)]
VEL_MS = float(sim.get("velocidad_ms", 1.2))
DT = float(sim.get("periodo_s", 2.0))
PLANTA_INI = sim.get("planta_inicial") or PLANTAS[0]
PASO = VEL_MS * DT
RUIDO_LAT = 0.4

if len(PASILLO) < 2:
    sys.exit("La ruta del simulador necesita al menos dos puntos "
             "(`simulador.ruta` en config.yaml).")

# Patrulla de ida y vuelta, para recorrer todo y volver al principio
_RUTA = PASILLO + PASILLO[-2:0:-1]
_SEG_LEN = [math.dist(_RUTA[i], _RUTA[i + 1]) for i in range(len(_RUTA) - 1)]
_TOTAL = sum(_SEG_LEN)


def punto_en_ruta(s):
    """(x, y, rumbo) a distancia s metros a lo largo de la ruta cíclica."""
    s = s % _TOTAL
    for i, seg in enumerate(_SEG_LEN):
        if s <= seg or i == len(_SEG_LEN) - 1:
            (x0, y0), (x1, y1) = _RUTA[i], _RUTA[i + 1]
            t = s / seg if seg > 1e-6 else 0.0
            return (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t,
                    math.degrees(math.atan2(y1 - y0, x1 - x0)),
                    x1 - x0, y1 - y0, seg)
        s -= seg
    x, y = _RUTA[-1]
    return x, y, 0.0, 0.0, 0.0, 1.0


def siguiente_mensaje(estado):
    """Avanza la simulación un tick y devuelve el payload a publicar.

    Va aparte de main() para poder probar el formato del mensaje sin broker.
    """
    estado["tick"] += 1
    quieto = random.random() < 0.18
    if not quieto:
        estado["s"] += PASO

    x, y, rumbo, dxseg, dyseg, seglen = punto_en_ruta(estado["s"])

    if seglen > 1e-6:                       # ruido perpendicular al tramo
        jit = random.uniform(-RUIDO_LAT, RUIDO_LAT)
        x += (-dyseg / seglen) * jit
        y += (dxseg / seglen) * jit

    if estado["tick"] % 20 == 0:            # cambio de planta de vez en cuando
        estado["nivel"] = random.choice(PLANTAS)

    dx = 0.0 if quieto else round(x - estado["x_prev"], 3)
    dy = 0.0 if quieto else round(y - estado["y_prev"], 3)
    estado["x_prev"], estado["y_prev"] = x, y

    return {
        "nivel": estado["nivel"],
        "x": round(x, 2),
        "y": round(y, 2),
        "quieto": quieto,
        "metodo": random.choice(METODOS),
        "n_aps": random.randint(3, 12),
        "imu_pdr": {
            "dx_m": dx,
            "dy_m": dy,
            "steps": 0 if quieto else random.randint(1, 3),
            "heading": round(rumbo, 1),
        },
    }


def main():
    print(f"Simulador -> topic: {TOPIC}")
    print(f"Ruta: {len(_RUTA)} tramos, {_TOTAL:.0f} m, paso {PASO:.1f} m/tick")
    print(f"Plantas: {', '.join(PLANTAS)}")

    client = mqtt.Client(client_id=f"sim_{GRUPO}_{random.randint(1000, 9999)}",
                         protocol=mqtt.MQTTv311)
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set_context(ssl.create_default_context())

    print(f"Conectando a {MQTT_HOST}:{MQTT_PORT} ...")
    try:
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    except Exception as e:
        sys.exit(f"No se pudo conectar al broker: {e}\n"
                 f"Revisa MQTT_HOST, MQTT_USER y MQTT_PASS en .env.")
    client.loop_start()
    print(f"Publicando en {TOPIC}. Ctrl+C para detener.\n")

    estado = {"s": 0.0, "tick": 0, "nivel": PLANTA_INI,
              "x_prev": _RUTA[0][0], "y_prev": _RUTA[0][1]}
    try:
        while True:
            msg = siguiente_mensaje(estado)
            client.publish(TOPIC, json.dumps(msg), qos=0)
            estado_txt = "QUIETO" if msg["quieto"] else "MOVIL "
            print(f"  [{msg['nivel']}] x={msg['x']:6.1f} y={msg['y']:5.1f}  {estado_txt}")
            time.sleep(DT)
    except KeyboardInterrupt:
        print("\nDetenido.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
