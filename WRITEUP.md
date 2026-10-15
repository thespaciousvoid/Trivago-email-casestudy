# Rate Connect onboarding email: write-up

## Approach

**Spec from the source, not by eye.** Instead of measuring screenshots, I decoded the `.fig` file and read the exact values: every padding, gap, colour, font size and line height for both the 700px desktop frame and the 300px mobile frame. The logos, icons and support avatar are vectors in the file, so I rendered them straight from that geometry to PNG at 3× for sharp retina display.

**Build.** I used nested tables throughout, because that is what Outlook's Word engine renders reliably. The container is fluid with a 700px cap, plus a fixed 700px "ghost" table that only Outlook sees. Mobile is one media query at 600px that turns on the stacked layout from the mobile frame. The two side-by-side rows (the banner and the support links) are "hybrid" inline-blocks, so they still wrap on narrow screens in clients that ignore media queries, such as the Gmail app with a non-Google account.

**One source, three outputs.** `build.py` creates the static email, the AMPscript version and a multi-property preview from a single template, so a layout fix is only ever made once.

## What broke and what I changed

- **Narrow screens without media queries overflowed to 412px on a 375px screen.** The support block was a fixed-width table, and those clients ignore `max-width` on it. Fix: `width:100%; max-width` for everyone, and the fixed `width` attribute for Outlook only.
- **The footer links stacked and "Add a property" wrapped** in Windows and Android fonts. Figma had sized those blocks exactly to SF Pro, with zero slack. Fix: the support block is 420px instead of 372px, and the buttons use `nowrap`.
- **A bug in the Figma mobile frame:** the banner subtitle is a fixed 363px-wide line inside a 260px column, so it runs off both sides. I let it wrap and centred it.
- **Outlook desktop (fixed in advance; each one is a known limitation):**
  - It has no `border-radius`, so the buttons are VML roundrects and the numbered circles are VML ovals.
  - It ignores the system font stack and falls back to Times New Roman, so it is forced to Segoe UI.
  - `rgba` text is unreliable, so the 70%-black subtitle is pre-blended to `#454a4d`.
  - 1px spacer rows render taller than 1px, so the dividers are cell borders instead.
- **Dark mode:** Gmail and Outlook apps invert the background but not images, which would make the black "Rate Connect" logo text disappear. I gave the logo PNG a faint white outline: invisible on white, readable on dark.
- **AMPscript:** writing `%` straight after an inline output block produces `%%%`, which confuses the parser, so the `%` is concatenated inside AMPscript instead.

## Testing

- Rendered in Chromium at 320, 375, 620 and 760px, including a run with the media queries stripped out, and checked for horizontal overflow at every width.
- Linted against caniemail.com support data (`doiuse-email`). Every unsupported feature it flagged in Outlook and Gmail already has a fallback.
- Checked that the HTML size (26 KB) is under Gmail's 102 KB clipping limit, and that every Outlook conditional comment and AMPscript `IF/ENDIF` is balanced.
- **Real inboxes:** sent with `send_test.py` to Gmail (web, iOS/Android), Apple Mail, Outlook.com and Outlook desktop. **[TODO: record what you saw in each client, plus screenshots]**

## How I used AI

I used Claude as the main build partner:
- It wrote the `.fig` decoder and asset renderer.
- It drafted the table structure, VML fallbacks, build script and AMPscript.
- It ran the browser render checks and the caniemail lint.

What I checked or corrected myself:

- **The first render was not shippable.** The no-media-query test exposed the overflow and the wrapping problems above. Each one was fixed only after measuring the elements in the browser, not by guessing.
- **The first avatar export came out blank.** Figma keeps the geometry on the component instance, not the master, and SVG does not allow a `<g>` inside a `clipPath`.
- **I checked AMPscript's `Format()` signature** against the documentation instead of trusting memory.
- **I kept the design's colours** even though white on `#0088d9` (3.8:1) and the footer grey (3.3:1) fall below WCAG AA contrast. Changing brand colours is the design team's call, so I flag it here instead.

**[TODO: add your own notes: what you asked, what you kept, what you would have done differently]**

## With more time

- A full device matrix in Litmus or Email on Acid, with Outlook dark-mode overrides (`[data-ogsc]`).
- Localisation: the VML button widths are fixed, so German and French labels need wider buttons or per-language widths.
- HTML-encode property names in AMPscript (for example `&`), and take number formatting (`15,5 %`) from the hotelier's locale.
- Swap the placeholder campaign and add-property URLs for real deep links, and test the AMPscript against a real Data Extension.
- Raise the two failing colour contrasts with the design team.
