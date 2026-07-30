# Registro de cambios

El formato sigue el criterio de versionado semántico.

## [1.2.0] - 2026-07-31

Documentación y coherencia del sistema. Los resultados publicados no cambian: el
método de estimación es el mismo y la v1.0.0, que es la que cita la comunicación
de EDUTRENDS 2026, sigue intacta.

**Umbral de potencia unificado en −90 dBm.** Las tres piezas filtraban a valores
distintos: el registrador a −95, el cliente a −90 y el servidor a −85, y la guía
del hito 2 pedía −85 mientras el criterio 1 de la evaluación exigía −90. Cada
programa trabajaba con un conjunto distinto de antenas y las métricas no eran
comparables entre equipos. Ahora es `RSSI_MIN = -90` en los tres, declarado como
constante también en el cliente, donde estaba escrito a mano dentro del bucle.
Efecto secundario a tener en cuenta: el registrador ya no guarda las redes entre
−90 y −95 dBm, así que esos datos no se podrán recuperar de una campaña nueva.

**Los documentos siguen la identidad visual de la asignatura.** Los dieciséis
PDF se generan ahora desde HTML con la misma maqueta —Cormorant Garamond y Lora
empotradas, secciones numeradas, tablas y avisos con los componentes del sistema—
en vez de venir de Word, Google Docs o ReportLab con seis tipografías distintas.

- Las guías del hito 1 y del hito 2, los criterios de evaluación, la guía de la
  plataforma y el manual de UIFlow 2, migrados.
- El enunciado y el calendario del proyecto se separan en dos documentos:
  `Proyecto_enunciado.pdf` y `Proyecto_calendario.pdf`. El calendario es apaisado.
- La guía del hito 2 avisa de que el `A = -40` y el `n = 2.2` de su ejemplo son
  los valores genéricos del modelo y hay que calibrarlos, que es lo que evalúa el
  criterio 2.

**Retirado `docs/practicas/guias/hoja_evaluacion.pdf`**, que contenía el banco de
preguntas de la defensa con sus respuestas modelo. Es material del profesorado y
este repositorio es público. Quien adopte el material puede pedirlo por correo.

- Corregido: la guía del profesorado daba por bueno el M5StickC Plus 1.1, pero el
  cliente que programa el alumnado usa la API `M5.Lcd` del Plus 2. Solo el
  registrador funciona en el Plus 1.1.
- Corregido: el visualizador carga Three.js y el cliente MQTT desde CDN cada vez,
  no solo la primera. La guía explica ahora cómo servirlos en local para un aula
  con la red filtrada.
- Dirección de contacto institucional (`ebalvis@uvigo.gal`) en el README y en
  `CITATION.cff`.

## [1.1.1] - 2026-07-30

Solo metadatos: ni el código ni el material cambian. Es la primera versión que
se archiva en Zenodo, y por eso lleva la ficha del depósito completa.

- `.zenodo.json` con los metadatos del depósito: tipo, título, autoría con
  filiación, descripción, palabras clave y licencia.
- Los ORCID de las tres personas autoras, verificados contra el registro
  público, en `.zenodo.json` y en `CITATION.cff`.

## [1.1.0] - 2026-07-29

Añadidos, sin cambios en el sistema ni en los resultados. La versión 1.0.0 se
mantiene intacta porque es la que cita la comunicación de EDUTRENDS 2026.

- `docs/guion-laboratorio.pdf`: guion de conducción de las trece sesiones, con
  qué preparar antes de cada una, en qué se comprueba que ha salido y los fallos
  habituales. Complementa a `docs/guia-profesor.md`, que cubre la adopción.
- Resumen en inglés al principio del README, con el aviso de que el material
  está en castellano.

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
