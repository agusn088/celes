# celes — Herbario de Primavera

Página de sorpresa para el día de la primavera. Un solo archivo, sin build,
sin dependencias: abrís `index.html` en cualquier navegador y anda.

## Cómo personalizarla

Todo lo editable está en el objeto `CONFIG`, al principio del `<script>`
(al final de `index.html`). No hace falta tocar nada más.

| Campo | Qué es |
| --- | --- |
| `nombre` | Cómo se llama ella, o el apodo. Aparece en la portada y en el cierre. |
| `desde` | Fecha en que empezaron, `AAAA-MM-DD`. De acá salen los días, las primaveras y los domingos. |
| `firma` | Cómo firmás la carta. |
| `motivos` | Las fichas del herbario: `especie`, `hallazgo`, `nota`, `mano`. Poné las que quieras. |
| `flores` | Las cuatro flores del jardincito: `nombre` y `texto`. |
| `carta` | Lista de párrafos. Cada string es un renglón de la carta. |
| `fotos` | Lista de `{ src, pie }`. Vacío muestra marcos con instrucciones. |

### Fotos

Copiá las imágenes en la carpeta `fotos/` y listalas:

```js
fotos: [
  { src: "fotos/costa.jpg", pie: "aquel finde en la costa" },
  { src: "fotos/cumple.jpg", pie: "tu cumple, la torta torcida" }
]
```

## Publicarla

**GitHub Pages** — Settings → Pages → Source: la rama de este repo, carpeta `/ (root)`.
Queda en `https://<usuario>.github.io/celes/`.

**Sin internet** — mandale el `index.html` (con la carpeta `fotos/` al lado) y
que lo abra con doble clic.

## Detalles

- Modo claro y oscuro, según el sistema de quien la abra.
- Anda en celular; los pétalos son un canvas liviano que se frena cuando la pestaña no está a la vista.
- Respeta `prefers-reduced-motion`: sin animación, los pétalos quedan quietos.
- Tipografías desde Google Fonts (Young Serif, Karla, Caveat) con fallbacks del sistema.
