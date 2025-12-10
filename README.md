## Icon Mapping Table

This project provides a visual comparison table to remap Material icons—specifically many common icons used in Home Assistant—to visually similar alternatives in other popular icon sets. Open `index.html` in a browser to see side-by-side previews powered by the Iconify CDN. The `mappings` array in the script lists each Material icon and its suggested equivalents; edit it to refine matches or add notes.

Icon sets used on this page:
- **Material Design Icons (MDI)** — prefix `mdi:` — https://icon-sets.iconify.design/mdi/
- **Fluent UI System Icons** — prefix `fluent:` — https://icon-sets.iconify.design/fluent/
- **Tabler Icons** — prefix `tabler:` — https://icon-sets.iconify.design/tabler/
- **Phosphor Icons** — prefix `ph:` — https://icon-sets.iconify.design/ph/
- Icons are loaded via **Iconify CDN** — https://iconify.design/

Sources (browsing pages):
- Material Symbols: https://icon-sets.iconify.design/material-symbols/
- Fluent UI: https://icon-sets.iconify.design/fluent/
- Tabler: https://icon-sets.iconify.design/tabler/
- Phosphor: https://icon-sets.iconify.design/ph/

Optional automation: export SVGs and compute visual similarity (for example, using DINOv3 embeddings: https://github.com/facebookresearch/dinov3) to propose matches before curating them in `index.html`.

