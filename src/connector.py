# connector.py


# connector.py (extracted from fetch_and_report.py without logic changes)
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound

CANONICAL_HEADER = ["timestamp","source","brands","title","link","summary","sentiment","topic","est_reach"]

class Connector:

    sheet_id = ""
    sheet_name = ""
    client = None

    def __init__(self, sheet_id, sheet_name):
        self.sheet_id = sheet_id
        self.sheet_name = sheet_name
        scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_service_account.json", scope)
        self.client = gspread.authorize(creds)

    def ensure_header(self, ws):
        """Ensure the sheet has the canonical header; upgrade 'brand' -> 'brands' if needed."""
        try:
            values = ws.get_all_values()
            if not values or not values[0]:
                ws.update(f"A1:{chr(64+len(CANONICAL_HEADER))}1", [CANONICAL_HEADER])
                logging.info("Initialized header row: %s", CANONICAL_HEADER)
                return
            header = values[0]
            if len(header) >= 3 and header[2].strip().lower() == "brand":
                header[2] = "brands"
                ws.update(f"A1:{chr(64+len(header))}1", [header])
                logging.info("Renamed 'brand' column to 'brands'.")
            missing = [h for h in CANONICAL_HEADER if h not in header]
            if missing:
                for m in missing:
                    header.append(m)
                ws.update(f"A1:{chr(64+len(header))}1", [header])
                logging.info("Updated header row to include missing fields: %s", missing)
        except Exception as e:
            logging.warning("Could not ensure header: %s", e)

    
    def load_sheet(self):
        # logging.info("Authorizing service account: %s; opening spreadsheet by ID",
        #              getattr(creds, "_service_account_email", "unknown-sa"))

        try:
            sh = self.client.open_by_key(self.sheet_id)
        except SpreadsheetNotFound:
            logging.error("SpreadsheetNotFound")
            raise
        except APIError as e:
            logging.error("APIError when opening spreadsheet: %s", e)
            raise

        try:
            ws = sh.worksheet(self.sheet_name)
            logging.info("Worksheet found: %s (rows=%d, cols=%d)", ws.title, ws.row_count, ws.col_count)
        except WorksheetNotFound:
            logging.warning("Worksheet %r not found. Creating it…", self.sheet_name)
            ws = sh.add_worksheet(self.sheet_name, rows=1000, cols=12)
            ws.update(f"A1:{chr(64+len(CANONICAL_HEADER))}1", [CANONICAL_HEADER])
            logging.info("Created worksheet and initialized header.")

        self.ensure_header(ws)

        try:
            worksheets = sh.worksheets()
            sh.reorder_worksheets([ws] + [w for w in worksheets if w.id != ws.id])
            logging.info("Reordered worksheets so '%s' is first.", ws.title)
        except Exception as e:
            logging.warning("Could not reorder worksheets: %s", e)

        logging.info("Targeting spreadsheet URL: https://docs.google.com/spreadsheets/d/%s/edit#gid=%s", sh.id, ws.id)
        return ws
