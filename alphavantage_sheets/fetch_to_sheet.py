#!/usr/bin/env python3
"""Pull daily stock prices from Alpha Vantage and store a 500-row sample in a new Google Sheet.

Setup:
  1. Free API key:  https://www.alphavantage.co/support/#api-key
  2. Google Cloud Console: enable the "Google Sheets API", create an OAuth client ID
     (Application type: Desktop app) and save it as credentials.json next to this file.
  3. export ALPHAVANTAGE_API_KEY=your_key
  4. pip install -r requirements.txt
  5. python fetch_to_sheet.py --symbol IBM --rows 500
"""
import argparse
import os
import sys

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

API_URL = "https://www.alphavantage.co/query"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
HEADER = ["date", "symbol", "open", "high", "low", "close", "volume"]


def fetch_daily(symbol: str, api_key: str, rows: int) -> list[list]:
    """Return the most recent `rows` daily bars (newest first)."""
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "outputsize": "full" if rows > 100 else "compact",  # compact = 100 rows, full = 20+ years
        "apikey": api_key,
    }
    resp = requests.get(API_URL, params=params, timeout=30)
    resp.raise_for_status()
    payload = resp.json()

    series = payload.get("Time Series (Daily)")
    if series is None:
        # Alpha Vantage returns errors / rate-limit notices with HTTP 200
        msg = payload.get("Error Message") or payload.get("Note") or payload.get("Information") or payload
        sys.exit(f"Alpha Vantage error: {msg}")

    data = [
        [day, symbol, float(v["1. open"]), float(v["2. high"]),
         float(v["3. low"]), float(v["4. close"]), int(v["5. volume"])]
        for day, v in sorted(series.items(), reverse=True)
    ]
    if len(data) < rows:
        print(f"Warning: only {len(data)} rows available (requested {rows}).")
    return data[:rows]


def get_credentials() -> Credentials:
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())
    return creds


def create_sheet(title: str, values: list[list]) -> str:
    sheets = build("sheets", "v4", credentials=get_credentials())
    ss = sheets.spreadsheets().create(
        body={"properties": {"title": title}}, fields="spreadsheetId,spreadsheetUrl"
    ).execute()
    sheets.spreadsheets().values().update(
        spreadsheetId=ss["spreadsheetId"],
        range="A1",
        valueInputOption="USER_ENTERED",
        body={"values": values},
    ).execute()
    return ss["spreadsheetUrl"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbol", default="IBM")
    ap.add_argument("--rows", type=int, default=500)
    args = ap.parse_args()

    api_key = os.environ.get("ALPHAVANTAGE_API_KEY")
    if not api_key:
        sys.exit("Set ALPHAVANTAGE_API_KEY first.")

    rows = fetch_daily(args.symbol, api_key, args.rows)
    url = create_sheet(f"Alpha Vantage {args.symbol} daily ({len(rows)} rows)", [HEADER] + rows)
    print(f"Wrote {len(rows)} rows -> {url}")


if __name__ == "__main__":
    main()
