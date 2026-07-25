# Geolocalización indoor multisensor (APS)

Plataforma abierta para una práctica de laboratorio de la asignatura Adquisición y
Procesamiento de la Señal, del Grado en Inteligencia Artificial de la Universidade de Vigo (Escola Superior de Enxeñaría Informática,
Ourense).

Cada equipo construye, de principio a fin, un sistema de localización en interiores
sobre el propio edificio: un dispositivo mide la potencia de las redes WiFi y las
publica por MQTT, un servidor estima la posición, y un visualizador 3D en el
navegador muestra el resultado en tiempo real. El problema recorre la cadena
completa de tratamiento de señal: adquisición con hardware real, filtrado del ruido,
calibración de un modelo de propagación, extracción de características y fusión de
sensores.

Este repositorio contiene el material que se cita como abierto en la comunicación
presentada en EDUTRENDS 2026 (ver `CITATION.cff`).

**Versión 1.0** (curso 2026-2027). Corresponde al artículo y a la presentación de
EDUTRENDS 2026, y **los resultados que se publican allí son solo de WiFi**: el sistema
de referencia estima la posición a partir de los escaneos y usa la IMU como filtro
temporal, no como sensor de posición.

La navegación inercial sí está en esta versión, pero **como ejercicio**: las prácticas
B4 y B7 la explican y el `TODO 8` del cliente pide implementarla. Lo que traerá la
versión 2 es el PDR resuelto en el sistema de referencia y sus resultados medidos, con
la especificación completa en `CHANGELOG.md`.

## Qué hay aquí

| Carpeta | Contenido |
|---|---|
| `firmware/` | Dos apps MicroPython para el M5StickC (UIFlow 2.0): registrador WiFi (completa) y envío MQTT (esqueleto). |
| `server/` | Esqueleto del servidor de estimación en Python (agregación, k-NN, fusión WiFi + PDR). |
| `simulator/` | Simulador que publica posiciones sin necesidad de hardware, para probar el visualizador. |
| `visualizer/` | Visualizador 3D del edificio en Three.js, su servidor HTTP y las texturas de cobertura. |
| `planos/` | Plano con cuadrícula métrica y sistema de coordenadas (ejemplo, planta 3ª). |
| `docs/` | Arquitectura, modelo de propagación, protocolo MQTT y guía de MicroPython. |
| `docs/practicas/` | Las prácticas de laboratorio B1–B7 y el proyecto integrador (PDF). |

**Si vas a impartirlo, empieza por [`docs/guia-profesor.md`](docs/guia-profesor.md)**: de
la primera prueba sin hardware a la entrega final, incluida la calibración de tus planos
y la campaña de medidas.

## Qué está terminado y qué no

Esto es material docente, y una parte está incompleta **a propósito**: son los
ejercicios que se evalúan. Conviene saberlo antes de clonar.

| Componente | Estado |
|---|---|
| Visualizador 3D y su servidor | **completo y configurable**, funciona out of the box |
| Simulador de posiciones | **completo**, permite ver el sistema sin hardware |
| Registrador WiFi (`firmware/app1_wifi_logger/`) | **completo**, herramienta acabada y probada en dispositivo |
| Servidor de estimación (`server/`) | **esqueleto con 6 `TODO`**: carga de bases, k-NN, filtrado con la IMU, verificador de planta, publicación y fusión |
| Cliente del dispositivo (`firmware/app2_mqtt_sender/`) | **esqueleto con 8 `TODO`**, el último es la navegación inercial (PDR) |

O sea: si clonas esto esperando un sistema de localización que funcione al arrancar, no
lo es. Lo que funciona de extremo a extremo sin escribir una línea es
**simulador → broker → visualizador 3D**. El núcleo de estimación hay que
implementarlo, y el fundamento de cada método está documentado en
`docs/modelo-propagacion.md` para que se pueda hacer.

Si lo que quieres es reutilizar el visualizador con tu propio sistema de localización,
solo tienes que publicar en el topic de resultado con el formato de
`docs/protocolo-mqtt.md`.

## Arquitectura

```
  M5StickC Plus 2            broker MQTT (TLS)          servidor Python
  WiFi + IMU + barómetro  ->  un canal por equipo   ->  agregación + k-NN + fusión
                                                             |
                                              resultado por MQTT
                                                             v
                                          visualizador 3D (navegador, Three.js)
```

Hay dos flujos que se pueden usar por separado:

- Flujo de práctica: el M5StickC publica escaneos, el servidor estima la posición y
  la devuelve por MQTT. Es lo que programa cada equipo.
- Flujo de demostración: el simulador (o el sistema real) publica posiciones y el
  visualizador 3D las pinta sobre el edificio. Sirve para ver el resultado en clase
  y para probar sin hardware.

Detalle de temas y canales en `docs/protocolo-mqtt.md`.

## Puesta en marcha rápida (sin hardware)

Para ver el visualizador funcionando con posiciones simuladas:

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml   # edificio de ejemplo, ya listo
cp .env.example .env                 # y rellena las credenciales de tu broker MQTT

# terminal 1: sirve el visualizador en http://localhost:8000
python visualizer/servidor_visual.py

# terminal 2: publica una ruta simulada
python simulator/test_mqtt_g0.py
```

Abre `http://localhost:8000`, introduce el grupo (por defecto `G0`) y verás el marcador
recorriendo los pasillos. El `config.example.yaml` viene con el edificio del ejemplo y
sus planos incluidos, así que el visualizador se ve sin configurar nada.

Necesitas un broker MQTT con WebSocket sobre TLS. Una cuenta gratuita de HiveMQ Cloud
sirve; el puerto 8883 es para el servidor y el 8884 para el navegador.

## Adaptarlo a otro edificio

El visualizador no cablea ningún número de plantas: todo sale de `config.yaml`. Se ha
probado con dos, tres y cinco plantas, con alturas irregulares y con plantas sin plano.
El procedimiento completo (planos, escala, origen de coordenadas) está en
`visualizer/README.md` y `planos/README.md`.

## Firmware y servidor (con hardware)

El firmware se copia al M5StickC Plus 2 (MicroPython) y se editan en el propio
fichero el SSID, la contraseña del WiFi y los datos del broker. El servidor lee sus
credenciales de `.env`. Los pasos completos están en `firmware/README.md` y
`server/README.md`.

## Sobre el mapa de cobertura WiFi

El mapa de cobertura de `visualizer/heatmaps/` no procede de medidas interpoladas.
Es una simulación: se genera con el modelo de propagación log-distancia (potencia de
referencia a un metro de unos -61 dBm y exponente de pérdidas cercano a 2,2),
aplicado de forma radial alrededor de la posición de cada punto de acceso, tomando
en cada punto del plano el AP de mayor potencia y añadiendo un sombreado log-normal.
La localización real que hace el sistema es distinta y sí parte de medidas discretas
(ver `docs/modelo-propagacion.md`).

## Licencia

Doble licencia, según lo que uses:

| Qué | Licencia | Fichero |
|---|---|---|
| Código: `firmware/`, `server/`, `simulator/`, `visualizer/` y cualquier `.py`, `.js`, `.html` o `.bat` del repositorio | MIT | `LICENSE` |
| Material docente y gráfico: `docs/` y `planos/` | CC BY 4.0 | `LICENSE-docs` |

En ambos casos puedes reutilizarlo, incluso con fines comerciales, citando la fuente.

## Cómo citar

Ver `CITATION.cff`.

## Contacto

Eduardo Balvís Outeiriño, Universidade de Vigo. Correo: ebalvis@gmail.com
