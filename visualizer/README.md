# Visualizador 3D

Reconstruye el edificio en el navegador (Three.js) y muestra la posición de cada equipo
en tiempo real, con su trayectoria y, de forma opcional, el mapa de cobertura WiFi. Se
suscribe al broker por WebSocket seguro. El renderizado corre en el cliente; el servidor
solo sirve la página, los planos y la configuración.

**Nada del edificio está en el código.** El número de plantas, sus nombres, sus planos y
sus alturas salen de `config.yaml`. Sirve igual para dos plantas que para siete.

## Arrancar

```bash
pip install -r ../requirements.txt
cp ../config.example.yaml ../config.yaml   # adáptalo a tu edificio
cp ../.env.example ../.env                 # credenciales del broker
python servidor_visual.py
```

Se sirve en `http://localhost:8000`. Ábrelo desde ahí: si abres el HTML como fichero
suelto no hay `/config.json` y el visualizador te lo dirá con un mensaje en pantalla en
vez de quedarse en negro.

Al arrancar, el servidor imprime cada planta declarada y si encontró su plano:

```
  Edificio     : Politécnico de Ourense
  Plantas      : 3
      1P  z=   0.0 m  plano: OK  cobertura: OK
      2P  z=  14.0 m  plano: OK  cobertura: OK
      3P  z=  28.0 m  plano: OK  cobertura: OK
```

Introduce el grupo y verás el marcador. Para probar sin hardware, lanza el simulador de
`../simulator/`; publica en el grupo `G0`.

## Controles

| Tecla | Acción |
|---|---|
| `1`…`9` | encuadra la planta n-ésima, contando de abajo arriba |
| `C` | activa o desactiva la capa de cobertura WiFi |
| `R` | restablece la vista general |

Ratón: arrastrar rota, rueda hace zoom, botón derecho desplaza.

## Adaptarlo a tu edificio

Todo se hace en `config.yaml`, sin tocar código:

1. **Consigue los planos de cada planta** en PNG, JPG o WEBP y déjalos en `../planos/`.
   No importa cómo se llamen: la ruta se declara en la configuración.
2. **Declara una entrada por planta** en `plantas:`, con su `id`, su `etiqueta` y su
   `imagen`. El `id` es el que tu servidor de estimación pondrá en el campo `nivel` de
   los mensajes MQTT.
3. **Mide la huella del edificio** y ponla en `edificio.ancho_m` y `edificio.fondo_m`.
   De ahí salen el tamaño del suelo y el encuadre de la cámara.
4. **Calibra la escala** de cada plano: mide sobre la imagen una distancia real conocida
   y calcula `metros_por_pixel = distancia_m / distancia_px`. Fija también `origen_px`,
   el píxel que hace de origen de coordenadas.
5. **Ajusta las alturas** si no son regulares, con `altura_m` por planta. Si son
   regulares basta con `edificio.altura_planta_m`.
6. Si el plano te sale espejado respecto a cómo mides, invierte el eje con
   `simetria_x` o `simetria_y`.

Cosas que el visualizador tolera sin romperse: plantas sin plano (salen de color liso),
plantas sin `heatmap` (esa capa no aparece), alturas negativas para sótanos, y plantas
declaradas en cualquier orden, porque se ordenan por altura.

El `logo.png` de esta carpeta es opcional: si lo borras, el rótulo se dibuja sin él.

## Mapa de cobertura

Las texturas de `heatmaps/` son una **simulación** con el modelo de propagación
log-distancia, no medidas interpoladas. Detalle en `../docs/modelo-propagacion.md`.

Son opcionales: si ninguna planta declara `heatmap`, el botón de cobertura no aparece.

Vienen ya generadas, así que solo hace falta rehacerlas si cambias de edificio o de
modelo:

```bash
pip install matplotlib scipy          # solo para esta herramienta
python gen_heatmap_texturas.py
```

Lee de `config.yaml` las plantas con `heatmap:`, su plano, su escala y su origen, más
la sección `modelo:` con los parámetros `A` y `n` y las coordenadas de los puntos de
acceso. Genera cada textura alineada píxel a píxel con su plano.

## Dependencias del navegador

Three.js r128, OrbitControls y el cliente MQTT Paho se cargan desde CDN. No hay que
compilar nada, pero **hace falta conexión a internet** la primera vez. Para uso sin red,
descarga los tres ficheros a esta carpeta y cambia los `<script src>` del HTML por rutas
locales; el servidor ya sirve los estáticos de `visualizer/`.

## Endpoints del servidor

| Ruta | Qué devuelve |
|---|---|
| `/` | el visualizador |
| `/config.json` | edificio, plantas y credenciales MQTT (para WebSocket) |
| `/plano/<id>` | el plano de esa planta |
| `/heatmap/<id>` | su textura de cobertura, si la declara |
| `/logo.png` | el logo, si existe |

Variables de entorno: `PORT`, `APS_CONFIG` (ruta del config.yaml), `PLANOS_BASE` (base
para resolver rutas relativas) y `OPEN_BROWSER=0` para no abrir el navegador.
