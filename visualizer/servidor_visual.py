"""
Servidor HTTP local para el visualizador 3D.

Todo lo que depende del edificio sale de config.yaml: cuántas plantas hay, qué
imagen usa cada una, su altura y la escala. Este servidor no cablea ningún
nombre de fichero ni ningún número de plantas.

Sirve:
  /                  visualizador3d.html
  /config.json       edificio + plantas + credenciales MQTT (desde .env)
  /plano/<id>        plano de la planta <id> declarada en config.yaml
  /heatmap/<id>      textura de cobertura de la planta <id>, si la hay
  /logo.png          logo opcional (visualizer/logo.png)

Uso:
  cp config.example.yaml config.yaml     # y adáptalo a tu edificio
  cp .env.example .env                   # y pon las credenciales del broker
  python visualizer/servidor_visual.py
  Abre http://localhost:8000

Variables de entorno:
  PORT           puerto de escucha (8000)
  APS_CONFIG     ruta a config.yaml (por defecto, la raíz del repositorio)
  PLANOS_BASE    directorio base para resolver rutas relativas de las imágenes
                 (por defecto, la raíz del repositorio)
  OPEN_BROWSER   0 para no abrir el navegador (útil en un servidor headless)
"""
import http.server
import json
import os
import socketserver
import threading
import webbrowser
from pathlib import Path

import yaml

try:
    from dotenv import load_dotenv
except ImportError:                                   # dotenv es opcional
    def load_dotenv(*a, **kw):
        pass

PORT = int(os.environ.get("PORT", 8000))

VIS_DIR  = Path(__file__).resolve().parent            # visualizer/
REPO_DIR = VIS_DIR.parent                             # raíz del repositorio

CONFIG_PATH = Path(os.environ.get("APS_CONFIG", REPO_DIR / "config.yaml"))
PLANOS_BASE = Path(os.environ.get("PLANOS_BASE", REPO_DIR))

load_dotenv(REPO_DIR / ".env")

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript",
    ".css": "text/css",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".json": "application/json",
}


def mime_de(path: Path) -> str:
    return MIME.get(path.suffix.lower(), "application/octet-stream")


def resolver(ruta: str) -> Path:
    """Resuelve una ruta del config.yaml. Absoluta se respeta; relativa cuelga
    de PLANOS_BASE (por defecto, la raíz del repositorio)."""
    p = Path(ruta)
    return p if p.is_absolute() else (PLANOS_BASE / p)


def cargar_config() -> dict:
    """Lee config.yaml. Devuelve {} si no existe o está mal formado; el
    visualizador muestra el error en vez de quedarse en negro."""
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {"_error": f"No existe {CONFIG_PATH.name}. Copia config.example.yaml a config.yaml."}
    except yaml.YAMLError as e:
        return {"_error": f"config.yaml no es YAML válido: {e}"}


def plantas_de(cfg: dict) -> list:
    """Lista normalizada de plantas, ordenada por altura ascendente.

    La altura de cada planta se toma de `altura_m` si está; si no, se reparte
    con `altura_planta_m` del edificio según el orden de declaración. Así el
    caso normal (plantas equiespaciadas) no obliga a escribir alturas a mano.
    """
    edificio = cfg.get("edificio", {}) or {}
    paso = float(edificio.get("altura_planta_m", 14))
    salida = []
    for i, p in enumerate(cfg.get("plantas", []) or []):
        pid = str(p.get("id", f"P{i + 1}"))
        salida.append({
            "id": pid,
            "etiqueta": p.get("etiqueta", pid),
            "altura_m": float(p["altura_m"]) if p.get("altura_m") is not None else i * paso,
            "simetria_x": bool(p.get("simetria_x", False)),
            "simetria_y": bool(p.get("simetria_y", False)),
            "_imagen": p.get("imagen"),
            "_heatmap": p.get("heatmap"),
        })
    salida.sort(key=lambda p: p["altura_m"])
    return salida


class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        # Silenciar los accesos correctos; los errores sí interesan
        if args and str(args[1]) not in ("200", "304"):
            super().log_message(fmt, *args)

    def send_file(self, path: Path, mime: str = None):
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            self.send_error(404, f"No encontrado: {path.name}")
            return
        except OSError as e:
            self.send_error(500, str(e))
            return
        self.send_response(200)
        self.send_header("Content-Type", mime or mime_de(path))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, obj: dict):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _config_json(self) -> dict:
        """Todo lo que el visualizador necesita para dibujar el edificio.

        El puerto MQTT que se entrega al navegador es el de WebSocket seguro
        (8884 en HiveMQ Cloud), no el de MQTT puro: el navegador no habla MQTT
        sobre TCP.
        """
        cfg = cargar_config()
        if "_error" in cfg:
            return {"error": cfg["_error"]}

        edificio = cfg.get("edificio", {}) or {}
        plantas = []
        for p in plantas_de(cfg):
            plantas.append({
                "id": p["id"],
                "etiqueta": p["etiqueta"],
                "altura_m": p["altura_m"],
                "simetria_x": p["simetria_x"],
                "simetria_y": p["simetria_y"],
                "plano": f"/plano/{p['id']}" if p["_imagen"] else None,
                "heatmap": f"/heatmap/{p['id']}" if p["_heatmap"] else None,
            })

        vis = cfg.get("visualizador", {}) or {}
        return {
            "edificio": {
                "nombre": edificio.get("nombre", "Edificio"),
                "descripcion": edificio.get("descripcion", ""),
                "ancho_m": float(edificio.get("ancho_m", 100)),
                "fondo_m": float(edificio.get("fondo_m", 50)),
                "altura_planta_m": float(edificio.get("altura_planta_m", 14)),
            },
            "plantas": plantas,
            "mqtt": {
                "host": os.environ.get("MQTT_HOST", ""),
                "port": int(os.environ.get("MQTT_WS_PORT", 8884)),
                "user": os.environ.get("MQTT_USER", ""),
                "pass": os.environ.get("MQTT_PASS", ""),
            },
            "coordOffset": {
                "x": float(vis.get("coord_offset_x", 0)),
                "y": float(vis.get("coord_offset_y", 0)),
            },
        }

    def _servir_imagen_de_planta(self, pid: str, campo: str):
        for p in plantas_de(cargar_config()):
            if p["id"] == pid:
                ruta = p.get(campo)
                if not ruta:
                    self.send_error(404, f"La planta {pid} no declara {campo[1:]} en config.yaml")
                    return
                real = resolver(ruta)
                if not real.is_file():
                    self.send_error(404, f"No existe el fichero {ruta} declarado para la planta {pid}")
                    return
                self.send_file(real)
                return
        self.send_error(404, f"Planta desconocida: {pid}")

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/config.json":
            self.send_json(self._config_json())
            return

        if path in ("/", "/index.html"):
            self.send_file(VIS_DIR / "visualizador3d.html")
            return

        if path == "/logo.png":
            logo = VIS_DIR / "logo.png"
            if logo.is_file():
                self.send_file(logo)
            else:
                self.send_error(404, "logo.png no encontrado (es opcional)")
            return

        if path.startswith("/plano/"):
            self._servir_imagen_de_planta(path[len("/plano/"):], "_imagen")
            return

        if path.startswith("/heatmap/"):
            self._servir_imagen_de_planta(path[len("/heatmap/"):], "_heatmap")
            return

        # Estáticos de visualizer/, sin salir del directorio
        rel = path.lstrip("/")
        local = (VIS_DIR / rel).resolve()
        if VIS_DIR in local.parents and local.is_file():
            self.send_file(local)
            return

        self.send_error(404, path)


def main():
    cfg = cargar_config()
    plantas = plantas_de(cfg)

    print()
    print("=" * 60)
    print("  Visualizador 3D — Geolocalización indoor")
    print("=" * 60)
    print(f"  URL          : http://localhost:{PORT}")
    print(f"  config.yaml  : {CONFIG_PATH}")

    if "_error" in cfg:
        print(f"  ERROR        : {cfg['_error']}")
    elif not plantas:
        print("  ERROR        : config.yaml no declara ninguna planta.")
    else:
        edificio = cfg.get("edificio", {}) or {}
        print(f"  Edificio     : {edificio.get('nombre', '(sin nombre)')}")
        print(f"  Plantas      : {len(plantas)}")
        for p in plantas:
            img = resolver(p["_imagen"]) if p["_imagen"] else None
            heat = resolver(p["_heatmap"]) if p["_heatmap"] else None
            estado = "OK" if img and img.is_file() else ("SIN PLANO" if not img else "NO ENCONTRADO")
            extra = ""
            if heat:
                extra = "  cobertura: " + ("OK" if heat.is_file() else "NO ENCONTRADA")
            print(f"    {p['id']:>4s}  z={p['altura_m']:>6.1f} m  plano: {estado}{extra}")
            if img and not img.is_file():
                print(f"          -> se esperaba {img}")

    print()
    print("  Ctrl+C para detener")
    print("=" * 60)
    print()

    with socketserver.TCPServer(("", PORT), Handler) as srv:
        srv.allow_reuse_address = True
        if os.environ.get("OPEN_BROWSER", "1") == "1":
            threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido.")


if __name__ == "__main__":
    main()
