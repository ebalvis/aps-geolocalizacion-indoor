# Registro de cambios

El formato sigue el criterio de versionado semántico.

## [1.0.0] - 2026-07-25

Primera versión pública. Corresponde al artículo y a la presentación de EDUTRENDS
2026, para el curso 2026-2027.

### Incluye

- Firmware para M5StickC Plus 2 (MicroPython, UIFlow 2.0): registrador WiFi por
  puntos (herramienta completa, con descarga por WiFi, punto de acceso y USB) y
  esqueleto de cliente en tiempo real con 8 TODO, el último de navegación
  inercial (PDR).
- Esqueleto del servidor de estimación en Python con 6 TODO: agregación de
  escaneos, k-NN y fusión WiFi con odometría.
- Los dos esqueletos son el mismo fichero que se reparte en el curso, sin
  variantes: un solo texto para el alumnado y para quien clone el repositorio.
- Simulador que publica rutas sin hardware, para probar el visualizador.
- Visualizador 3D del edificio en Three.js con su servidor HTTP y las texturas de
  cobertura simuladas. El edificio se define entero en `config.yaml`: número de
  plantas, planos, alturas y dimensiones. No hay nada cableado en el código, así
  que se adapta a cualquier edificio sin tocar el HTML ni el servidor.
- Documentación: arquitectura, modelo de propagación, protocolo MQTT y guía de
  MicroPython. Prácticas de laboratorio B1-B7 y proyecto integrador en PDF.
- Planos de las tres plantas del edificio de ejemplo, más el de la planta tercera
  con la cuadrícula métrica y el origen de coordenadas marcado.

### Notas

- El mapa de cobertura es una simulación del modelo de propagación log-distancia,
  no una interpolación de medidas.
- **Los resultados publicados son solo de WiFi.** El sistema de referencia estima
  la posición a partir de los escaneos, y usa la IMU como filtro temporal: acumula
  medidas cuando el usuario está quieto y las descarta cuando se mueve.
- La navegación inercial (PDR) está en esta versión como **material docente y
  ejercicio**: las prácticas B4 y B7 la explican, y el `TODO 8` del cliente pide
  implementarla. Lo que no hay en v1 es PDR resuelto en el sistema de referencia
  ni resultados medidos con él. Eso es la versión 2.

## [Sin publicar] - versión 2

La v2 no añade temario: convierte en sistema de referencia lo que la v1 deja como
ejercicio, y publica sus resultados. Especificación de lo que tiene que traer:

### Estimación inercial

- Detección de pasos por umbral adaptativo sobre la magnitud del acelerómetro,
  con periodo refractario para no contar dobles.
- Longitud de zancada por modelo dependiente de la frecuencia de paso, calibrada
  por usuario sobre un recorrido de longitud conocida.
- Rumbo por integración del giroscopio con corrección de deriva.
- Remuestreo a intervalo uniforme antes de filtrar: el ESP32 no entrega las
  muestras a periodo constante y hacerlo sobre el eje crudo introduce un error
  que se confunde con deriva del sensor.

### Fusión

- Combinación del fix WiFi con la predicción PDR por ponderación de varianza
  inversa, con la incertidumbre del PDR creciendo por paso desde la última
  corrección.
- Cierre del lazo: el resultado fusionado realimenta la predicción siguiente.

### Validación

- Repetir la comparación de métodos sobre los mismos 20 puntos de referencia,
  añadiendo la fusión como cuarto método.
- Informar del error medio, del percentil 95 y del acierto de planta, en las
  mismas condiciones que la v1, para que las cifras sean comparables.

### Compatibilidad

- El formato de los mensajes no cambia: el bloque `imu_pdr` ya existe en v1 y
  viaja con ceros mientras no se implemente.
- Los canales MQTT no cambian.
