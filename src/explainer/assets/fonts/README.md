# Bundled deck fonts

Variable woff2 files consumed by `deckbuild._font_css` when a theme declares a
`fonts` field (see `themes.py`; currently the `founder` theme → Fraunces + Inter).
They are copied into each project's `deck/fonts/` and referenced via `@font-face`,
so the captured render uses real glyphs with no network dependency at render time.

| File | Family | Source | License |
|---|---|---|---|
| `fraunces-wght-normal.woff2` | Fraunces (variable wght) | [@fontsource/fraunces](https://fontsource.org/fonts/fraunces) → Undercase Type | SIL Open Font License 1.1 |
| `fraunces-wght-italic.woff2` | Fraunces italic (variable wght) | same | SIL OFL 1.1 |
| `inter-wght-normal.woff2` | Inter (variable wght) | [@fontsource/inter](https://fontsource.org/fonts/inter) → Rasmus Andersson | SIL OFL 1.1 |

Both Fraunces and Inter are licensed under the SIL Open Font License 1.1, which permits
bundling/redistribution. Full license text: https://openfontlicense.org/
