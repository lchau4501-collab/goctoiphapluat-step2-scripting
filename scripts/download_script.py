import os
import sys
import re
import logging
from google_api_helper import get_gspread_client, download_gdoc_as_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DownloadScript")

def extract_doc_id(url):
    match = re.search(r"document/d/([a-zA-Z0-9-_]+)", url)
    if match:
        return match.group(1)
    return None

def main():
    spreadsheet_id = os.environ.get("SPREADSHEET_ID", "1FXYJOhyMxNpUNYpLf5O6Tf6UehI1ulHa_B8HzwTkmdM")
    episode_id = os.environ.get("EPISODE_ID") or os.environ.get("ROW_ID")
    output_path = "script.txt"
    
    if not episode_id:
        logger.error("EPISODE_ID or ROW_ID environment variable is missing.")
        sys.exit(1)
        
    logger.info(f"Connecting to Google Sheets. Spreadsheet ID: {spreadsheet_id}")
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(spreadsheet_id)
        ws = sh.worksheet("goctoiphapluat")
    except Exception as e:
        logger.error(f"Failed to access Google Sheet: {e}")
        sys.exit(1)
        
    # Find the row matching episode_id
    logger.info(f"Locating episode row with ID: {episode_id}")
    rows = ws.get_all_values()
    headers = [h.strip() for h in rows[0]]
    
    if "ID" not in headers:
        logger.error("Could not find 'ID' column in goctoiphapluat tab.")
        sys.exit(1)
        
    id_col_idx = headers.index("ID")
    
    target_row_idx = None
    for idx, r in enumerate(rows[1:], start=2):
        if r[id_col_idx] == episode_id:
            target_row_idx = idx
            break
            
    if not target_row_idx:
        logger.error(f"No row found with ID '{episode_id}' in GSheet.")
        sys.exit(1)
        
    row_data = rows[target_row_idx - 1]
    
    def get_val(col_name):
        if col_name in headers:
            return row_data[headers.index(col_name)]
        return ""
        
    gdoc_link = get_val("GDoc 1 (Script)")
    if not gdoc_link:
        logger.error("GDoc 1 (Script) link is empty in the sheet row.")
        sys.exit(1)
        
    doc_id = extract_doc_id(gdoc_link)
    if not doc_id:
        logger.error(f"Could not extract Document ID from link: {gdoc_link}")
        sys.exit(1)
        
    logger.info(f"Found Google Doc ID: {doc_id}. Starting download...")
    try:
        download_gdoc_as_text(doc_id, output_path)
        logger.info(f"Successfully downloaded script to '{output_path}'")
    except Exception as e:
        logger.error(f"Failed to download document: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
