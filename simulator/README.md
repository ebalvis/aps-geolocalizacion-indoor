# Simulador de posiciones

Publica por MQTT una ruta simulada que recorre los pasillos del edificio, sin necesidad
de hardware. Sirve para probar el visualizador y para las demostraciones en clase.

## Uso

```bash
pip install -r ../requirements.txt
cp ../config.example.yaml ../config.yaml
cp ../.env.example ../.env    # y rellena las credenciales del broker
python test_mqtt_g0.py
```

Publica en `indoor_geolocation/G0/location/result` cada dos segundos. Cambia el grupo
con la variable de entorno `G0_GROUP`.

Con el visualizador abierto (ver `../visualizer/`) e introduciendo el mismo grupo, el
marcador recorre la ruta y va cambiando de planta cada cierto tiempo.

## Adaptarlo

Nada está cableado en el código. La ruta, la velocidad, el periodo y la planta de
arranque salen de la sección `simulador:` de `config.yaml`, y las plantas por las que
va rotando, de `plantas:`.

```yaml
simulador:
  planta_inicial: "1P"
  velocidad_ms: 1.2
  periodo_s: 2.0
  ruta:
    - [44.0, 32.3]     # coordenadas en metros, mismo origen que los planos
    - [30.0, 32.3]
    # ...
```

La ruta se recorre de ida y vuelta en bucle, con un pequeño ruido lateral que imita el
caminar y pausas aleatorias. Con dos puntos ya funciona.

Si no hay `config.yaml`, el simulador avisa y usa un cuadrado de 20 m sobre una sola
planta, que basta para comprobar que la cadena MQTT llega al visualizador.

## Formato del mensaje

El que describe `../docs/protocolo-mqtt.md`. La función `siguiente_mensaje()` está
separada de la conexión a propósito, para poder inspeccionar lo que se publicaría sin
necesidad de un broker.
