# Proceso para pulir un fade (degradé) en una foto

Proceso con el que salió el pulido final de la foto 2. El script es `pulir_fade.py`.

```bash
pip install numpy scipy opencv-python-headless
python fade/pulir_fade.py foto.jpg resultado
```

Genera `resultado.png` y estas imágenes de control:
- `resultado_cmp.png` / `resultado_full.png`: antes y después;
- `resultado_temple.png`: la sien;
- `resultado_dbg.png`: la línea de peso (en rojo la limpia, en verde la real) y las zonas protegidas (en azul).

## Reglas (lo que funcionó y lo que no)

1. **Respetar el corte.** La línea de peso original es el techo del fade: se mantiene su
   altura y solo se emprolija su forma (sin picos ni escalones). Si es oblicua, sigue oblicua.
2. **Cambio chico.** Los tonos y el largo del degradé son los de la foto, solo que
   parejos. Nada de inventar un degradé nuevo, más largo ni más oscuro.
3. **La oscuridad sale de los pelitos.** Un fade real no tiene sombreados lisos: el oscuro es
   la cantidad, el largo y los grupos de pelitos. Por eso se permite oscurecer muy poco
   (`DMAX`); cerca de la línea un poco más, para que el negro conecte.
4. **Sin claridades de la nada.** No se aclara cerca de la oreja, la patilla ni la línea
   oscura de atrás, porque ahí hay sombras naturales. En el resto se aclara como máximo
   `BMAX` (10). Controlar siempre el mapa de diferencias contra el original.
5. **Piel real.** No se retoca: poros, manchitas e imperfecciones se quedan.
6. **No tocar:** la oreja, la patilla, la línea oscura de atrás de la oreja ni la punta del
   flequillo.
7. **Sien:** borde limpio en forma de "C" desde el flequillo hasta la patilla.
8. **Borde del pelo natural.** Puntas desparejas que caen apenas sobre el fade, nunca una
   línea "de regla".

## Pasos del script

1. **Línea de peso.** Detecta el borde real del pelo largo (luminancia > 75), ajusta una
   curva suave (spline) a la misma altura y deja el frente del flequillo como está.
2. **Warp.** Desplaza verticalmente el pelo y el fade, unos pocos px, para que el borde real
   caiga justo sobre la curva limpia. La textura sigue siendo la real.
3. **Perfil propio.** Mide la mediana del degradé de la foto (tono en función de la
   distancia a la línea) en la zona más limpia, detrás de la oreja. La hace monotónica
   y suaviza el primer tramo (`GAMMA` 1.3) para conectar el negro.
4. **Emparejado.** Lleva la baja frecuencia de cada zona a ese perfil, ajustado a la piel
   local de cada columna, con el oscurecido limitado (`DMAX`) y el aclarado limitado
   (`BMAX`, 0 cerca de las zonas protegidas). La textura fina de pelitos y poros queda
   intacta.
5. **Máscaras.** Zonas protegidas (oreja, patilla, línea de atrás), la cara delante de la
   "C" y puntas de pelo desparejas sobre el borde.
6. **Puntas.** Neutraliza un poco las puntas marrones justo arriba de la línea (`TIPW`).

## Parámetros (variables de entorno)

| Variable | Por defecto | Qué hace |
|---|---|---|
| `GAMMA` | 1.3 | suavidad de la unión negro → fade (más alto: más conectado) |
| `DMAX` | 12 | cuánto se puede oscurecer fuera de la zona de unión |
| `BMAX` | 10 | cuánto se puede aclarar (0 cerca de oreja, patilla y línea) |
| `TIPW` | 0.35 | cuánto se oscurecen las puntas del pelo en el borde |

## Para usarlo con otra foto

La geometría está marcada a mano para la foto 2 (1004×1296 px). Para otra foto hay que
volver a ubicar, en coordenadas de esa imagen:
- los polígonos `ear`, `sideburn` y `stripe`;
- la curva `carc` de la sien;
- `XL` y `XR` (inicio y fin del fade);
- `Lb`, el largo del fade por columna, hasta la oreja, la patilla o la línea;
- los rangos de búsqueda de la línea (filas 520–800) y de columnas del perfil (525–700).

Para ubicarlos sirve dibujar una grilla con coordenadas sobre la foto y revisar
`resultado_dbg.png`.

## Lo que se probó y se descartó

- **Degradé sintético largo y oscuro** (según la referencia): quedó muy estirado y
  con un sombreado plano.
- **Pelitos generados por código:** parecían salpicaduras o ruido.
- **Textura copiada de una foto de referencia** (mapa de pelito y piel de otro fade): se
  ve real, pero es un cambio grande. Sirve solo si se quiere rehacer el fade entero.

---

# Estilo TAPER fade (degradé solo en patilla y nuca)

Script: `pulir_taper.py`, con el perfil de tonos `taper_ref_profile.npy`. Salió de la foto 4.

```bash
python fade/pulir_taper.py foto.png resultado
```

Genera `resultado.png` y estas imágenes de control: `_cmp` y `_full` (antes y después),
`_diff` (mapa de cambios) y `_dbg` (zonas y contornos).

## Reglas del taper

1. **Solo patilla y nuca.** Arriba de la oreja no se toca. No es un drop fade.
2. **Pulido = más blanco que negro.** Negro solo en una franja corta pegada al pelo largo,
   un gris corto y la mayor parte del fade clara, con entrada de luz alrededor de la oreja.
   Si el degradé queda gris parejo, está mal.
3. **Tres tonos: negro, gris y blanco,** siempre en ese orden. Varía la altura según el
   corte, pero el reparto es siempre el mismo.
4. **El tono sale de la cantidad de pelitos.** Los pelitos reales se reacomodan en vertical
   para que cada tono caiga a su altura, con un estirado máximo de 1,7×. No se generan
   pelos, no se rellenan puntitos de negro y no se pinta sombra ni velo de color: todo eso
   se ve artificial.
5. **Contornos oscuritos.** El borde delantero de la patilla, la línea lateral de la nuca,
   la oreja y la silueta del cuello conservan su oscuridad natural: no se aclaran ni se
   oscurecen.
6. **Sin líneas fantasma.** La edición entra de a poco:
   - arriba, a lo largo de una franja ancha;
   - hacia la cara y el cuello, en los últimos 14 px antes del borde.

   En la franja de arriba no se oscurece nada. Si la edición corta de golpe o oscurece
   arriba, aparece una "línea de peso transparente" o una banda oscura en la nuca.
7. **Manchas.** Se emparejan con un ajuste multiplicativo suave, que mantiene la textura:
   oscurece como máximo 8 (`DK`) y aclara como máximo 14 (`LT`), solo en la parte baja.

## Pasos del script

1. **Geometría.** Oreja, cara (delante de la patilla), cuello (delante de la línea de la
   nuca), pared del fondo y las dos zonas: A (patilla) y B (nuca), cada una con su borde
   de arriba (`topA`/`topB`) y de abajo (`botA`/`botB`).
2. **Borde de la patilla.** Curva suave a la misma altura; el pelo se desplaza unos pocos px.
3. **Perfil propio de cada zona.** Mediana del tono según la profundidad normalizada `t`
   (0 = borde de arriba, 1 = piel).
4. **Perfil objetivo.** La curva de la referencia de taper en versión "pulida" (más blanca),
   entre el negro (`HB`) y la piel de cada columna (`SKB`).
5. **Re-mapeo vertical.** Para cada profundidad busca en el fade real dónde vive ese tono y
   trae esos pelitos. Es un mapeo 1-D por zona, con la pendiente limitada entre 0,6 y 1,7
   y los extremos suaves.
6. **Emparejado suave** de manchas (modo `A2`).
7. **Máscara final.** Entrada suave arriba y hacia la cara y el cuello; contornos, oreja y
   pared quedan intactos.

## Parámetros

| Variable | Por defecto | Qué hace |
|---|---|---|
| `WHITE` | 1 | perfil pulido, más blanco (0 = perfil tal cual de la referencia) |
| `HB` | 40 | nivel del negro |
| `SKB` | 1.04 | brillo del "blanco" respecto a la piel real |
| `DK` / `LT` | 8 / 14 | cuánto se puede oscurecer / aclarar al emparejar manchas |
| `MODE` | A2 | A2 = solo re-mapeo + emparejado suave (B/C = variantes descartadas) |

## Descartado en taper

- **Rampa lineal de oscuro a piel:** queda gris plano y monótono.
- **Rellenar los pelitos existentes de negro:** parece estampado de leopardo.
- **Oscurecer con color:** deja un velo gris plano.
