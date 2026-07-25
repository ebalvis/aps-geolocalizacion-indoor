# Protocolo MQTT

Todo va sobre MQTT con TLS. Cada equipo usa sus propios canales, derivados de su
identificador, para no interferir con los demás.

## Canales

    indoor_geolocation/<equipo>/location/data      dispositivo  ->  servidor
    indoor_geolocation/<equipo>/location/result    servidor     ->  visualizador

`<equipo>` es el mismo identificador en los tres sitios: el `GRUPO` del firmware, el
`--equipo` del servidor y lo que se escribe en el visualizador al abrirlo. Si no coincide,
no se ve nada y no hay ningún error: simplemente cada uno habla por su canal.

## Recorrido completo

```
  M5StickC ──data──> broker ──data──> servidor de estimación
                                            │
                                          result
                                            v
                        broker ──result──> visualizador 3D
```

El simulador ocupa el lugar del servidor: publica en `result` sin necesidad de
dispositivo ni de estimación, para probar el visualizador.

## Mensaje de datos

Lo publica el dispositivo. El servidor necesita `wifi_scans` y `estado_imu`; el resto es
opcional y lo decide cada equipo.

```json
{
  "grupo": "G1",
  "timestamp": 1719840000,
  "estado_imu": "quieto",
  "presion": 1013.2,
  "wifi_scans": [
    {"BSSID": "aa:bb:cc:dd:ee:ff", "potencia": -65},
    {"BSSID": "11:22:33:44:55:66", "potencia": -72}
  ],
  "imu_pdr": {"dx_m": 0.0, "dy_m": 0.0, "steps": 0}
}
```

`estado_imu` decide qué hace el servidor con el escaneo: acumular en el buffer cuando se
está quieto, para promediar y bajar el ruido, o descartar cuando hay movimiento. Los
valores que use cada equipo son cosa suya, pero el criterio tiene que ser coherente entre
firmware y servidor.

`presion` solo aparece si el equipo tiene la unidad ENV III; sirve para el verificador de
planta. `imu_pdr` lleva el desplazamiento estimado por navegación inercial desde el
mensaje anterior, y es lo que se fusiona con el fix WiFi en el tercer hito.

## Mensaje de resultado

Lo publica el servidor y lo consume el visualizador. Este formato **sí es fijo**: es el
contrato con el visualizador 3D.

```json
{
  "nivel": "3P",
  "x": 12.4,
  "y": 30.8,
  "quieto": false,
  "metodo": "C",
  "n_aps": 6,
  "imu_pdr": {"dx_m": 0.5, "dy_m": 0.0, "steps": 1, "heading": 90.0}
}
```

`x` e `y` van en metros, en el sistema de coordenadas del edificio: el origen y la escala
están en `config.yaml`. `nivel` es el `id` de la planta tal como se declara ahí, así que
tiene que coincidir con lo que el servidor estime. `metodo` y `n_aps` solo alimentan el
panel de información; el visualizador no los usa para colocar el marcador.

## Puertos

| Puerto | Para qué | Quién lo usa |
|---|---|---|
| 8883 | MQTT sobre TLS | dispositivo, servidor, simulador |
| 8884 | MQTT sobre WebSocket seguro | el visualizador, en el navegador |

El navegador no habla MQTT sobre TCP, así que el visualizador necesita el 8884 aunque
todo lo demás use el 8883. Es el error de configuración más común al empezar.

## Si cambias los nombres de los canales

Están en cuatro sitios y tienen que coincidir:

| Fichero | Constante |
|---|---|
| `firmware/app2_mqtt_sender/m5stick_skeleton.py` | `TOPIC_BASE` |
| `server/server_skeleton.py` | `TOPIC_DATA`, `TOPIC_RESULT` |
| `simulator/test_mqtt_g0.py` | `TOPIC` |
| `visualizer/visualizador3d.html` | el topic que se arma con el grupo |
