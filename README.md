# Icon Mapping Table

This project provides a visual comparison table to remap Material Design icons—specifically the top-used icons in Home Assistant—to visually similar alternatives in Fluent, Tabler, and Phosphor icon sets. Open `index.html` in a browser to see side-by-side previews powered by Iconify CDN. The `mappings` array in the script lists each Material icon and its suggested equivalents; edit it to refine matches or add notes.

Sources:
- Material Symbols: https://icon-sets.iconify.design/material-symbols/
- Fluent UI: https://icon-sets.iconify.design/fluent/
- Tabler: https://icon-sets.iconify.design/tabler/
- Phosphor: https://icon-sets.iconify.design/ph/

Optional automation: export SVGs and compute visual similarity (e.g., DINOv3 embeddings: https://github.com/facebookresearch/dinov3) to propose matches before curating them in `mapping.html`.

