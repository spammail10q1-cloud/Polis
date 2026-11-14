# POLIS design direction

POLIS is a clinical research instrument, not a wellness dashboard. The interface should read like a well-made scientific report: quiet surfaces, precise rules, readable type, and one clear place for the eye to land.

## Dials

- **Energy: 2.** Restrained. No page-wide gradients, glow fields, noise overlays or decorative grids. A single border or rule carries structure.
- **Rhythm: 2.** Calm and repeating. Panels share one radius, one border weight and one padding scale. Density comes from information, not ornament.
- **Motion: 1.** One short entrance fade and functional loading indicators. No perpetual scanning, pulsing, breathing, rotating or marquee motion.

## Visual identity

**Palette.** Warm near-black graphite (`#0b0e0c`) with bone text (`#eef1ea`). One signal cyan (`#7dded6`) marks the current selection or primary action. Amber means review or uncertainty. Violet means experimental or modeled. Mint means in-range. Red is reserved for safety and destructive actions. A single accent appears at a time; semantic colours are never used as decoration.

**Type.** IBM Plex Sans for interface text and narrative, because it was designed for technical and scientific communication and stays legible at small sizes. IBM Plex Mono for measurements, units, codes and timestamps, because tabular numbers and fixed-width codes need stable alignment. Newsreader for display headlines, because an editorial serif gives the research record a human, considered voice instead of a console cosplay. Body text is 13 to 15 pixels; metadata is never smaller than 11 pixels.

**Form.** Two-pixel radius, one-pixel borders, flat fills. No shadows, glass, blur, capsule pills or letter-spaced uppercase eyebrows. Panels are sheets of paper on a desk, not floating glass cards.

## Component rules

- **Panels:** `--color-panel` fill, one `--color-line` border, no shadow. A panel that needs emphasis changes its border colour, not its background.
- **Headers:** a 12-pixel sentence-case eyebrow, a 16 to 20-pixel sans title, and a 13-pixel muted description. No uppercase tracking.
- **Controls:** 44-pixel touch target on coarse pointers, 2-pixel visible focus ring, 16-pixel form text to prevent mobile zoom.
- **Status:** colour plus a written label. A dot alone is never the only signal. Static dots are acceptable in legends; animated dots are not.
- **Evidence:** badges use plain language and semantic colour. Model estimates are never styled like established clinical facts.
- **Motion:** `prefers-reduced-motion` removes entrance movement and all decorative animation. Loading spinners remain because they communicate state.
- **Empty and error states:** every panel that can be empty says what is missing and what the user can do next. Errors name the failed action, not just "something went wrong".
- **Mobile:** the layout reflows rather than shrinking. Sideways scrolling is limited to charts and tables that need it. Navigation is a full-height sheet, not a compressed desktop rail.

## Deliberate choices

- The anatomical illustration stays. It is a licensed, attributed navigation model (DBCLS, CC BY 4.0), and it is explicitly labelled as navigation, not a scan. It earns its place because users need to locate a biological system quickly.
- The dark palette stays because the product is used for concentrated reading and because the original brief asked for a clinical research instrument. It is warm and flat rather than blue-black and glowing.
- Data density stays. POLIS is a record, and hiding evidence behind progressive disclosure would undermine its scientific honesty. Density is made readable through hierarchy, not by shrinking type.
- No overall health score exists. The design must not invent one through a hero number or gauge.

## Anti-slop boundaries

No em dashes. No fabricated statistics, quotes or clinical claims. No dead controls. No placeholder sections presented as finished. No icon chosen because it looks clever; icons must name an action or a known concept. No decorative arrows. No animated status dots. No uppercase letter-spaced labels. No generic blue-purple gradients.
