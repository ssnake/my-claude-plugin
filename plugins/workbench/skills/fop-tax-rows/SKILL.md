---
name: fop-tax-rows
description: Build copy-paste rows for a Ukrainian FOP group 3 tax Google Sheet (5% single tax + 1% military levy) from Wise business-account income, using the official NBU rate on the day each payment arrived. Use when the user asks for tax rows, the quarter's income for the tax sheet, or "fill the taxes sheet" for a quarter.
---

# FOP tax rows from Wise

Requires `WISE_API_TOKEN` in the environment. Income comes from the Wise profile of type BUSINESS. To use a different profile, set `WISE_PROFILE_ID`.

1. Work out the year and quarter. "Last quarter" means the quarter before today's date.
2. Run the script from this skill's base directory:
   ```
   python3 <skill dir>/fop_tax_rows.py <year> <quarter> --copy
   ```
   - `--copy` puts the rows on the clipboard with their tabs intact (clip.exe on WSL/Windows, pbcopy, wl-copy or xclip). Always pass it: rows copied from the terminal get their tabs turned into spaces, so each line pastes into one cell as text and the formulas don't work.
   - `--start-row N` overrides the sheet row of the first payment. The defaults follow the yearly tab layout: Q1 starts at row 2, Q2 at 9, Q3 at 16, Q4 at 25.
   - `--decimal ,` is for a sheet whose locale uses a comma as the decimal separator (Ukrainian, Russian and most European locales). You can also set it with `FOP_SHEET_DECIMAL`. If the pasted formulas show `#VALUE!`, the separator is wrong: the amounts pasted as text.
   - The script prints a summary on stderr (payer, amount, rate, totals) and tab-separated rows on stdout.
3. Show the user the summary as a short table. Tell them the rows are already on their clipboard: click cell **A{start row}** in that year's tab and press Ctrl+V. If the script found no clipboard tool, show the stdout rows exactly as printed in a fenced code block and warn that copying from the terminal may turn the tabs into spaces. The rows fill A–F: Дата, USD, EUR, USD/UAH, EUR/UAH, UAH formula. The quarter's total row already sums F, and its G and H cells hold the 5% and 1% formulas.
4. If a quarter has more payments than its block has rows (6 for Q1 and Q2, 8 for Q3 and Q4), warn the user to insert rows before pasting.

## Rules
- Income is only what reaches the business profile from outside payers. The script skips transfers between the user's own Wise profiles.
- Amount is the amount received after fees. Use the NBU rate for the date the money arrived, taken in Kyiv time. Wise timestamps are UTC, so a payment at 22:00 UTC is dated the next day.
- Never edit the user's original tax sheet. Write to a copy, and only when the user asks for one.
- Wise statement endpoints need SCA signing, so the script reads the `/v1/profiles/{id}/activities` feed instead.
