# Arquitectura

El sistema tiene cuatro piezas: el dispositivo, el broker, el servidor y el
visualizador.

## Dispositivo

Un M5StickC Plus 2 por equipo. Escanea las redes WiFi visibles y anota, de cada una,
su identificador (BSSID) y la potencia recibida (RSSI, en dBm). Lee además la IMU y el
barómetro. Con la IMU clasifica el estado de movimiento (quieto, moviéndose, rápido),
que después decide qué hacer con las medidas WiFi. Publica todo por MQTT.

## Broker

Un broker MQTT sobre TLS, con un canal por equipo. Puede ser una cuenta gratuita de un
servicio en la nube o un Mosquitto propio. No hace falta infraestructura del centro.

## Servidor

Un proceso Python por equipo, suscrito al canal de datos de ese equipo. Con las
medidas y el mapa de radio que el equipo levantó en la primera fase, estima la
posición y la publica en el canal de resultado. Combina la localización WiFi con la
navegación inercial cuando el usuario se mueve.

## Visualizador

Una página web (Three.js) que reconstruye las plantas del edificio y se suscribe al
canal de resultado por WebSocket seguro. Pinta el marcador y la trayectoria. Corre en
el navegador de cada alumno; el servidor HTTP solo entrega la página, los planos y la
configuración.

## Flujos

- Práctica: dispositivo -> broker -> servidor -> broker -> visualizador.
- Demostración sin hardware: simulador -> broker -> visualizador.

Los nombres de los canales están en `protocolo-mqtt.md`.
