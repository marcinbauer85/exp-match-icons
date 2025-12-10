// Project index.ts
// Description: lists icon sets used by the visual mapping table and exports their identifiers.
//
// Icon sets referenced in this project (prefix -> source):
// - mdi:  Material Design Icons (https://icon-sets.iconify.design/mdi/)
// - fluent: Fluent UI System Icons (https://icon-sets.iconify.design/fluent/)
// - tabler: Tabler Icons (https://icon-sets.iconify.design/tabler/)
// - ph: Phosphor Icons (https://icon-sets.iconify.design/ph/)
// Icons are displayed using Iconify (https://iconify.design/) which aggregates these sets.

export const ICON_SETS = [
  { prefix: 'mdi', name: 'Material Design Icons', url: 'https://icon-sets.iconify.design/mdi/' },
  { prefix: 'fluent', name: 'Fluent UI System Icons', url: 'https://icon-sets.iconify.design/fluent/' },
  { prefix: 'tabler', name: 'Tabler Icons', url: 'https://icon-sets.iconify.design/tabler/' },
  { prefix: 'ph', name: 'Phosphor Icons', url: 'https://icon-sets.iconify.design/ph/' },
];

export const DESCRIPTION = `This project compares icons from multiple icon sets (MDI, Fluent, Tabler, Phosphor) using Iconify.`;
