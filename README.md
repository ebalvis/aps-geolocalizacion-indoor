# Geolocalización indoor multisensor (APS)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21700904.svg)](https://doi.org/10.5281/zenodo.21700904)
[![Licencia: MIT](https://img.shields.io/badge/c%C3%B3digo-MIT-b68235)](LICENSE)
[![Licencia: CC BY 4.0](https://img.shields.io/badge/documentaci%C3%B3n-CC%20BY%204.0-b68235)](LICENSE-docs)

> **In English.** An open platform for a signal-processing lab course: student teams
> build an indoor positioning system for their own building. An M5StickC Plus 2 measures
> WiFi signal strength and publishes it over MQTT, a Python server estimates the
> position, and a Three.js viewer shows it live in the browser. The viewer adapts to any
> building through a single config file — floors, plans, heights and scale.
>
> The teaching material is deliberately incomplete: the signal-processing core is left
> as marked `TODO`s, because that is what the course assesses. See *Qué está terminado y
> qué no* below.
>
> **All documentation and code comments are in Spanish**, including the seven lab
> handouts and the project guides. The identifiers in the code are Spanish too. Code is
> MIT-licensed, teaching material CC BY 4.0.

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

**Línea 1 del material** (curso 2026-2027), publicada como versión 1.2.0. Los resultados
de la comunicación de EDUTRENDS 2026 corresponden a la v1.0.0 y **son solo de WiFi**: el
sistema de referencia estima la posición a partir de los escaneos y usa la IMU como
filtro temporal, no como sensor de posición. De la v1.0.0 a la v1.2.0 se añadieron el
guion de laboratorio y los metadatos del depósito, se unificó el umbral de potencia y se
rehízo la documentación con la identidad visual de la asignatura; el método de estimación
y los resultados numéricos no cambiaron. El detalle, en `CHANGELOG.md`.

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
| `planos/` | Los tres planos del edificio de ejemplo, más uno con cuadrícula métrica y el sistema de coordenadas marcado. |
| `docs/` | Guía del profesorado, guion de laboratorio, arquitectura, modelo de propagación, protocolo MQTT, guía de MicroPython y manual de UIFlow 2. |
| `docs/practicas/` | Las siete prácticas B1–B7 en PDF, el enunciado y el calendario del proyecto, y en `guias/` las de los dos primeros hitos y los criterios de evaluación. |

**Si vas a impartirlo, empieza por [`docs/guia-profesor.md`](docs/guia-profesor.md)**: de
la primera prueba sin hardware a la entrega final, incluida la calibración de tus planos
y la campaña de medidas. Y después, [`docs/guion-laboratorio.pdf`](docs/guion-laboratorio.pdf),
que baja al detalle de cada una de las trece sesiones: qué dejar preparado, en qué se
comprueba que ha salido y qué suele torcerse.

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

El firmware se copia al M5StickC Plus 2 (MicroPython). Sus credenciales van en el propio
fichero, porque MicroPython no tiene `.env`: los esqueletos vienen con marcadores
`___MQTT_USER___` y cada equipo pone ahí las suyas en su copia. **En el material que se
reparte, los marcadores se quedan como están.** El servidor sí lee las suyas de `.env`.
Los pasos completos están en `firmware/README.md` y `server/README.md`.

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

El repositorio está archivado en Zenodo, así que la cita no depende de que esta URL de
GitHub siga existiendo:

> Balvís Outeiriño, E., Novo-Lourés, M. y García Lourenço, A. M. (2026).
> *Geolocalización indoor multisensor (APS): plataforma abierta para una práctica de
> laboratorio*. Zenodo. https://doi.org/10.5281/zenodo.21700904

Ese DOI es el **de concepto**: apunta siempre a la versión archivada más reciente, que
hoy es la v1.1.1, con DOI propio
[10.5281/zenodo.21700905](https://doi.org/10.5281/zenodo.21700905). Para citar una
versión concreta se usa su DOI, no el de concepto.

Los resultados de la comunicación de EDUTRENDS 2026 corresponden a la **v1.0.0**. Los
datos de cita en formato legible por máquina están en `CITATION.cff`.

## Contacto

Eduardo Balvís Outeiriño, Universidade de Vigo. Correo: ebalvis@uvigo.gal
