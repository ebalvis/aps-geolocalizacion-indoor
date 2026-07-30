# Firmware del M5StickC

Dos aplicaciones para el dispositivo de cada equipo:

| Carpeta | Qué es | Estado |
|---|---|---|
| `app1_wifi_logger/` | Registrador de huellas WiFi: escanea las redes por puntos, las guarda en la flash y las sirve para descargar. | Completa, probada en dispositivo. |
| `app2_mqtt_sender/` | Cliente en tiempo real: envía WiFi, presión y estado de movimiento por MQTT, y recibe la posición estimada. | Esqueleto: el alumnado completa 8 `TODO`. |

Es el mismo `m5stick_skeleton.py` que se reparte en clase. Repositorio y curso llevan el
fichero idéntico, byte a byte, a propósito.

## Hardware y firmware

- M5StickC Plus 2 (ESP32, pantalla 240×135, IMU MPU6886). El registrador funciona
  también en el Plus 1.1.
- Unidad ENV III (SHT30 + QMP6988) en el puerto Grove, I2C en `SCL=GPIO33, SDA=GPIO32`.
  El barómetro sirve para identificar la planta. Opcional para la App 1, necesario para
  el verificador de planta de la App 2.
- MicroPython sobre UIFlow 2.0. Validado sobre MicroPython 1.25.0.

## Cómo cargar el código

1. Instala UIFlow 2.0 en el M5StickC con M5Burner y ponlo en modo USB/MicroPython.
2. Copia el `.py` al dispositivo con Thonny, el IDE web de UIFlow o `mpremote`:

   ```bash
   python -m mpremote connect COM11 fs cp wifi_logger.py :wifi_logger.py
   ```

   El puerto es el del puente serie: en Windows aparece como `USB-Enhanced-SERIAL
   CH9102`, en Linux suele ser `/dev/ttyUSB0`.

3. Para que arranque solo al encender, guárdalo como `main.py` en la flash.

La App 1 solo necesita configuración si vas a usar la descarga por «WiFi local». La App 2
necesita que rellenes el TODO 1 con tu red, tu broker y tu identificador de equipo.

## App 1: registrador WiFi

Cada grabación es un **punto de referencia**: te colocas, pulsas A, el M5 escanea cada
tres segundos, vuelves a pulsar A y paras. El número de punto sube solo y se ve en
pantalla. Todo se acumula en `/flash/wifi_log.csv`, con el número de punto en cada fila,
y al reiniciar continúa por donde iba.

| Pantalla | Botón A | Botón B |
|---|---|---|
| Parado | graba el punto siguiente | menú de descarga |
| Grabando | para | — |
| Menú | cambia de opción | elige |

Tres formas de descargar, desde el menú:

- **Punto de acceso**: el M5 crea su propia red `APS-Logger-XXXX` y sirve en
  `http://192.168.4.1`. Funciona en un aula sin red, que es lo habitual.
- **WiFi local**: el M5 se conecta a la red del aula y sirve la misma web.
- **USB por serie**: desde el PC, con `descargar_wifi_log.py` o el `.bat`.

Descarta redes por debajo de −90 dBm y comprueba que quede espacio en flash.

## App 2: cliente en tiempo real

Publica en `indoor_geolocation/<equipo>/location/data` y se suscribe a `.../result`, los
mismos canales que usan el servidor y el visualizador 3D. Detalle del formato en
`../docs/protocolo-mqtt.md`.

Viene resuelto: conexión WiFi, conexión TLS al broker con reconexión automática, lectura
de sensores, el bucle de publicación y la recepción de la posición estimada.

Los ocho `TODO` que completa el alumnado:

1. Configuración: red, broker e identificador de equipo.
2. Lectura de la presión con el QMP6988.
3. Clasificación del estado de movimiento con el acelerómetro.
4. Construcción del mensaje JSON.
5. Publicación en el broker.
6. Tratamiento de la respuesta del servidor.
7. Visualización de la posición recibida.
8. **PDR**: detección de pasos, integración del rumbo con el giroscopio y estimación del
   desplazamiento (Δx, Δy) que viaja en el bloque `imu_pdr`.

El TODO 8 es el que convierte la IMU de filtro temporal en sensor de posición, y es la
base de la fusión WiFi + inercial del tercer hito.

## Mini-guía de MicroPython en el M5

Lo justo para empezar; la API completa está en la documentación de M5Stack y hay más
detalle en `../docs/micropython-m5.md`.

- Arranque: `M5.begin()` una vez y `M5.update()` en el bucle, para leer botones y sensores.
- Pantalla: `M5.Lcd.drawString(texto, x, y)` o etiquetas con
  `Widgets.Label(texto, x, y, escala, color, fondo, fuente)`. Colores en `0xRRGGBB`.
- Botones: `BtnA.wasPressed()` para el clic corto, `BtnA.wasHold()` para mantener.
- IMU: `Imu.getAccel()` devuelve `(ax, ay, az)` en g; `Imu.getGyro()`, la velocidad
  angular en grados por segundo.
- WiFi: `network.WLAN(network.STA_IF)` para escanear o conectar;
  `network.WLAN(network.AP_IF)` para crear un punto de acceso.
- Ficheros: la flash se usa como un disco normal, `open("/flash/archivo.csv", "w")`.
- Texto con formato: usa `"{}".format(valor)`. Las f-strings pueden no estar disponibles
  según la versión del firmware.
- Tiempo: `time.ticks_ms()` y `time.ticks_diff(a, b)` para medir sin desbordamientos.

Las prácticas B1 a B7 explican paso a paso cada sensor y cada técnica.
