import os
import sys
import gspread
from google_api_helper import get_gspread_client

SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID', '1FXYJOhyMxNpUNYpLf5O6Tf6UehI1ulHa_B8HzwTkmdM')

def main():
    print("Connecting to Google Sheets...")
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(SPREADSHEET_ID)
        print(f"Connected to spreadsheet: {sh.title}")
    except Exception as e:
        print(f"Failed to connect: {e}")
        print("\n[IMPORTANT] If you see a permission error, please share the Google Sheet with the service account email:")
        print("  n8n-sheets@make-240717.iam.gserviceaccount.com")
        sys.exit(1)

    # 1. Organize 'goctoiphapluat' tab
    headers_master = [
        "ID", "Historical Figure", "Video Title", "Status", 
        "GDrive Folder Link", "GDoc 1 (Script)", "GDoc 2 (Metadata)", 
        "Image Prompts (gsheet link)", "Image (gdrive link)", "Date Created", "Voice"
    ]
    
    print("\n--- Organizing 'goctoiphapluat' tab ---")
    try:
        # Try to find existing worksheet
        ws_master = sh.worksheet('goctoiphapluat')
        print("Found existing 'goctoiphapluat' tab.")
    except gspread.exceptions.WorksheetNotFound:
        # Create it if it doesn't exist
        ws_master = sh.add_worksheet(title='goctoiphapluat', rows=1000, cols=11)
        print("Created new 'goctoiphapluat' tab.")
        
    # Get current values to see if we need to adjust
    current_values = ws_master.get_all_values()
    if not current_values:
        ws_master.append_row(headers_master)
        print("Appended default headers.")
    else:
        # Check if headers match
        current_headers = current_values[0]
        if current_headers[:len(headers_master)] != headers_master:
            print("Headers do not match. Updating headers...")
            ws_master.update(values=[headers_master], range_name='A1:K1')
            print("Headers updated successfully.")
        else:
            print("Headers are already correct.")

    # 2. Organize 'Scene_Prompts' tab
    headers_scenes = [
        "Scene ID", "Episode ID", "Paragraph Excerpt", "Image Prompt", "Image Filename"
    ]
    
    print("\n--- Organizing 'Scene_Prompts' tab ---")
    try:
        ws_scenes = sh.worksheet('Scene_Prompts')
        print("Found existing 'Scene_Prompts' tab.")
    except gspread.exceptions.WorksheetNotFound:
        ws_scenes = sh.add_worksheet(title='Scene_Prompts', rows=5000, cols=10)
        print("Created new 'Scene_Prompts' tab.")
        
    current_values_scenes = ws_scenes.get_all_values()
    if not current_values_scenes:
        ws_scenes.append_row(headers_scenes)
        print("Appended default scene headers.")
    else:
        current_headers_scenes = current_values_scenes[0]
        if current_headers_scenes[:len(headers_scenes)] != headers_scenes:
            print("Scene headers do not match. Updating headers...")
            ws_scenes.update(values=[headers_scenes], range_name='A1:E1')
            print("Scene headers updated successfully.")
        else:
            print("Scene headers are already correct.")

    # 3. Format header rows (optional but professional)
    print("\nFormatting headers...")
    try:
        # Format goctoiphapluat headers
        ws_master.format("A1:K1", {
            "backgroundColor": {"red": 0.1, "green": 0.5, "blue": 0.8, "alpha": 1.0},
            "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True},
            "horizontalAlignment": "CENTER"
        })
        # Format Scene_Prompts headers
        ws_scenes.format("A1:E1", {
            "backgroundColor": {"red": 0.1, "green": 0.5, "blue": 0.8, "alpha": 1.0},
            "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True},
            "horizontalAlignment": "CENTER"
        })
        print("Headers formatted with bold text and professional blue background.")
    except Exception as e:
        print(f"Formatting failed (non-critical): {e}")

    print("\nGoogle Sheets organization complete!")

if __name__ == '__main__':
    main()
