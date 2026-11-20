# Discord AI Companion — Interface System

Desktop control panel (PySide6) for one person running their own Discord bot.
It should feel like part of Discord itself, not a separate admin tool.

Source of truth for values: `gui/theme.py` (`TOKENS` + QSS) and `gui/widgets.py`.

## Direction
- Discord-native dark UI: the sidebar reads like Discord's channel list, and the status panel reads like Discord's bottom-left user panel.
- One accent, Blurple, used only for primary actions, selection, focus and toggles.
- Status colours follow Discord presence. They mean state, never decoration.
- No emoji in the UI. Tone comes from colour. Glyphs are monochrome: the `#` nav icon, plus SVG chevrons and checkmarks.

## Surfaces (lightness steps only, one hue)
| Token | Value | Use |
|---|---|---|
| BASE | #1e1f22 | window, sidebar, status bar |
| CARD | #2b2d31 | cards, status panel, dropdown popups |
| RAISED | #35373c | hover, disabled buttons |
| SELECTED | #404249 | selected nav item, pressed button |
| INSET | #1e1f22 | inputs and wells inside cards |
| WELL | #111214 | inputs inside an inset well, menus, tooltips |
| HAIRLINE | rgba(255,255,255,0.06) | sidebar edge, header and status bar dividers |

Text: TEXT #dbdee1 · TEXT_STRONG #f2f3f5 · TEXT_MUTED #949ba4 · TEXT_FAINT #6d6f78.
Accent: BLURPLE #5865f2 (hover #4752c4, pressed #3c45a5). Danger #da373c. Success #23a55a.
Presence: online #23a55a · connecting/stopping #f0b232 · error #f23f43 · offline #80848e.

## Depth
- Surface shifts only. Cards have no border and no shadow.
- Hairlines only between the big regions (sidebar, header, status bar).
- Inputs sink below their parent surface: INSET on a card, WELL inside an inset.
- Never put a #35373c solid border around cards, tables or lists. That was the old look.

## Spacing (4px base)
- Page margins 20 · gap between cards 16 · splitter handle 16.
- Card padding 16 (top 14) · header-to-body gap 12 · body item spacing 10.
- Inset wells: 10–12 inner margins.

## Type (Segoe UI, 13px base)
- Card header: 12px / 700 / TEXT_MUTED / uppercase / +0.4px tracking.
- Sidebar header: 15px / 600 / TEXT_STRONG. Sidebar section: 11px / 700 / muted.
- Nav item: 14px / 500, muted until hovered or selected.
- Buttons 13px / 500. Muted helper text 12px. Logs use Consolas 12px.
- Hierarchy comes from weight and colour first, size second.

## Components
- **Card** (`gui.widgets.Card`): `Card("Title")`; add content to `card.body` (a QVBoxLayout). For grids: `grid = QGridLayout(); card.body.addLayout(grid)` plus `grid.setRowStretch(last+1, 1)` so the rows stay packed at the top. Radius 8. `setTitle()` works like QGroupBox's.
- **StatusLabel** (`gui.widgets.StatusLabel`): use for every feedback message. It stays hidden while empty. Set the tone with `setStyleSheet("color: …")` and no emoji prefix.
- **Buttons**: default grey #4e5058 · `setProperty("class","primary"|"danger"|"success")`. Radius 4, padding 7×16. Every button has a disabled state. Don't fix button widths, let the text size them.
- **Inset well**: `QFrame` + `setProperty("class","inset")`. Never style a container frame with an unscoped `setStyleSheet("…")`, because it spreads to every child widget and clips them.
- **Reply banner**: `class="replyBanner"`, INSET surface with a 3px Blurple left edge.
- **Sidebar nav**: QListWidget `#nav`, items 7px/8px padding, radius 4; the selected item has a 3px Blurple left border. Pages live in `MainWindow.tabs` (QStackedWidget).
- **Status panel**: 34px Blurple avatar circle with a 14px presence dot overlapping its bottom-right corner, cut out with a 3px CARD-coloured ring. Shows the bot name, with the state underneath.
- **Checkbox**: 18px rounded square, Blurple fill plus a white SVG check when checked.
- **Icons**: QSS can't draw arrows or ticks, so add an SVG to `_ICONS` in theme.py. It's written to a temp folder and referenced by token name.

## Rules
- Text `&` in buttons, checkboxes and actions must be `&&`. In QLabel and list items, keep a single `&`.
- Gate actions that need the bot on BotState: enable on ONLINE; disable on CONNECTING, STOPPING, DISCONNECTED and ERROR as appropriate.
- Empty areas get placeholder text that says what will appear there and how to fill it.
- Add colours as TOKENS in theme.py, not as hex values in the tab files.
