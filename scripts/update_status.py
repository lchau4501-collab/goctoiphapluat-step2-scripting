import os
import sys
import logging
from google_api_helper import get_gspread_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("UpdateStatus")

def main():
    spreadsheet_id = os.environ.get("SPREADSHEET_ID", "1FXYJOhyMxNpUNYpLf5O6Tf6UehI1ulHa_B8HzwTkmdM")
    episode_id = os.environ.get("EPISODE_ID") or os.environ.get("ROW_ID")
    status_to_set = os.environ.get("STATUS", "prompt")
    
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
        
    if "Status" not in headers:
        logger.error("Could not find 'Status' column in goctoiphapluat tab.")
        sys.exit(1)
        
    status_col_idx = headers.index("Status") + 1
    
    logger.info(f"Updating status of row {target_row_idx} to '{status_to_set}'...")
    try:
        ws.update_cell(target_row_idx, status_col_idx, status_to_set)
        logger.info("Successfully updated status in GSheet!")
    except Exception as e:
        logger.error(f"Failed to update GSheet status cell: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
