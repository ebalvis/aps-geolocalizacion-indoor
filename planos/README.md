# Planos

El sistema de coordenadas de toda la práctica se apoya en los planos del edificio, con
un origen común a todas las plantas y una escala conocida.

## Qué hay aquí

| Fichero | Qué es |
|---|---|
| `andar1.png`, `andar2.png`, `andar3.png` | plantas 1ª, 2ª y 3ª del Politécnico de Ourense. Son los que declara `config.example.yaml`, así que el visualizador arranca con ellos sin configurar nada |
| `plano_grid_3P.jpg` | la 3ª planta con la cuadrícula de 5 m superpuesta y el origen marcado. Es el que se reparte al alumnado para situar los puntos de medida |

Los tres PNG miden unos 3.055 × 1.515 px, con escala 0,0312 m/px y origen de coordenadas
en el píxel [1407, 1492], que corresponde a la escalera E4.

Se publican bajo licencia CC BY 4.0 (ver `../LICENSE-docs`).

## Para tu edificio

1. Consigue los planos de cada planta en PNG, JPG o WEBP y déjalos en esta carpeta. El
   nombre da igual: la ruta se declara en `config.yaml`.
2. Declara una entrada por planta en `plantas:`, apuntando `imagen:` a cada fichero. No
   hay número fijo de plantas ni nombres obligatorios.
3. **Calibra la escala.** Mide sobre la imagen, en píxeles, una distancia real que
   conozcas, por ejemplo un pasillo o la separación entre dos pilares, y calcula:

   ```
   metros_por_pixel = distancia_real_m / distancia_medida_px
   ```

4. **Fija el origen.** Elige un punto reconocible en todas las plantas, como una escalera
   o un hueco de ascensor, y anota su píxel `[columna, fila]` en `origen_px`. Que sea el
   mismo punto en todas ellas es lo que permite comparar posiciones entre plantas.
5. Si al verlo en 3D el plano sale espejado respecto a cómo mides, invierte el eje con
   `simetria_x` o `simetria_y` en vez de retocar la imagen.

Los controles y el resto del procedimiento están en `../visualizer/README.md`.
