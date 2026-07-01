import os
import sys
import re
import logging
from google_api_helper import get_gspread_client, upload_to_gdoc, create_drive_folder

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("UploadGDrive")

def extract_folder_id(url):
    match = re.search(r"folders/([a-zA-Z0-9-_]+)", url)
    if match:
        return match.group(1)
    return None

def main():
    spreadsheet_id = os.environ.get("SPREADSHEET_ID", "1FXYJOhyMxNpUNYpLf5O6Tf6UehI1ulHa_B8HzwTkmdM")
    row_id = os.environ.get("ROW_ID") or os.environ.get("EPISODE_ID")
    
    gdoc1_path = "gdoc1.txt"
    gdoc2_path = "gdoc2.txt"
    
    if not row_id:
        logger.error("ROW_ID or EPISODE_ID environment variable is missing.")
        sys.exit(1)
        
    if not os.path.exists(gdoc1_path) or not os.path.exists(gdoc2_path):
        logger.error(f"Required files '{gdoc1_path}' or '{gdoc2_path}' not found in current directory.")
        sys.exit(1)
        
    logger.info(f"Connecting to Google Sheets. Spreadsheet ID: {spreadsheet_id}")
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(spreadsheet_id)
        ws = sh.worksheet("goctoiphapluat")
    except Exception as e:
        logger.error(f"Failed to access Google Sheet: {e}")
        sys.exit(1)
        
    # Find the row matching ROW_ID
    logger.info(f"Locating episode row with ID: {row_id}")
    rows = ws.get_all_values()
    headers = [h.strip() for h in rows[0]]
    
    if "ID" not in headers:
        logger.error("Could not find 'ID' column in goctoiphapluat tab.")
        sys.exit(1)
        
    id_col_idx = headers.index("ID")
    
    target_row_idx = None
    for idx, r in enumerate(rows[1:], start=2):
        if r[id_col_idx] == row_id:
            target_row_idx = idx
            break
            
    if not target_row_idx:
        logger.error(f"No row found with ID '{row_id}' in GSheet.")
        sys.exit(1)
        
    # Get details from row
    row_data = rows[target_row_idx - 1]
    
    # Help map column names to index
    def get_val(col_name):
        if col_name in headers:
            return row_data[headers.index(col_name)]
        return ""
        
    folder_link = get_val("GDrive Folder Link")
    title = get_val("Video Title") or f"Episode {row_id[:8]}"
    
    if not folder_link:
        logger.error("GDrive Folder Link is empty in the sheet row.")
        sys.exit(1)
        
    folder_id = extract_folder_id(folder_link)
    if not folder_id:
        logger.error(f"Could not extract folder ID from GDrive Link: {folder_link}")
        sys.exit(1)
        
    logger.info(f"Found GDrive Folder ID: {folder_id}")
    
    # Create the Images subfolder inside the main episode folder
    logger.info("Creating 'Images' subfolder inside the episode folder...")
    try:
        _, images_folder_url = create_drive_folder("Images", folder_id)
        logger.info(f"Created Images subfolder. URL: {images_folder_url}")
    except Exception as e:
        logger.error(f"Failed to create Images subfolder: {e}")
        sys.exit(1)
    
    # Upload and convert files
    doc1_name = f"{title} - Voiceover Script"
    doc2_name = f"{title} - YouTube Metadata"
    
    logger.info(f"Uploading {gdoc1_path} as Google Doc '{doc1_name}'...")
    try:
        _, doc1_url = upload_to_gdoc(gdoc1_path, doc1_name, folder_id)
    except Exception as e:
        logger.error(f"Failed to upload voiceover script: {e}")
        sys.exit(1)
        
    logger.info(f"Uploading {gdoc2_path} as Google Doc '{doc2_name}'...")
    try:
        _, doc2_url = upload_to_gdoc(gdoc2_path, doc2_name, folder_id)
    except Exception as e:
        logger.error(f"Failed to upload metadata doc: {e}")
        sys.exit(1)
        
    # Update GSheet Row
    logger.info("Updating GSheet row status and links...")
    
    from gspread.cell import Cell
    cells_to_update = []
    
    def add_update(col_name, val):
        if col_name in headers:
            col_idx = headers.index(col_name) + 1
            cells_to_update.append(Cell(row=target_row_idx, col=col_idx, value=val))
            
    add_update("GDoc 1 (Script)", doc1_url)
    add_update("GDoc 2 (Metadata)", doc2_url)
    add_update("Image (gdrive link)", images_folder_url)
    add_update("Status", "script")
    
    if cells_to_update:
        ws.update_cells(cells_to_update)
        logger.info("GSheet row updated successfully!")
    else:
        logger.warning("No updates were made to the GSheet row.")

if __name__ == "__main__":
    main()
