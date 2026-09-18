# Nova interface design system

Design intent in one sentence: a chat interface that looks like a finished product, exposes the matching logic on every turn, and works the same for keyboard, pointer and touch users on any screen from 320px up.

This document is the source of truth for `web/static/style.css` and `web/templates/index.html`. It follows the Renovast brief: token-driven, WCAG 2.2 AA, keyboard-first, no one-off exceptions.

## 1. Context and goals

The interface has one job: let a person talk to the chatbot and see why each reply was chosen. It is used in three situations.

- A reviewer at DecodeLabs opens the live demo on a laptop.
- An interviewer opens the link on a phone while talking.
- The author demonstrates the pipeline on a projector.

Goals, in priority order:

1. Every reply must show the matched intent, the tier that matched it, and the confidence.
2. The page must be usable at 320px wide with no horizontal scroll.
3. All interactive elements must be reachable and operable with the keyboard alone.
4. Colour contrast must meet AA on every text pair in both themes.
5. The visual style must follow the Renovast tokens: Helvetica Neue, 16px base, 4px radius, green accent with a 2px hard shadow, black header and footer bands.

Out of scope: user accounts, message persistence on the server, file uploads.

## 2. Design tokens and foundations

Tokens live on `:root` in `style.css`. Components must reference tokens, never raw values.

### Typography

| Token | Value | Use |
|---|---|---|
| `--font-family` | "Helvetica Neue", Helvetica, Arial, sans-serif | everything |
| `--font-size-xs` | 12px | metadata, hints, tags |
| `--font-size-sm` | 14px | buttons, trace rows, secondary text |
| `--font-size-md` | 16px | body, inputs (never smaller, or iOS zooms on focus) |
| `--font-size-lg` | 20px | page heading on phones |
| `--font-size-xl` | 24px | page heading from 480px |
| `--font-weight-regular` | 400 | body |
| `--font-weight-medium` | 500 | buttons, labels |
| `--font-weight-bold` | 700 | headings, sender names |
| `--line-height-base` | 24px | body |

Monospace is used only for machine values (intent names, cleaned input, entities), through the system stack `ui-monospace, "SF Mono", Menlo, Consolas, monospace`.

### Spacing

A 5px scale, matching `space.1 = 5px` and `space.2 = 20px` from the brief.

| Token | Value |
|---|---|
| `--space-1` | 5px |
| `--space-2` | 10px |
| `--space-3` | 15px |
| `--space-4` | 20px |
| `--space-5` | 30px |
| `--space-6` | 40px |
| `--space-7` | 60px |

Page gutter: `--gutter` is 16px on phones, 24px from 768px, 32px from 1024px. Nothing else defines its own horizontal page padding.

### Shape, elevation and motion

| Token | Value |
|---|---|
| `--radius-xs` | 4px (every box) |
| `--radius-pill` | 999px (chips, tags, meter) |
| `--shadow-1` | rgb(111 154 55) 0px 2px 0px 0px (primary button only) |
| `--shadow-2` | soft shadow for the phone bottom sheet |
| `--motion-fast` | 120ms (hover, press) |
| `--motion-base` | 200ms (sheet, message entry) |

Motion must be disabled under `prefers-reduced-motion: reduce`. The stylesheet does this globally.

### Colour

The brief listed `color.surface.base = #000000` next to `color.text.primary = #545454`. That pair is 2.4:1 and fails AA, and the extraction note admits low confidence. The system therefore reads Renovast the way the template itself renders: white surfaces, grey body text, green accent, black bands for header and footer.

Light theme, with measured contrast against its usual background:

| Token | Value | Pairs with | Ratio |
|---|---|---|---|
| `--color-surface-base` | #ffffff | | |
| `--color-surface-muted` | #f5f5f5 | | |
| `--color-surface-inverse` | #000000 | header, footer, user bubble | |
| `--color-text-primary` | #545454 | surface base | 7.57 |
| `--color-text-heading` | #1a1a1a | surface base | 17.4 |
| `--color-text-muted` | #6a6a6a | surface base | 5.41 |
| `--color-text-inverse` | #ffffff | surface inverse | 21.0 |
| `--color-text-on-inverse-muted` | #c9c9c9 | surface inverse | 12.7 |
| `--color-text-link` | #0000ee | surface base | 9.4 |
| `--color-accent` | #82b440 | backgrounds only | |
| `--color-accent-contrast` | #111111 | accent | 7.69 |
| `--color-accent-text` | #4f7a1f | surface base | 5.08 |
| `--color-accent-soft` | #eef5e3 | with accent-text | 4.55 |
| `--color-error` | #b71c1c | surface base | 6.57 |
| `--color-focus` | #4f7a1f | surface base | 5.08 |

Dark theme swaps the surfaces to #121412 and #1c1f1c, body text to #c9c9c9 (11.2:1), muted text to #9a9a9a (6.58:1), accent text to #9fd05a (8.31:1 on the soft accent), links to #8ab4f8 and errors to #ff8a80. The accent green itself does not change.

Rule: `--color-accent` (#82b440) is 2.46:1 on white, so it must never carry text on a light surface. Green text uses `--color-accent-text`; green backgrounds carry `--color-accent-contrast` text.

Theme is chosen by `prefers-color-scheme` and can be overridden with `data-theme="light|dark"` on `<html>`, saved in `localStorage`.

## 3. Component rules

Every component defines the seven states from the brief: default, hover, focus-visible, active, disabled, loading, error. Where a state does not apply it says so.

### 3.1 Button

Anatomy: container, optional leading or trailing icon (18px), label.

Variants:
- `btn-primary`: accent background, `--color-accent-contrast` text, `--shadow-1`. One per view (the Send button).
- `btn-secondary`: raised surface, strong border, heading colour text (Clear chat, close).
- `btn-header`: transparent on the black band, white text, translucent hover.
- `btn-icon`: square, icon only, must carry `aria-label`.

States:
- default: as above, minimum height 44px, minimum width 44px for icon-only.
- hover: primary darkens to `--color-accent-strong`; secondary and header get a muted background.
- focus-visible: 2px `--color-focus` outline, 2px offset; white outline inside the black bands.
- active: primary moves down 2px and drops its shadow (the hard shadow reads as a press); others darken.
- disabled: 55% opacity, `cursor: not-allowed`, no transform. Set with the `disabled` attribute so it also leaves the tab order.
- loading: `is-loading` class hides the label and shows a spinner; `aria-busy="true"` must be set.
- error: not applicable.

Behaviour: Enter and Space activate. Pointer and touch behave the same. Labels must be verbs ("Send", "Clear chat"), never "OK" or "Submit".

Responsive: header buttons show icons only below 600px and must keep an `aria-label`; the Send label hides below 480px with the same rule.

### 3.2 Suggestion chip

Anatomy: pill button with the exact message it sends.

States: default (raised surface, strong border), hover (soft accent background, accent border), focus-visible (standard ring), active (solid accent, contrast text), disabled (while a request is in flight), loading and error not applicable.

Keyboard: the row is a roving tabindex group. Tab enters the row on the first chip, Left and Right move, Home and End jump, Enter or Space sends. Pointer and touch tap sends.

Responsive: below 768px the row scrolls horizontally with scroll snap and a thin scrollbar; from 768px it wraps. Chips never truncate; the text is the message.

Edge cases: eight chips maximum in the row. The list is static and must include one example per tier (exact, pattern, keyword, fuzzy, vector).

### 3.3 Message composer

Anatomy: visually hidden label, textarea, Send button, hint line, character counter, error line.

States:
- default: 44px tall, 1px strong border, 16px text.
- hover: border darkens to muted text colour.
- focus-visible: border turns accent-strong and the standard outline is drawn with zero offset.
- active: not applicable.
- disabled: muted background, not-allowed cursor (only used if the server is unreachable for a long period; not used today).
- loading: the Send button carries the loading state; the textarea stays editable.
- error: `aria-invalid="true"`, error border, message in `#form-error` with `role="alert"`.

Placement: pinned at every width. The body is `100dvh` and only the message log scrolls, so the composer and the footer stay in view on phones as well as on desktop. Below 620px of height the suggestion chips and the chat subtitle are dropped to leave room for the log.

Behaviour: Enter sends, Shift+Enter inserts a newline, Escape clears. The textarea grows with content up to 144px (six lines) and then scrolls. `maxlength` is 500; the counter is hidden while the box is empty and turns red at 450. Empty submissions show "Type a message first." instead of sending.

Edge cases: a 500-character message wraps inside the box; pasted newlines are kept; whitespace-only input counts as empty.

### 3.4 Message bubble

Anatomy: meta line (sender, intent tag, time), bubble.

Variants: bot (muted surface), user (inverse surface, right aligned), system (soft accent with a 3px accent left border), error (soft error surface with an error left border).

States: none interactive. Text must be inserted with `textContent`, never `innerHTML`.

Responsive: max width 88% on phones, 80% from 480px, 75% from 768px, 70% from 1024px. Long tokens break with `overflow-wrap: anywhere`; newlines are preserved with `white-space: pre-wrap`.

Edge cases: a reply with a `{user_name}` placeholder must never render an empty slot (the engine filters templates; the UI must not patch this).

### 3.5 Intent tag

Anatomy: pill with intent name and confidence percentage in monospace.

Variants: matched (soft accent background, accent text), fallback and system (muted), error (soft error).

Behaviour: `title` names the tier. The tag is not focusable.

### 3.6 Trace panel

Anatomy: heading, close button (phones only), empty state, definition list of the last match, pipeline list, session list, a short note and a button that opens the intent dialog.

Placement: below 768px it is a bottom sheet (`position: fixed`, 85dvh max, scrim behind). From 768px it is a column of 300px, 340px from 1024px, scrolling internally. The header's Trace button hides or shows the column on wide screens (`is-trace-hidden` on the layout, remembered in `nova.trace-column`) and opens the sheet on phones. Step notes are written in plain words ("close enough despite typos"), not algorithm names.

States:
- closed (phones): translated off screen and `visibility: hidden` so nothing inside is focusable.
- open: `is-open` class, the toggle has `aria-expanded="true"`, focus moves to the panel, Escape or the scrim closes it and focus returns to the toggle.

Pipeline list: seven steps (sanitize, exact, pattern, keyword, fuzzy, vector, fallback) joined by a 2px thread so they read as one flow. Step 1 is always marked tried. Steps before the hit are marked tried, the hit is marked with the accent, later steps stay neutral. A fallback marks step 7.

Intent dialog: a native `<dialog>` opened by "Browse all 34 intents". One row per intent (name, description, one phrase to send), a filter field that matches names, descriptions and every example phrase, and an empty state when nothing matches. The list renders when the dialog opens, so the column itself stays short. Escape, the close button or the backdrop closes it and focus returns to the button.

Empty state: "Send a message to see how it was matched." Long values (a 500-character input) wrap inside the definition cell.

### 3.7 Header and footer bands

Black surface, 2px accent border on the inner edge. Header is sticky. Focus rings inside the bands are white. Below 480px the status shows as a dot only, with the text kept for screen readers; below 360px the tagline is removed. The brand mark is an inline SVG so it needs no request.

## 4. Accessibility requirements and acceptance criteria

Each criterion is a pass or fail check a reviewer can run.

| Requirement | Check | Pass condition |
|---|---|---|
| Skip link | Press Tab once on load | "Skip to message box" appears; Enter focuses the textarea |
| Focus visible | Tab through the whole page | Every stop shows a 2px ring, including inside the black bands |
| Keyboard send | Type in the box, press Enter | Message is sent; Shift+Enter inserts a newline |
| Chip navigation | Tab to the chips, press Right three times | Focus moves along the row without leaving it |
| Sheet focus | On a phone, open the trace, press Escape | Sheet closes and focus returns to the Trace button |
| Names on icon buttons | Inspect with a screen reader at 320px | Each button announces its purpose ("Send message", "Match trace") |
| Live region | Send a message with a screen reader running | The reply is announced without moving focus |
| Contrast | Sample every text colour on its background | 4.5:1 or better in both themes |
| Touch targets | Measure every control on a phone | 44px minimum on the shorter side (chips are 36px tall with 10px gap, which meets the 24px AA minimum in WCAG 2.2) |
| Zoom | Set browser zoom to 200% at 1280px | No content lost, no horizontal scroll |
| Reduced motion | Enable the OS setting | No sheet slide, no message rise, no spinner rotation |
| Error announce | Submit an empty message | "Type a message first." is announced through `role="alert"` |
| No trap | Tab from the last footer link | Focus leaves the page to the browser chrome |

## 5. Content and tone standards

Voice: short, plain, confident. The bot says what it can and cannot do without apologising more than once.

Rules with examples:
- Buttons are verbs: "Send", "Clear chat", "Browse all 34 intents". Not "OK", "Go", "Submit".
- Errors say what happened and what to do: "Messages are limited to 500 characters." Not "Invalid input."
- Limitations are stated as facts: "I don't have access to live weather data." Not "Unfortunately I am unable to help with that request at this time."
- Hints describe the shortcut, nothing else: "Enter to send. Shift+Enter for a new line. Press / to focus."
- Headings are sentence case: "Match trace", not "Match Trace".
- No exclamation marks in system or error text. Bot replies may use one.
- No emoji in the interface.

## 6. Anti-patterns and prohibited implementations

- Raw hex values inside a component rule. Add a token or reuse one.
- `outline: none` anywhere, for any reason.
- Accent green as text on a light surface.
- Font sizes below 16px on inputs, or below 12px anywhere.
- A new spacing value that is not a multiple of 5px.
- `innerHTML` with server or user text.
- Placeholder text as the only label.
- Disabling the Send button while the user still has text to fix (use the error state instead).
- Trapping focus in the bottom sheet without an Escape route.
- Hiding the horizontal scrollbar on the chip row (users need to know it scrolls).

Migration note: the earlier interface used a JetBrains Mono terminal look with a mint accent. All of its classes were removed; nothing from it should be reintroduced.

## 7. QA checklist

Run before every deploy.

- [ ] `pytest` passes.
- [ ] Page renders at 320, 375, 390, 412, 430, 448, 480, 767, 768, 1024 and 1280px with `document.documentElement.scrollWidth` equal to `clientWidth`.
- [ ] Both themes checked at 390px and 1280px.
- [ ] Every accessibility check in section 4 passes.
- [ ] Sending "my name is Zain", then "what is my name" returns the name.
- [ ] Sending "bye" ends the session and the next message starts a new one.
- [ ] Clear chat empties the log, resets the trace and keeps the welcome message.
- [ ] Reload keeps the conversation; Clear chat then reload shows only the welcome message.
- [ ] `/api/health` returns `"status": "ok"`.
- [ ] No console errors on load or after ten messages.
