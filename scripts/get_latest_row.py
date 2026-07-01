import os
import sys
import argparse
from google_api_helper import get_gspread_client

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", required=True, help="Status to search for")
    args = parser.parse_args()
    
    spreadsheet_id = os.environ.get("SPREADSHEET_ID", "1FXYJOhyMxNpUNYpLf5O6Tf6UehI1ulHa_B8HzwTkmdM")
    
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(spreadsheet_id)
        ws = sh.worksheet("goctoiphapluat")
    except Exception as e:
        print(f"Error accessing Google Sheet: {e}", file=sys.stderr)
        sys.exit(1)
        
    rows = ws.get_all_values()
    headers = [h.strip() for h in rows[0]]
    
    if "ID" not in headers or "Status" not in headers:
        print("Required columns ID or Status not found", file=sys.stderr)
        sys.exit(1)
        
    id_col = headers.index("ID")
    status_col = headers.index("Status")
    figure_col = headers.index("Historical Figure") if "Historical Figure" in headers else -1
    title_col = headers.index("Video Title") if "Video Title" in headers else -1
    
    target_row = None
    # Search from bottom to top to get the latest matching row
    for r in reversed(rows[1:]):
        if len(r) > status_col and r[status_col].strip().lower() == args.status.lower():
            target_row = r
            break
            
    if not target_row:
        print(f"No row found with status '{args.status}'", file=sys.stderr)
        sys.exit(1)
        
    episode_id = target_row[id_col]
    figure = target_row[figure_col] if figure_col != -1 and len(target_row) > figure_col else ""
    title = target_row[title_col] if title_col != -1 and len(target_row) > title_col else ""
    
    # Write to GITHUB_ENV if running in GitHub Actions
    github_env = os.environ.get("GITHUB_ENV")
    if github_env:
        with open(github_env, "a", encoding="utf-8") as f:
            f.write(f"EPISODE_ID={episode_id}\n")
            f.write(f"ROW_ID={episode_id}\n")
            # Build the prompt for ainovel-cli
            prompt = f"Viết kịch bản chi tiết về vụ án {figure}: {title} bằng tiếng Việt, theo phong cách Góc Tối Pháp Luật."
            f.write(f"PROMPT={prompt}\n")
        print(f"Set GITHUB_ENV: EPISODE_ID={episode_id}")
    else:
        print(f"EPISODE_ID={episode_id}")
        print(f"FIGURE={figure}")
        print(f"TITLE={title}")

if __name__ == "__main__":
    main()
