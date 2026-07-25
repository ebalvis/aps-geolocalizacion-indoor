"""Genera las texturas de cobertura WiFi del visualizador 3D.

IMPORTANTE: lo que produce es una SIMULACIÓN del modelo de propagación
log-distancia, no una interpolación de medidas reales. Sirve para ilustrar por
qué la potencia decae con la distancia, no como mapa de radio.

Para cada planta declarada en config.yaml con `heatmap:` genera una imagen RGBA
alineada píxel a píxel con su plano (mismas dimensiones y mismo origen), con
mapa de color jet, alfa modulado por la intensidad y un sombreado log-normal
correlacionado que rompe la simetría circular.

Todo sale de config.yaml: las plantas, sus planos, la escala, el origen, los
puntos de acceso y los parámetros del modelo. No hay nada cableado.

Uso:
    pip install -r requirements.txt
    python visualizer/gen_heatmap_texturas.py

Requiere matplotlib y scipy además de las dependencias básicas. Están en
requirements.txt marcadas como necesarias solo para esta herramienta: las
texturas ya vienen generadas en el repositorio, así que no hace falta ejecutar
esto salvo que cambies el edificio o el modelo.
"""
import os
import sys
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.cm as cm
    from scipy.ndimage import gaussian_filter
except ImportError as e:
    sys.exit(f"Falta una dependencia de esta herramienta: {e}.\n"
             f"Instálala con:  pip install matplotlib scipy")

VIS_DIR = Path(__file__).resolve().parent
REPO_DIR = VIS_DIR.parent
CONFIG_PATH = Path(os.environ.get("APS_CONFIG", REPO_DIR / "config.yaml"))
BASE = Path(os.environ.get("PLANOS_BASE", REPO_DIR))

# Rango de potencia que se reparte por el mapa de color, en dBm
VMIN, VMAX = -90.0, -60.0

# Parámetros por defecto del modelo, los calibrados en el edificio de ejemplo.
# Se sobreescriben con la sección `modelo:` de config.yaml.
A_DEF, N_DEF = -60.99, 2.22


def resolver(ruta):
    p = Path(ruta)
    return p if p.is_absolute() else BASE / p


def main():
    if not CONFIG_PATH.is_file():
        sys.exit(f"No existe {CONFIG_PATH}.\n"
                 f"Copia config.example.yaml a config.yaml y adáptalo.")

    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}

    modelo = cfg.get("modelo", {}) or {}
    A = float(modelo.get("A", A_DEF))
    N = float(modelo.get("n", N_DEF))

    aps = [(float(p[0]), float(p[1])) for p in (modelo.get("puntos_acceso") or [])]
    if not aps:
        sys.exit("config.yaml no declara `modelo.puntos_acceso`. Añade al menos "
                 "un punto de acceso con sus coordenadas [x, y] en metros.")

    print(f"Modelo log-distancia: A={A:.2f} dBm, n={N:.3f}")
    print(f"Puntos de acceso: {len(aps)}")

    plantas = [p for p in (cfg.get("plantas") or []) if p.get("heatmap")]
    if not plantas:
        sys.exit("Ninguna planta de config.yaml declara `heatmap:`. "
                 "Añade la ruta de salida a las que quieras generar.")

    cmap = matplotlib.colormaps["jet"]
    generadas = 0

    for planta in plantas:
        pid = planta.get("id", "?")
        plano_ruta = planta.get("imagen")
        if not plano_ruta:
            print(f"  {pid}: sin `imagen:`, no se puede alinear la textura. Se omite.")
            continue

        plano = resolver(plano_ruta)
        if not plano.is_file():
            print(f"  {pid}: no existe el plano {plano}. Se omite.")
            continue

        mpp = float(planta.get("metros_por_pixel", 0) or 0)
        origen = planta.get("origen_px")
        if not mpp or not origen:
            print(f"  {pid}: faltan `metros_por_pixel` u `origen_px`. Se omite.")
            continue

        W, H = Image.open(plano).size
        CC, RR = np.meshgrid(np.arange(W), np.arange(H))
        XM = (CC - float(origen[0])) * mpp
        YM = (float(origen[1]) - RR) * mpp

        # Potencia del mejor AP en cada píxel
        best = np.full((H, W), -120.0)
        for ax, ay in aps:
            d = np.maximum(np.hypot(XM - ax, YM - ay), 1.0)
            best = np.maximum(best, A - 10.0 * N * np.log10(d))

        # Sombreado log-normal correlacionado: da contornos orgánicos en vez de
        # círculos perfectos. Semilla fija para que el resultado sea reproducible.
        rng = np.random.default_rng(42)
        shadow = gaussian_filter(rng.normal(0.0, 1.0, best.shape), sigma=35)
        shadow *= 2.5 / shadow.std()
        best = best + shadow

        norm = np.clip((best - VMIN) / (VMAX - VMIN), 0.0, 1.0)
        rgba = cmap(norm)
        rgba[..., 3] = 0.15 + 0.55 * norm   # señal fuerte, más opaco

        salida = resolver(planta["heatmap"])
        salida.parent.mkdir(parents=True, exist_ok=True)
        # Sin `mode=`: Pillow lo deduce de la forma HxWx4, y el parámetro
        # desaparece en Pillow 13.
        Image.fromarray((rgba * 255).astype(np.uint8)).save(salida)
        print(f"  {pid}: {salida.relative_to(BASE) if BASE in salida.parents else salida}"
              f"  ({W}x{H})")
        generadas += 1

    print(f"\n{generadas} textura(s) generada(s).")


if __name__ == "__main__":
    main()
