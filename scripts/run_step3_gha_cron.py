import os
import sys
import subprocess
import logging
from google_api_helper import get_gspread_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Step3Cron")

def main():
    spreadsheet_id = os.environ.get("SPREADSHEET_ID", "1FXYJOhyMxNpUNYpLf5O6Tf6UehI1ulHa_B8HzwTkmdM")
    logger.info(f"Connecting to Google Sheet: {spreadsheet_id}")
    
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(spreadsheet_id)
        ws = sh.worksheet("goctoiphapluat")
    except Exception as e:
        logger.error(f"Failed to access Google Sheet: {e}")
        sys.exit(1)
        
    rows = ws.get_all_values()
    headers = [h.strip() for h in rows[0]]
    
    if "ID" not in headers or "Status" not in headers:
        logger.error("Required columns ID or Status not found in goctoiphapluat tab.")
        sys.exit(1)
        
    id_col = headers.index("ID")
    status_col = headers.index("Status")
    title_col = headers.index("Video Title") if "Video Title" in headers else -1
    
    # 1. Check if there are any rows with status 'pending' (Step 2 is still active)
    has_pending = False
    for r in rows[1:]:
        if len(r) > status_col and r[status_col].strip().lower() == "pending":
            has_pending = True
            break
            
    if has_pending:
        logger.info("Found active 'pending' rows in Step 2. Aborting Step 3 to avoid conflicts.")
        sys.exit(0)
        
    # 2. Find all rows with status 'script'
    script_rows = []
    for idx, r in enumerate(rows[1:], start=2):
        if len(r) > status_col and r[status_col].strip().lower() == "script":
            script_rows.append((idx, r))
            
    if not script_rows:
        logger.info("No rows with status 'script' found. Exiting.")
        sys.exit(0)
        
    logger.info(f"Found {len(script_rows)} rows with status 'script'. Starting prompt generation...")
    
    for idx, r in script_rows:
        episode_id = r[id_col]
        title = r[title_col] if title_col != -1 and len(r) > title_col else f"Episode {episode_id[:8]}"
        
        logger.info(f"--- Generating Prompts for row {idx}: {title} (ID: {episode_id}) ---")
        
        try:
            # Download script
            logger.info("Running download_script.py...")
            env = os.environ.copy()
            env["EPISODE_ID"] = episode_id
            subprocess.run([sys.executable, "scripts/download_script.py"], env=env, check=True)
            
            # Generate prompts
            logger.info("Running generate_prompts.py...")
            subprocess.run([sys.executable, "scripts/generate_prompts.py"], env=env, check=True)
            
            # Update status to 'prompt'
            logger.info("Running update_status.py...")
            env["STATUS"] = "prompt"
            subprocess.run([sys.executable, "scripts/update_status.py"], env=env, check=True)
            
            logger.info(f"Row {idx} prompt generation completed successfully!")
            
        except Exception as e:
            logger.error(f"Failed to generate prompts for row {idx}: {e}")
            try:
                ws.update_cell(idx, status_col + 1, "step3failed")
                logger.info(f"Updated row {idx} status to 'step3failed'")
            except Exception as se:
                logger.error(f"Failed to update status to step3failed for row {idx}: {se}")
            continue
            
    logger.info("Step 3 Cron run completed.")

if __name__ == "__main__":
    main()
