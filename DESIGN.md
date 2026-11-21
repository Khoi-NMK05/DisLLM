---
name: Discord AI Companion
description: A Discord-native dark control panel for a self-hosted AI bot.
colors:
  blurple: "#5865f2"
  blurple-hover: "#4752c4"
  blurple-pressed: "#3c45a5"
  base: "#1e1f22"
  card: "#2b2d31"
  raised: "#35373c"
  selected: "#404249"
  inset: "#1e1f22"
  well: "#111214"
  hairline: "rgba(255, 255, 255, 0.06)"
  text: "#dbdee1"
  text-strong: "#f2f3f5"
  text-muted: "#949ba4"
  text-faint: "#6d6f78"
  on-accent: "#ffffff"
  grey-button: "#4e5058"
  grey-button-hover: "#6d6f78"
  success: "#23a55a"
  success-hover: "#1a8a4a"
  danger: "#da373c"
  danger-hover: "#a12828"
  text-success: "#2dc770"
  text-warning: "#f0b232"
  text-danger: "#fa777c"
  presence-online: "#23a55a"
  presence-idle: "#f0b232"
  presence-error: "#f23f43"
  presence-offline: "#80848e"
typography:
  headline:
    fontFamily: "Segoe UI, gg sans, Helvetica Neue, Arial, sans-serif"
    fontSize: "16px"
    fontWeight: 600
  title:
    fontFamily: "Segoe UI, gg sans, Helvetica Neue, Arial, sans-serif"
    fontSize: "15px"
    fontWeight: 600
  nav:
    fontFamily: "Segoe UI, gg sans, Helvetica Neue, Arial, sans-serif"
    fontSize: "14px"
    fontWeight: 500
  body:
    fontFamily: "Segoe UI, gg sans, Helvetica Neue, Arial, sans-serif"
    fontSize: "13px"
    fontWeight: 400
  body-small:
    fontFamily: "Segoe UI, gg sans, Helvetica Neue, Arial, sans-serif"
    fontSize: "12px"
    fontWeight: 400
  label:
    fontFamily: "Segoe UI, gg sans, Helvetica Neue, Arial, sans-serif"
    fontSize: "12px"
    fontWeight: 700
    letterSpacing: "0.4px"
  label-small:
    fontFamily: "Segoe UI, gg sans, Helvetica Neue, Arial, sans-serif"
    fontSize: "11px"
    fontWeight: 700
    letterSpacing: "0.4px"
  mono:
    fontFamily: "Consolas, Courier New, monospace"
    fontSize: "12px"
    fontWeight: 400
rounded:
  xs: "3px"
  sm: "4px"
  md: "6px"
  lg: "8px"
  pill: "17px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "10px"
  lg: "12px"
  xl: "16px"
  page: "20px"
components:
  button-default:
    backgroundColor: "{colors.grey-button}"
    textColor: "{colors.on-accent}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: "7px 16px"
  button-default-hover:
    backgroundColor: "{colors.grey-button-hover}"
  button-default-pressed:
    backgroundColor: "{colors.selected}"
  button-primary:
    backgroundColor: "{colors.blurple}"
    textColor: "{colors.on-accent}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: "7px 16px"
  button-primary-hover:
    backgroundColor: "{colors.blurple-hover}"
  button-primary-pressed:
    backgroundColor: "{colors.blurple-pressed}"
  button-success:
    backgroundColor: "{colors.success}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.sm}"
    padding: "7px 16px"
  button-success-hover:
    backgroundColor: "{colors.success-hover}"
  button-danger:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.sm}"
    padding: "7px 16px"
  button-danger-hover:
    backgroundColor: "{colors.danger-hover}"
  button-disabled:
    backgroundColor: "{colors.raised}"
    textColor: "{colors.text-faint}"
  card:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.lg}"
    padding: "14px 16px 16px 16px"
  input:
    backgroundColor: "{colors.inset}"
    textColor: "{colors.text}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: "7px 10px"
  input-in-well:
    backgroundColor: "{colors.well}"
  inset-well:
    backgroundColor: "{colors.inset}"
    rounded: "{rounded.md}"
    padding: "10px 12px"
  nav-item:
    textColor: "{colors.text-muted}"
    typography: "{typography.nav}"
    rounded: "{rounded.sm}"
    padding: "7px 8px"
  nav-item-hover:
    backgroundColor: "{colors.raised}"
    textColor: "{colors.text}"
  nav-item-selected:
    backgroundColor: "{colors.selected}"
    textColor: "{colors.on-accent}"
  menu:
    backgroundColor: "{colors.well}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    padding: "6px"
  tooltip:
    backgroundColor: "{colors.well}"
    textColor: "{colors.text}"
    padding: "6px 8px"
  status-avatar:
    backgroundColor: "{colors.blurple}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.pill}"
    size: "34px"
---

# Design System: Discord AI Companion

<!-- Source of truth for values: gui/theme.py (TOKENS + QSS) and gui/widgets.py. If they disagree with this file, the code wins; re-run /impeccable document. -->

## Overview

**Creative North Star: "The Home Server"**

The control panel should feel like one more server in the owner's Discord sidebar. It's the place their bot lives: dark, calm and immediately familiar to anyone who uses Discord every day. The sidebar reads as a channel list, the bottom-left panel reads as Discord's user panel showing the bot's presence, and settings sit on flat cards in Discord's charcoal greys. A self-hoster opening it after hours in the tray should know where everything is before they read a word.

The language is Discord's, tightened slightly into a tool. Discord's settings screens are spacious, but this app holds sliders, tables, logs and model forms, so spacing stays compact (a 4px base, 16px card padding, 10px between items) and hierarchy comes from weight and colour rather than size. Depth comes from small steps in lightness within one cool grey hue, never from outlines or shadows. Blurple is the only accent, and the presence colours (green, amber, red, grey) mean bot state and nothing else.

The look this system replaced is the one thing it rejects outright: cards, tables and lists boxed in solid `#35373c` borders. No emoji appear in the interface. Tone comes from colour, and every glyph is monochrome.

**Key Characteristics:**
- Discord-native dark UI: a channel-list sidebar, a user-panel status block, flat cards.
- One accent (Blurple), used only for primary actions, selection, focus and toggles.
- Depth comes from lightness steps within one hue. No borders on cards and no shadows.
- Presence colours describe bot state and are never decorative.
- Compact, tool-like density with weight-led hierarchy.
- No emoji. Monochrome glyphs and small SVG icons only.

## Colors

One cool charcoal hue stepped through five lightness levels, a single Blurple accent, and Discord's presence colours reserved for state.

### Primary
- **Blurple** (`blurple`): primary buttons, the selected nav item's 3px left edge, input focus borders, checked checkboxes, the filled part of a slider, selected rows in dropdowns and menus, and the status avatar. It darkens on hover (`blurple-hover`) and further when pressed (`blurple-pressed`).

### Neutral
- **Channel-List Charcoal** (`base`): the window, sidebar, status bar and dialogs. The floor everything else sits on.
- **Card Slate** (`card`): cards, the status panel, dropdown popups and table header rows.
- **Hover Slate** (`raised`): hover backgrounds and disabled buttons.
- **Selected Slate** (`selected`): the selected nav item and pressed default buttons.
- **Inset** (`inset`): inputs, tables, lists and wells inside a card, sunk one step below it. The same value as `base`, but its own role.
- **Deep Well** (`well`): inputs inside an inset well, menus, tooltips and scrollbar handles. The darkest surface.
- **Hairline** (`hairline`): 1px dividers between the large regions only: the sidebar edge, the header underline and the status bar top. Also table gridlines.
- **Text** (`text`): body copy and input text. **Strong** (`text-strong`): the sidebar header, headings and the bot name. **Muted** (`text-muted`): card titles, nav items at rest, helper text and table headers. **Faint** (`text-faint`): disabled text and checkbox outlines.
- **Grey Button** (`grey-button`): the default (secondary) button. It lightens on hover (`grey-button-hover`). Also the empty part of a slider track.

### Status
- **Success Green** (`success`): confirming actions such as Start Bot. **Danger Red** (`danger`): destructive actions such as wipe, stop and delete. Both darken on hover.
- **Feedback text** (`text-success`, `text-warning`, `text-danger`): lighter versions used only for status message text, so it stays at least 4.5:1 on a card. The button fills are too dark for text (`danger` is 3.0:1 on `card`). In-progress messages use `text-muted`, not Blurple.
- **Presence**: online (`presence-online`), connecting or stopping (`presence-idle`), error (`presence-error`), disconnected (`presence-offline`). These appear only on the status panel's presence dot and in state text.

### Named Rules
**The One Accent Rule.** Blurple is the only accent colour. If something needs to stand out and it isn't a primary action, selection, focus or a toggle, use weight or `text-strong`, not colour.

**The Presence Means State Rule.** Green, amber, red and grey on a status element always mean the bot's connection state. Never use them for decoration, categories or emphasis.

## Typography

**Body Font:** Segoe UI (falling back to gg sans, Helvetica Neue, Arial, sans-serif)
**Mono Font:** Consolas (falling back to Courier New, monospace), for logs only

**Character:** the platform's own UI sans at a 13px base, close to Discord's density. One family carries the whole hierarchy. Weight and colour do most of the work and size does the rest.

### Hierarchy
- **Headline** (600, 16px): in-page headings (`QLabel.heading`), in `text-strong`.
- **Title** (600, 15px): the sidebar header, "Discord AI Companion", 48px tall with a hairline underneath.
- **Nav** (500, 14px): sidebar nav items, muted until hovered or selected.
- **Body** (400, 13px): everything by default, including buttons (at weight 500), inputs and form labels.
- **Body Small** (400, 12px): muted helper text (`QLabel.muted`), the status bar, and the bot's state under its name.
- **Label** (700, 12px, +0.4px tracking, uppercase): card headers, in `text-muted`. `Card` uppercases the title for you.
- **Label Small** (700, 11px, +0.4px tracking): the sidebar section label ("CONTROL CENTER") and table column headers.
- **Mono** (400, 12px): the log console.

### Named Rules
**The Weight Before Size Rule.** Build hierarchy with weight and colour first and size second. The full range runs from 11px to 16px. A new screen shouldn't need anything bigger.

## Layout

A fixed left sidebar (the channel list) with a pinned status panel at its foot, and a stacked content area on the right where each nav item swaps in a page (`MainWindow.tabs`, a QStackedWidget). A status bar runs along the bottom.

- Page margins are 20px. Cards sit 16px apart, and splitter handles are 16px wide and invisible.
- Card padding is 16px (14px on top). Header to body is 12px, and items in the body are 10px apart.
- Inset wells use 10–12px inner margins. The status panel uses 10px margins and 10px gaps.
- In grids inside a card, give the last row stretch so rows stay packed at the top and don't spread out.
- Density is deliberately a little tighter than Discord's own settings. Don't add whitespace to make things feel premium. This is a working tool.
- The app is a resizable desktop window, from the 960×620 minimum to a maximized monitor, on Windows, macOS and Linux.
- A page whose cards can be taller than the window goes in a frameless `QScrollArea` (vertical only). Its viewport and content widget must have `setAutoFillBackground(False)` after `setWidget()`, or a light default grey shows behind the cards. The page's action bar (Save, Reset) sits outside the scroll area so it's always visible.
- Rows of cards side by side become a single column when the page is narrower than about 820px. See `AIModelsTab.resizeEvent`.
- Technical settings get a plain-language tooltip on their label. Slider readouts have a fixed width so the slider doesn't shift while dragging.

## Elevation & Depth

Completely flat. There are no shadows anywhere. Depth comes only from tonal steps: content cards (`card`) sit one step above the window (`base`), interactive surfaces get lighter on hover (`raised`) and when selected (`selected`), and inputs sink below their parent (`inset` on a card, `well` inside an inset). Hairlines appear only between the large regions (sidebar, header, status bar).

### Named Rules
**The Sink, Don't Outline Rule.** To separate an element, step its surface up or down one level. Never draw a border around a card, table or list. That was the old look.

**The Hairline Only Between Regions Rule.** 1px `hairline` dividers belong between the sidebar, header and status bar, and nowhere inside the content area.

## Shapes

Small, consistent rounding. Cards use 8px (`lg`), inset wells 6px (`md`), and buttons, inputs, nav items, checkboxes, menus and tables 4px (`sm`). Menu and dropdown items use 3px (`xs`). The only true circles are the status avatar (34px) and its 14px presence dot. A 3px left edge in Blurple is the recurring accent mark, on the selected nav item and on the reply banner.

## Components

### Buttons
Compact, flat and readable at a glance.
- **Shape:** gently rounded (4px), 7px × 16px padding, text at weight 500. Let the label set the width. Don't fix button widths.
- **Default:** a grey button for most actions.
- **Primary / Success / Danger:** set the `class` property to `primary`, `success` or `danger`. Use Primary for the main action on a card, Success for starting things, and Danger for destructive actions.
- **States:** each variant has hover and pressed steps. Every variant has a disabled state (`raised` background, `text-faint` text). Buttons inside tables use tighter 4px × 12px padding.

### Cards / Containers
- Use `gui.widgets.Card("Title")` and add content to `card.body`, which is a vertical layout. `setTitle()` works like QGroupBox's.
- `card` surface, 8px radius, no border and no shadow. The uppercase `label` header is in `text-muted`.
- **Inset well:** a `QFrame` with `class="inset"`, used for tool rows, editors and composers inside a card. Inputs inside it automatically drop to `well`.

### Inputs / Fields
- `inset` background, a transparent 1px border, 4px radius, 7px × 10px padding.
- **Focus:** the border turns Blurple. Dropdowns also get the Blurple border on hover.
- **Disabled:** text drops to `text-faint`.
- **Dropdowns:** use the SVG chevron. The popup list is `card` with a hairline border, items are at least 26px tall, hover is `raised` and the selected item is Blurple.
- **Spin boxes:** SVG up and down chevrons, with a `raised` background on hover.
- **Checkbox:** an 18px rounded square on `inset` with a `text-faint` outline. When checked it fills Blurple and shows a white SVG tick.
- **Slider:** a 6px track, Blurple to the left of the handle and `grey-button` to the right, with a 14px white round handle.

### Navigation
- **Sidebar:** a QListWidget (`#nav`) on `base`. Items have 7px × 8px padding and a 4px radius, and rest in `text-muted` at 14px/500.
- **Hover:** `raised` background with `text`. **Selected:** `selected` background, white text and a 3px Blurple left edge.
- A small monochrome `#` glyph in front of each item, like a Discord channel.

### Status Panel (signature)
Discord's bottom-left user panel, showing the bot. A 34px Blurple avatar circle, with a 14px presence dot overlapping its bottom-right corner and cut out by a 3px ring in the `card` colour. Beside it, the bot's name in `text-strong` 13px/600, with its state underneath in `text-muted` 12px ("Connecting...", "Error - see Dashboard").

### Reply Banner
An `inset` strip with a 3px Blurple left edge and a 4px radius (`class="replyBanner"`). It shows which message a reply will go to.

### Feedback Messages
Use `gui.widgets.StatusLabel` for every inline result or error. It word-wraps and stays hidden while it has no text. Set text and tone together with `setTone(text, "neutral" | "success" | "warning" | "error")`, which reads the feedback tokens. Don't hardcode a hex colour, and never add an emoji prefix. A message says what happened and what to do next ("Settings saved. Restart the bot to connect to the new Ollama host.").

### Tables, Lists, Menus, Tooltips
- Tables and lists use `inset` with no border and `hairline` gridlines. Header cells are `card` with 11px/700 muted text.
- Menus use `well` with a hairline border and 6px padding, and hovered items turn Blurple.
- Tooltips use `well` with no border and 6px × 8px padding.
- Scrollbars are 8px wide: a `well` handle that turns `grey-button` on hover, with no arrow buttons.

## Do's and Don'ts

### Do:
- **Do** take every colour from `TOKENS` in `gui/theme.py`. Add a token there before you use a new value.
- **Do** separate surfaces by stepping lightness (`base` → `card` → `inset` → `well`), following the Sink, Don't Outline Rule.
- **Do** give every button a disabled state, and enable bot-dependent actions only while `BotState` is ONLINE. Disable them on CONNECTING, STOPPING, DISCONNECTED and ERROR as appropriate.
- **Do** add new arrows, ticks or glyphs as small monochrome SVGs in `_ICONS` in `theme.py`, because Qt stylesheets can't draw them.
- **Do** escape `&` as `&&` in button, checkbox and action text. Keep a single `&` in QLabel and list items.
- **Do** style containers through a `class` property and the global QSS.
- **Do** write form labels and checkboxes in sentence case ("Max reply length (tokens):") and buttons and card titles in Title Case ("Save Persona"). When a setting has a well-known technical name, put it in brackets after the plain one ("Creativity (temperature):") so people can match it to model guides.

### Don't:
- **Don't** put a solid `#35373c` border around cards, tables or lists.
- **Don't** use emoji anywhere in the UI, including button labels and status messages.
- **Don't** use presence colours for anything other than bot state.
- **Don't** introduce a second accent colour or any gradients or shadows.
- **Don't** call an unscoped `setStyleSheet("…")` on a container frame. It spreads to every child widget and clips them.
- **Don't** fix button widths, or go beyond the 11–16px type range for interface text.
