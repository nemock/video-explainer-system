# Bundled deck fonts

Variable woff2 files consumed by `deckbuild._font_css` when a theme declares a
`fonts` field (see `themes.py`; the `founder` theme → Fraunces + Inter, the `fwf`
theme → Archivo). They are copied into each project's `deck/fonts/` and referenced
via `@font-face`, so the captured render uses real glyphs with no network dependency
at render time.

| File | Family | Source | License |
|---|---|---|---|
| `fraunces-wght-normal.woff2` | Fraunces (variable wght) | [@fontsource/fraunces](https://fontsource.org/fonts/fraunces) → Undercase Type | SIL Open Font License 1.1 |
| `fraunces-wght-italic.woff2` | Fraunces italic (variable wght) | same | SIL OFL 1.1 |
| `inter-wght-normal.woff2` | Inter (variable wght) | [@fontsource/inter](https://fontsource.org/fonts/inter) → Rasmus Andersson | SIL OFL 1.1 |
| `archivo-wdth-wght-normal.woff2` | Archivo (variable **wght + wdth**) | [@fontsource-variable/archivo](https://fontsource.org/fonts/archivo) `standard` axes file → Omnibus-Type | SIL OFL 1.1 |

Fraunces, Inter, and Archivo are all licensed under the SIL Open Font License 1.1, which
permits bundling/redistribution. Full license text: https://openfontlicense.org/

Note: Archivo carries a real **width** axis (62–125), so the `fwf` theme renders a genuine
condensed cut via `font-stretch` — used because Montserrat (the FWF kit's face) has no width
axis. `deckbuild.FONT_STRETCH` advertises the axis range in the `@font-face`.
