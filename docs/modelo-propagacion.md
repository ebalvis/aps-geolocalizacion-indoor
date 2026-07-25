# Modelo de propagación y métodos de localización

## Modelo log-distancia

La potencia recibida de un punto de acceso decae con el logaritmo de la distancia al
emisor:

    RSSI(d) = A - 10 * n * log10(d)

donde `A` es la potencia de referencia a un metro (en dBm) y `n` el exponente de
pérdidas del entorno. En el edificio de ejemplo, calibrados por regresión sobre
medidas propias, salieron valores cercanos a `A = -61 dBm` y `n = 2,2`, coherentes con
un interior de tabiquería ligera. Estos dos parámetros no se dan hechos: cada equipo
los estima con sus datos.

## Métodos de localización

El servidor implementa y compara tres métodos:

- Máxima potencia: asigna la posición del punto de acceso del que se recibe más señal.
  Es la referencia mínima.
- Multilateración: convierte cada RSSI en una distancia con el modelo anterior y
  resuelve la posición por mínimos cuadrados. Necesita al menos tres puntos de acceso.
- Huella de radiofrecuencia (fingerprinting): compara el vector de potencias actual
  con el mapa de radio levantado en la primera fase y estima la posición por k vecinos
  más próximos.

En las condiciones reales de la práctica (mapa de radio poco denso), el método más
simple suele dar el menor error medio. Entender por qué es el objetivo del análisis.

## Fusión de sensores

El barómetro determina la planta, resolviendo la ambigüedad de los puntos de acceso
visibles desde varios pisos. La IMU decide qué hacer con el WiFi: promediar cuando el
usuario está quieto (menos ruido) o descartar cuando se mueve. En el tercer hito, la
localización WiFi se combina con la navegación inercial (PDR) por ponderación de
varianza inversa, para que la posición avance de forma suave entre correcciones.

## Sobre el mapa de cobertura del visualizador

El mapa continuo de cobertura que se ve en el visualizador y en el vídeo de la
comunicación no procede de medidas interpoladas. Es una simulación: se evalúa el
modelo log-distancia de forma radial alrededor de la posición de cada punto de acceso,
se toma en cada punto del plano el AP de mayor potencia y se añade un término de
sombreado log-normal para que la superficie no quede lisa. La localización real que
hace el sistema parte, en cambio, de medidas discretas en los puntos de referencia. El
mapa continuo es solo para visualizar la cobertura, no para localizar. El generador
está en `../visualizer/gen_heatmap_texturas.py`.
