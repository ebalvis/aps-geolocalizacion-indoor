# Servidor de estimación (Python)

Recibe por MQTT los escaneos de un equipo, estima la posición y la vuelve a publicar.
Es el núcleo de tratamiento de señal de la segunda y tercera fase de la práctica.

## Requisitos

```bash
pip install -r ../requirements.txt
cp ../.env.example ../.env    # y rellena las credenciales del broker
```

El servidor lee `MQTT_HOST`, `MQTT_USER` y `MQTT_PASS` de `.env`. No hay credenciales
en el código.

## Uso

```bash
python server_skeleton.py --equipo G1 \
    --antenas base_antenas.csv \
    --fingerprints base_fingerprints.csv \
    [--plantas base_plantas.csv]
```

Los CSV los genera cada equipo en la primera fase, al levantar su mapa de radio.

El identificador de `--equipo` es el que forma los canales MQTT, así que tiene que ser
**el mismo** que lleva el firmware en `GRUPO` y el que se escribe en el visualizador al
abrirlo. Si no coinciden no hay error: cada pieza habla por su canal y no se ve nada.

    indoor_geolocation/<equipo>/location/data      lo que escucha
    indoor_geolocation/<equipo>/location/result    lo que publica

## Qué tienes que completar

Seis partes marcadas como `TODO`:

1. Carga de las bases de datos (antenas, huellas, plantas).
2. Agregación del buffer de escaneos y k-NN ponderado.
3. Gestión del buffer según el estado de movimiento (filtrado temporal con la IMU).
4. Verificador de planta con el barómetro (opcional).
5. Publicación del resultado.
6. Fusión WiFi + PDR por varianza inversa.

El fundamento de cada método está en `../docs/modelo-propagacion.md`. El formato de
los mensajes, en `../docs/protocolo-mqtt.md`.
