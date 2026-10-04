# Simulator UI contract

The interface is a research instrument for reading monthly scenarios and making
loan repayment decisions. Preserve the narrative, questionnaire order, treatment
visibility, calculations, scoring, persistence, and confirmation rules.

## Visual system

Use locally hosted IBM Plex Sans for controls and data, with Plex Serif reserved
for calendar-month and profile headings. Keep the warm paper surfaces, dark
masthead, aligned financial statement, restrained ochre accents, and four-pixel
corners. Income and available money are green; costs and debt are red, with text
labels conveying the meaning independently of color.

Use shared components and semantic tokens. Avoid decorative charts, gradients,
glows, oversized headings, and separate cards for every value. Financial values
use tabular numbers and consistent right alignment.

## Interaction and accessibility

Page changes focus the new page title. A keyboard skip link reaches the main
content. Language changes retain focus on the language control. Consent and
instructions promote their existing Markdown title and subsections to the
correct heading levels without changing the text.

At widths below 900px, the simulation stacks narrative before the financial
statement and includes a link to the payment decision. Keep narration readable,
inputs at least 16px, visible focus indicators, and header controls at least 44px
high. Test 320, 768, 1024, and 1440px layouts.

The administrator's condition selector keeps C1–C8 as submission values and
displays the localized explanation below it, so narrow screens never hide the
meaning of the selected treatment. Set the document language on administrative
and participant pages alike.

Page transitions use a short opacity fade. Next-month narration uses a separate
word reveal that never blocks decisions. Both respect reduced motion. The main
content is not a live region: focusing the heading announces page changes without
announcing every animated narration word. Errors remain alerts.

## Verification

Run `python -m pytest -q` and `python scripts/review_ui.py <review-name>`.
The browser review uses disposable in-memory data and exercises all 24 months,
questionnaire chapters, administration, both languages, and alternate payment
states. Review screenshots alongside automated accessibility checks; passing
automation alone is not a claim of complete accessibility compliance.
