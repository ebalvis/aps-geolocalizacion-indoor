# Guía del profesorado

Cómo poner esto en marcha en tu centro, de la primera prueba a la entrega final. Da por
supuesto que no conoces el material; no da por supuesto que vayas a usarlo entero.

---

## 1. Qué es y qué no es

Es el andamiaje completo de una práctica de laboratorio en la que cada equipo construye
un sistema de localización en interiores sobre su propio edificio: un M5StickC mide la
potencia de las redes WiFi, un servidor estima la posición y un visualizador 3D la
pinta en tiempo real.

**No es un sistema de localización llave en mano.** El núcleo de estimación se entrega
como esqueleto con los huecos marcados, porque esos huecos son el ejercicio evaluable.
Si lo clonas esperando localizar a alguien al arrancar, no va a pasar.

| Pieza | Estado | Quién la completa |
|---|---|---|
| Visualizador 3D y su servidor | funciona | nadie, se configura |
| Simulador de posiciones | funciona | nadie |
| Registrador WiFi del M5 | funciona | nadie |
| Cliente del M5 (`firmware/app2_`) | 8 huecos | el alumnado |
| Servidor de estimación (`server/`) | 6 huecos | el alumnado |

Puedes usar solo una parte. Mucha gente querrá el visualizador y las prácticas B1–B7 sin
montar el proyecto entero, y eso funciona.

---

## 2. Qué necesitas

**Hardware, por equipo de dos personas:**

- Un M5StickC Plus 2 (o Plus 1.1) con firmware UIFlow 2.0. Es lo único imprescindible.
- Unidad ENV III en el puerto Grove, si quieres usar el barómetro para distinguir
  plantas. Opcional.

**Infraestructura:**

- La red WiFi que ya tenga el edificio. No hay que desplegar nada: el sistema mide las
  redes existentes, no crea infraestructura.
- Un broker MQTT con TLS y WebSocket. Una cuenta gratuita de HiveMQ Cloud basta para un
  curso. Necesitas los dos puertos: 8883 para el dispositivo y el servidor, 8884 para el
  navegador.
- Los planos de tu edificio, una imagen por planta.

**Software:** Python 3.11 o superior y un navegador. El visualizador carga Three.js y el
cliente MQTT desde CDN, así que la primera vez hace falta conexión a internet.

---

## 3. Pruébalo en diez minutos, sin hardware

Antes de comprar nada ni pisar el edificio, comprueba que te sirve:

```bash
git clone <url-del-repositorio>
cd aps-geolocalizacion-indoor
pip install -r requirements.txt
cp config.example.yaml config.yaml
cp .env.example .env
```

Edita `.env` con los datos de tu broker. Luego, en dos terminales:

```bash
python visualizer/servidor_visual.py
```

```bash
python simulator/test_mqtt_g0.py
```

Abre `http://localhost:8000`, escribe el grupo `G0` y verás un marcador recorriendo los
pasillos del edificio de ejemplo, cambiando de planta. Teclas `1`–`9` para encuadrar cada
planta, `C` para la capa de cobertura, `R` para volver a la vista general.

Al arrancar, el servidor te dice qué ha encontrado. Si algo falta, lo dice aquí:

```
  Edificio     : Politécnico de Ourense
  Plantas      : 3
      1P  z=   0.0 m  plano: OK  cobertura: OK
      2P  z=  14.0 m  plano: OK  cobertura: OK
      3P  z=  28.0 m  plano: OK  cobertura: OK
```

---

## 4. Adaptarlo a tu edificio

Todo se hace en `config.yaml`. No hay que tocar código: ni el número de plantas, ni sus
nombres, ni las dimensiones están en el programa.

**Paso 1. Los planos.** Consigue una imagen por planta, en PNG, JPG o WEBP, y déjala en
`planos/`. El nombre da igual.

**Paso 2. La escala.** Mide sobre la imagen, en píxeles, una distancia real que conozcas
—un pasillo, la separación entre dos pilares—:

```
metros_por_pixel = distancia_real_m / distancia_medida_px
```

**Paso 3. El origen.** Elige un punto reconocible **en todas las plantas**: una escalera,
un hueco de ascensor. Anota su píxel `[columna, fila]`. Que sea el mismo punto en todas
es lo que permite comparar posiciones entre plantas. En el ejemplo es la escalera E4.

**Paso 4. Declara las plantas.**

```yaml
edificio:
  nombre: "Tu edificio"
  ancho_m: 96          # ancho_px * metros_por_pixel
  fondo_m: 47
  altura_planta_m: 14  # separación vertical en el render

plantas:
  - id: "1P"
    etiqueta: "Primera planta"
    imagen: "planos/tu_planta_1.png"
    metros_por_pixel: 0.0312
    origen_px: [1407, 1492]
    simetria_y: true
```

`id` es lo que el servidor manda en el campo `nivel` de los mensajes, así que úsalo
también en tus CSV y carpetas.

**Paso 5. Ajusta.** Si el plano sale espejado respecto a cómo mides, invierte el eje con
`simetria_x` o `simetria_y` en vez de retocar la imagen. Si las coordenadas no cuadran
con el suelo dibujado, usa `visualizador.coord_offset_x/y` para el ajuste fino.

Esto tolera sin romperse: cualquier número de plantas, alturas irregulares con `altura_m`
por planta, sótanos con altura negativa, plantas sin plano (salen de color liso) y
plantas declaradas en cualquier orden.

**La ruta del simulador** también sale de aquí, en `simulador.ruta`. Adáptala a tus
pasillos para las demostraciones en clase.

**El mapa de cobertura** es opcional y es una simulación, no medidas. Si quieres
regenerarlo para tu edificio, pon los puntos de acceso y los parámetros del modelo en
`modelo:` y ejecuta:

```bash
pip install matplotlib scipy
python visualizer/gen_heatmap_texturas.py
```

---

## 5. Preparar los dispositivos

1. Instala UIFlow 2.0 en el M5StickC con M5Burner y ponlo en modo USB/MicroPython.
2. Copia `firmware/app1_wifi_logger/wifi_logger.py` al dispositivo con Thonny, el IDE web
   de UIFlow o `mpremote`.
3. Para que arranque solo al encender, guárdalo como `main.py`.

Con `mpremote`, desde el PC:

```bash
python -m mpremote connect COM11 fs cp wifi_logger.py :wifi_logger.py
```

El puerto es el del puente serie del M5: en Windows aparece como `USB-Enhanced-SERIAL
CH9102`. En Linux suele ser `/dev/ttyUSB0`.

Si vas a usar la descarga por «WiFi local», edita antes `WIFI_SSID` y `WIFI_PASS` al
principio de `wifi_logger.py`. Para las otras dos vías no hace falta.

---

## 6. La campaña de medidas

Es el hito 1 y lo que más condiciona el resultado. El registrador funciona **por puntos**:
una grabación es un punto de referencia.

**En el aula, antes de salir:** reparte el plano con la cuadrícula y el origen marcado, y
que cada equipo apunte en papel qué número de punto corresponde a qué posición. El
dispositivo numera solo, pero no sabe dónde está.

**El manejo del M5:**

| Pantalla | Botón A | Botón B |
|---|---|---|
| Parado | empieza a grabar el punto siguiente | abre el menú de descarga |
| Grabando | para | — |
| Menú | cambia de opción | elige |

Escanea cada tres segundos y descarta redes por debajo de −95 dBm. Todo se acumula en
`/flash/wifi_log.csv`, con el número de punto en cada fila. Al reiniciar continúa por
donde iba, así que una campaña puede repartirse en varios días.

**Descarga**, desde el menú del botón B:

- **Punto de acceso** — el M5 crea su propia red `APS-Logger-XXXX`. Conectas el portátil
  y descargas desde `http://192.168.4.1`. **Es la que funciona siempre**, incluso en un
  aula sin red o con la red del centro filtrada.
- **WiFi local** — el M5 se conecta a la red del aula y sirve la misma web.
- **USB por serie** — desde el PC.

Consejos que ahorran una sesión perdida: más puntos y mejor repartidos importa más que
grabar mucho rato en cada uno; el mapa de radio poco denso es justo lo que hace que el
método simple gane, y esa es la lección del análisis. Y recuerda que «Borrar todo»
reinicia también el contador de puntos.

---

## 7. Lo que programa el alumnado

**En el dispositivo** (`firmware/app2_mqtt_sender/m5stick_skeleton.py`, 8 huecos): leer la
presión, clasificar el movimiento con el acelerómetro, construir el mensaje, publicarlo,
tratar la respuesta y mostrarla. El octavo es el PDR: contar pasos, integrar el rumbo con
el giroscopio y estimar el desplazamiento. La conexión WiFi, el TLS con reconexión y la
suscripción van resueltos.

**En el servidor** (`server/server_skeleton.py`, 6 huecos): cargar las bases de datos,
agregar el buffer de escaneos, k-NN ponderado, gestión del buffer según el estado de
movimiento, verificador de planta con el barómetro y publicación del resultado. El sexto
es la fusión WiFi + PDR por varianza inversa, del tercer hito.

Es exactamente el mismo fichero que se reparte en clase: repositorio y curso llevan la
copia idéntica a propósito, para que no se separen.

```bash
python server/server_skeleton.py --equipo G1 \
    --antenas base_antenas.csv \
    --fingerprints base_fingerprints.csv \
    [--plantas base_plantas.csv]
```

El fundamento de cada método está en `modelo-propagacion.md`, y el formato de los
mensajes en `protocolo-mqtt.md`. La idea es que el alumnado pueda hacerlo leyendo la
documentación, no adivinando.

**El identificador tiene que ser el mismo en las tres piezas**: el `GRUPO` del firmware,
el `--equipo` del servidor y lo que se escribe en el visualizador al abrirlo. Si no
coinciden no salta ningún error, simplemente cada uno habla por su canal y no se ve nada.
Es el fallo más frecuente el primer día, y conviene avisarlo antes de que ocurra.

Si un equipo prefiere montar su propio sistema, con publicar en
`indoor_geolocation/<equipo>/location/result` con el formato documentado ya se ve en
el 3D.

---

## 8. Montar el curso

Las siete prácticas de `practicas/` preparan cada pieza y se pueden dar sueltas. El orden
es acumulativo: B2 va de datos crudos del acelerómetro al contador de pasos, B3 añade el
barómetro para la planta, B5 el acondicionamiento de señal, B6 el fingerprinting y B7 la
fusión.

El proyecto corre en paralelo con tres hitos: recolección, procesado y demostración en
vivo. Enunciado y calendario en `practicas/Proyecto_enunciado_y_calendario.pdf`; los
criterios y la hoja de evaluación, en `practicas/guias/`.

Dos decisiones del diseño original que merece la pena conservar:

**La defensa se hace por separado con cada miembro del equipo**, con preguntas sobre
partes distintas del sistema. Es lo que evita que uno arrastre al otro.

**La demostración es en vivo, con el sistema funcionando** mientras su autor recorre el
edificio. Elimina de raíz la copia de entregas entre cursos y entre equipos.

---

## 9. Cuando algo no va

| Síntoma | Causa casi siempre |
|---|---|
| El visualizador se queda en negro | Has abierto el HTML como fichero. Ábrelo desde el servidor, en `localhost:8000` |
| «No existe config.yaml» | Falta el `cp config.example.yaml config.yaml` |
| Una planta sale de color liso | Su plano no se encontró. El servidor te dice en el arranque qué ruta esperaba |
| El marcador no aparece | El grupo del visualizador no coincide con el del que publica |
| El marcador aparece fuera del edificio | `metros_por_pixel` u `origen_px` mal calibrados, o falta `coord_offset` |
| El navegador no conecta al broker | Estás usando el 8883. El navegador necesita WebSocket: 8884 |
| El M5 no aparece como puerto serie | Falta el driver del CH9102 |
| El botón de cobertura no está | Ninguna planta declara `heatmap:`. Es lo normal si no la has generado |

---

## 10. Antes de repartir nada

**No pongas tus credenciales en el material del alumnado.** Los esqueletos vienen con
marcadores `___MQTT_USER___` a propósito: reparte los datos del broker por el aula
virtual, no dentro del código. Un fichero con la contraseña en claro acaba en un
repositorio público de un alumno tarde o temprano.

**Usa una cuenta de broker del aula**, distinta de la tuya personal y con permisos
limitados a los canales del curso. Rótala al acabar.

**Las capturas WiFi son datos del edificio.** El `.gitignore` ya excluye `wifi_log_*.csv`
por eso. Los BSSID identifican puntos de acceso concretos y su posición.

**Los planos** pueden estar sujetos a las normas de tu centro. Los de ejemplo se publican
con permiso; los tuyos decídelo tú.

---

## 11. Licencias

El código es MIT (`LICENSE`) y el material docente y los planos, CC BY 4.0
(`LICENSE-docs`). Puedes usar, adaptar y redistribuir ambos, también con fines
comerciales, citando la fuente. Cómo citarlo, en `CITATION.cff`.

Si adaptas las prácticas a tu centro, la atribución basta: no hace falta pedir permiso ni
compartir tus cambios.
