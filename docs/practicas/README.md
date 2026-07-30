# Prácticas de laboratorio (B1–B7) y proyecto

Estas son las prácticas del curso, que preparan cada pieza del proyecto integrador.
Cada bloque introduce un sensor o una técnica y produce algo que después se usa en
el sistema de geolocalización. Se publican bajo licencia CC BY 4.0.

| Bloque | Práctica | Aporta al proyecto |
|---|---|---|
| B1 | `B1_ecosistema_aiot.pdf` | M5StickC, WiFi y MQTT: dispositivo y conectividad. |
| B2 | `B2_imu_acelerometro.pdf` | IMU: de los datos crudos del acelerómetro a la detección de pasos. |
| B3 | `B3_sensores_ambientales.pdf` | ENV III (presión): identificación de la planta. |
| B4 | `B4_pedometro_trayectoria.pdf` (+ `B4_guia_referencia_python.pdf`) | Giroscopio, rumbo y navegación por estima (PDR). |
| B5 | `B5_espectrograma_filtros.pdf` | Espectrograma (STFT) y filtros: acondicionamiento de señal. |
| B6 | `B6_tiempo_real_fingerprinting.pdf` | Streaming MQTT, RSSI y localización por huellas (k-NN). |
| B7 | `B7_pasos_giros_fusion.pdf` | PDR y fusión WiFi + inercial: integración final. |

## Proyecto integrador

- `Proyecto_enunciado.pdf`: enunciado del proyecto y sus hitos.
- `Proyecto_calendario.pdf`: calendario de sesiones y entregas.
- `guias/H1_toma_de_datos.pdf`, `guias/H2_geolocalizacion_basica.pdf`: los dos
  primeros hitos paso a paso.
- `guias/criterios_evaluacion.pdf`: qué se evalúa y con qué peso.
- `guias/guia_plataforma.pdf`: uso de la plataforma y el visualizador.

La hoja de evaluación de la defensa, con el banco de preguntas y sus respuestas
modelo, es material del profesorado y no se publica aquí. Está descrita en
`../guia-profesor.md`.

## Cómo encaja con el código

Las prácticas explican los fundamentos; el código de este repositorio los pone en
funcionamiento. La programación del M5 se apoya en `../micropython-m5.md`. El
registrador WiFi (`../../firmware/app1_wifi_logger/`) es la herramienta del hito 1;
el envío por MQTT (`../../firmware/app2_mqtt_sender/`) y el servidor
(`../../server/`) son el hito 2; la fusión y la demostración, el hito 3.
