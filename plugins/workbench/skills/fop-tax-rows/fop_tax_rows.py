"""Print Google Sheet rows (TSV) of business income from Wise with official NBU rates.

Usage: python3 fop_tax_rows.py <year> <quarter 1-4> [--start-row N] [--decimal ,]

Columns match the yearly tab: Дата | USD | EUR | USD/UAH | EUR/UAH | UAH formula.
Needs WISE_API_TOKEN in the environment. Income is read from the Wise BUSINESS
profile; set WISE_PROFILE_ID to pick a different profile.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from zoneinfo import ZoneInfo

# First data row of each quarter block in the yearly tab (2026 layout)
QUARTER_START_ROW = {1: 2, 2: 9, 3: 16, 4: 25}
KYIV = ZoneInfo("Europe/Kyiv")


def fetch_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def wise(path, params=None):
    token = os.environ.get("WISE_API_TOKEN")
    if not token:
        sys.exit("WISE_API_TOKEN is not set")
    url = "https://api.wise.com" + path + ("?" + urllib.parse.urlencode(params) if params else "")
    return fetch_json(url, {"Authorization": f"Bearer {token}"})


def nbu_rate(currency, day):
    url = ("https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?"
           f"valcode={currency}&date={day:%Y%m%d}&json")
    data = fetch_json(url)
    if not data:
        sys.exit(f"No NBU rate for {currency} on {day}")
    return data[0]["rate"]


def parse_amount(text):
    """'<positive>+ 4,583.50 EUR</positive>' -> (4583.5, 'EUR')"""
    m = re.search(r"([\d,]+(?:\.\d+)?)\s+([A-Z]{3})", re.sub(r"<[^>]+>", "", text or ""))
    return (float(m.group(1).replace(",", "")), m.group(2)) if m else (None, None)


def quarter_bounds(year, q):
    start = date(year, 3 * q - 2, 1)
    end = date(year + 1, 1, 1) if q == 4 else date(year, 3 * q + 1, 1)
    return start, end


def kyiv_midnight_utc(day):
    return (datetime(day.year, day.month, day.day, tzinfo=KYIV)
            .astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S.000Z"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("year", type=int)
    ap.add_argument("quarter", type=int, choices=[1, 2, 3, 4])
    ap.add_argument("--start-row", type=int, help="sheet row of the first payment")
    ap.add_argument("--decimal", default=os.environ.get("FOP_SHEET_DECIMAL", "."),
                    help="decimal separator for the sheet locale (default: $FOP_SHEET_DECIMAL or '.')")
    ap.add_argument("--copy", action="store_true", help="also copy the rows to the clipboard")
    args = ap.parse_args()

    start, end = quarter_bounds(args.year, args.quarter)
    profiles = wise("/v2/profiles")
    own_names = {p.get("fullName") or p.get("businessName") for p in profiles}
    wanted = os.environ.get("WISE_PROFILE_ID")
    matches = [p for p in profiles
               if (str(p["id"]) == wanted if wanted else p.get("type") == "BUSINESS")]
    if len(matches) != 1:
        sys.exit(f"Expected one {'profile ' + wanted if wanted else 'BUSINESS profile'}, "
                 f"found {len(matches)}; set WISE_PROFILE_ID")
    business = matches[0]

    activities, cursor = [], None
    while True:
        # Wise times are UTC; the quarter is bounded by Kyiv midnight
        params = {"since": kyiv_midnight_utc(start), "until": kyiv_midnight_utc(end), "size": 100}
        if cursor:
            params["nextCursor"] = cursor
        page = wise(f"/v1/profiles/{business['id']}/activities", params)
        activities += page.get("activities", [])
        cursor = page.get("cursor")
        if not cursor:
            break

    payments = []
    for a in activities:
        if a.get("status") != "COMPLETED" or "<positive>" not in (a.get("primaryAmount") or ""):
            continue
        payer = re.sub(r"<[^>]+>", "", a.get("title") or "").strip()
        if payer in own_names:
            continue  # transfer between own accounts, not income
        amount, currency = parse_amount(a["primaryAmount"])
        if currency not in ("USD", "EUR"):
            print(f"! skipped {payer}: {a['primaryAmount']} (unsupported currency)", file=sys.stderr)
            continue
        arrived = (datetime.fromisoformat(a["createdOn"].replace("Z", "+00:00"))
                   .astimezone(KYIV).date())
        if not start <= arrived < end:
            continue
        payments.append((arrived, payer, amount, currency))
    payments.sort()

    row = args.start_row or QUARTER_START_ROW[args.quarter]
    num = lambda x: f"{x:g}".replace(".", args.decimal) if x is not None else ""
    lines, total = [], 0.0
    for arrived, payer, amount, currency in payments:
        rate = nbu_rate(currency, arrived)
        total += amount * rate
        usd, eur = (amount, None) if currency == "USD" else (None, amount)
        usd_rate, eur_rate = (rate, None) if currency == "USD" else (None, rate)
        formula = f"=B{row}*D{row}+C{row}*E{row}"
        lines.append("\t".join([arrived.isoformat(), num(usd), num(eur), num(usd_rate), num(eur_rate), formula]))
        print(f"  {arrived}  {payer}  {amount:,.2f} {currency} @ {rate}", file=sys.stderr)
        row += 1

    print(f"  total {total:,.2f} UAH | 5% {total * 0.05:,.2f} | 1% {total * 0.01:,.2f}", file=sys.stderr)
    print("\n".join(lines))
    if args.copy:
        copy_to_clipboard("\n".join(lines) + "\n")


def copy_to_clipboard(text):
    """Copy with tabs intact; terminals turn tabs into spaces, which breaks the paste."""
    for cmd in (["clip.exe"], ["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"]):
        if shutil.which(cmd[0]):
            subprocess.run(cmd, input=text.encode(), check=True)
            print(f"  copied {len(text.splitlines())} rows to the clipboard", file=sys.stderr)
            return
    print("! no clipboard tool found (clip.exe, pbcopy, wl-copy, xclip)", file=sys.stderr)


if __name__ == "__main__":
    main()
