import os
import sys
import logging
import requests
import json
from typing import List, Dict, Any
from google_api_helper import get_gspread_client, create_sheet_in_folder

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("GeneratePrompts")

STATE_FILE = "goctoiphapluat_state.json"
CONFIG_FILE = "../api_config.json" # Relative to scripts folder

class APIClientManager:
    """Manages custom endpoints, API keys, and handles automatic rotation & fallback."""
    def __init__(self):
        self.endpoints: List[Dict[str, Any]] = []
        self.current_index = 0
        self.load_configurations()
 
    def load_configurations(self):
        # 0. Check for Centralized LLM Gateway variables first
        gateway_url = os.environ.get("GATEWAY_URL")
        gateway_token = os.environ.get("GATEWAY_TOKEN")
        if gateway_url and gateway_token:
            self.endpoints.append({
                "type": "openai-compatible",
                "api_key": gateway_token,
                "base_url": gateway_url,
                "model": os.environ.get("GEMINI_MODEL", "google/gemini-2.5-flash")
            })
            logger.info("Configured to use Centralized LLM Gateway.")
            return

        # 1. Try loading from api_config.json
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "api_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "endpoints" in data and isinstance(data["endpoints"], list):
                        for ep in data["endpoints"]:
                            if ep.get("api_key") and ep.get("type") in ["gemini", "openai-compatible"]:
                                self.endpoints.append({
                                    "type": ep["type"],
                                    "api_key": ep["api_key"],
                                    "model": ep.get("model", "gemini-2.5-flash"),
                                    "base_url": ep.get("base_url", "https://generativelanguage.googleapis.com")
                                })
                if self.endpoints:
                    logger.info(f"Loaded {len(self.endpoints)} endpoints from api_config.json.")
                    return
            except Exception as e:
                logger.warning(f"Failed to read api_config.json: {e}")

        # 2. Fallback to env
        gemini_keys_str = os.environ.get("GEMINI_API_KEYS", "")
        if gemini_keys_str:
            keys = [k.strip() for k in gemini_keys_str.split(",") if k.strip()]
            for k in keys:
                self.endpoints.append({
                    "type": "gemini",
                    "api_key": k,
                    "model": os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
                    "base_url": "https://generativelanguage.googleapis.com"
                })

        # Single key fallback
        single_key = os.environ.get("GEMINI_API_KEY")
        if not self.endpoints and single_key:
            self.endpoints.append({
                "type": "gemini",
                "api_key": single_key,
                "model": os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
                "base_url": "https://generativelanguage.googleapis.com"
            })

        if not self.endpoints:
            logger.error("No valid API endpoints configured. Please set GEMINI_API_KEY in .env.")
            sys.exit(1)

    def get_current_endpoint(self) -> Dict[str, Any]:
        return self.endpoints[self.current_index]

    def rotate_endpoint(self):
        if len(self.endpoints) <= 1:
            return
        self.current_index = (self.current_index + 1) % len(self.endpoints)
        logger.info(f"Rotating to API endpoint index {self.current_index}")

    def generate_prompt_for_para(self, paragraph: str) -> str:
        prompt = (
            "You are an expert prompt engineer for Midjourney and Stable Diffusion. "
            "Write a detailed, high-quality, atmospheric image prompt in English based on this paragraph from a Vietnamese True Crime noir story (often set in historical/vintage Vietnam, e.g., pre-1975 Saigon, retro Asian styling).\n"
            "Format: oil painting / vintage photograph / cinematic photography, cinematic lighting, moody noir, retro Vietnamese aesthetic.\n"
            "Rules: Keep the style dark, dramatic, retro, and cinematic. Avoid any gore, graphic violence, text, modern objects, or cartoonish details. Focus on scenery, lighting, vintage objects (like rotary phones, old documents, neon lights, desk lamps, old vehicles), and vintage Vietnamese cityscapes or interior spaces.\n"
            f"Paragraph:\n{paragraph}\n\n"
            "Prompt (output only the raw prompt text):"
        )
        
        attempts = 0
        max_attempts = len(self.endpoints) * 2
        while attempts < max_attempts:
            ep = self.get_current_endpoint()
            headers = {"Content-Type": "application/json"}
            
            try:
                if ep["type"] == "gemini":
                    url = f"{ep['base_url']}/v1beta/models/{ep['model']}:generateContent?key={ep['api_key']}"
                    payload = {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.6}
                    }
                    response = requests.post(url, headers=headers, json=payload, timeout=60)
                else:
                    url = f"{ep['base_url']}/chat/completions"
                    headers["Authorization"] = f"Bearer {ep['api_key']}"
                    payload = {
                        "model": ep["model"],
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.6
                    }
                    response = requests.post(url, headers=headers, json=payload, timeout=60)
                
                if response.status_code == 200:
                    data = response.json()
                    if ep["type"] == "gemini":
                        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    else:
                        return data["choices"][0]["message"]["content"].strip()
                else:
                    logger.warning(f"API status code {response.status_code}. Rotating...")
                    self.rotate_endpoint()
            except Exception as e:
                logger.error(f"API call failed: {e}")
                self.rotate_endpoint()
            attempts += 1
            
        raise RuntimeError("Failed to generate prompt after trying all endpoints.")

def main():
    spreadsheet_id = os.environ.get("SPREADSHEET_ID", "1FXYJOhyMxNpUNYpLf5O6Tf6UehI1ulHa_B8HzwTkmdM")
    episode_id = os.environ.get("EPISODE_ID") or os.environ.get("ROW_ID")
    script_path = "script.txt"
    
    if not episode_id:
        logger.error("EPISODE_ID or ROW_ID environment variable is missing.")
        sys.exit(1)
        
    if not os.path.exists(script_path):
        logger.error(f"Script file '{script_path}' not found. Run download_script.py first.")
        sys.exit(1)
        
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Split by section divider
    sections = [s.strip() for s in content.split(".........") if s.strip()]
    
    # Further split sections into paragraphs
    paragraphs = []
    for section_idx, section in enumerate(sections, 1):
        lines = [p.strip() for p in section.split("\n\n") if p.strip()]
        for p in lines:
            # Skip any remaining metadata header lines
            if "YOUTUBE VIDEO METADATA" in p or "CHOSEN TITLE" in p or "DESCRIPTION" in p:
                continue
            paragraphs.append(p)
            
    logger.info(f"Parsed {len(paragraphs)} paragraphs from script.")
    
    # Locate episode in the master sheet to get title and folder link
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
        
    folder_link = get_val("GDrive Folder Link")
    title = get_val("Video Title") or f"Episode {episode_id[:8]}"
    
    if not folder_link:
        logger.error("GDrive Folder Link is empty in the sheet row.")
        sys.exit(1)
        
    def extract_folder_id(url):
        import re
        match = re.search(r"folders/([a-zA-Z0-9-_]+)", url)
        if match:
            return match.group(1)
        return None
        
    folder_id = extract_folder_id(folder_link)
    if not folder_id:
        logger.error(f"Could not extract folder ID from GDrive Link: {folder_link}")
        sys.exit(1)
        
    # Create the independent Google Sheet
    sheet_name = f"{title} - Image Prompts"
    logger.info(f"Creating independent Google Sheet '{sheet_name}' in folder ID {folder_id}...")
    try:
        new_sheet_id, new_sheet_url = create_sheet_in_folder(sheet_name, folder_id)
    except Exception as e:
        logger.error(f"Failed to create independent Google Sheet: {e}")
        sys.exit(1)
    
    # Initialize API Manager
    api_manager = APIClientManager()
    
    # Generate prompts
    scene_rows = []
    scene_counter = 1
    
    prefix = episode_id[:8]
    
    for i, para in enumerate(paragraphs, 1):
        # Clean paragraph text
        clean_para = para.replace("\n", " ").strip()
        if not clean_para or len(clean_para.split()) < 10:
            continue # Skip very short or empty paragraphs
            
        logger.info(f"Generating prompt for Scene {scene_counter}/{len(paragraphs)}...")
        try:
            image_prompt = api_manager.generate_prompt_for_para(clean_para)
            # Remove any wrapping quotes from LLM
            image_prompt = image_prompt.strip('"\'')
            
            scene_id = f"{prefix}_SC{scene_counter:02d}"
            filename = f"sc{scene_counter:02d}.png"
            
            scene_rows.append([
                scene_id,
                episode_id,
                clean_para,
                image_prompt,
                filename
            ])
            scene_counter += 1
        except Exception as e:
            logger.error(f"Failed to generate prompt for paragraph {i}: {e}")
            # Keep moving or stop? We can continue with a fallback prompt
            image_prompt = "Calm historical scene, oil painting style, soft ambient lighting"
            scene_id = f"{prefix}_SC{scene_counter:02d}"
            filename = f"sc{scene_counter:02d}.png"
            scene_rows.append([scene_id, episode_id, clean_para, image_prompt, filename])
            scene_counter += 1
            
    # Write to the new independent Google Sheet
    logger.info(f"Connecting to the new independent Google Sheet (ID: {new_sheet_id})...")
    try:
        new_sh = gc.open_by_key(new_sheet_id)
        new_ws = new_sh.get_worksheet(0)
        new_ws.update_title('Scene_Prompts')
        
        # Add headers first
        headers_scenes = ["Scene ID", "Episode ID", "Paragraph Excerpt", "Image Prompt", "Image Filename"]
        new_ws.append_row(headers_scenes)
        
        # Format headers
        new_ws.format('A1:E1', {
            'backgroundColor': {'red': 0.1, 'green': 0.5, 'blue': 0.8, 'alpha': 1.0},
            'textFormat': {'foregroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0}, 'bold': True},
            'horizontalAlignment': 'CENTER'
        })
        
        # Batch append scene rows
        new_ws.append_rows(scene_rows)
        logger.info("Successfully uploaded all scenes to the new independent Google Sheet!")
    except Exception as e:
        logger.error(f"Failed to write scenes to the new Google Sheet: {e}")
        sys.exit(1)
        
    # Update the link in the master sheet
    logger.info("Updating GSheet master row with the independent Google Sheet link...")
    try:
        if "Image Prompts (gsheet link)" in headers:
            col_idx = headers.index("Image Prompts (gsheet link)") + 1
            ws.update_cell(target_row_idx, col_idx, new_sheet_url)
            logger.info("Master GSheet updated successfully with prompts link!")
    except Exception as e:
        logger.error(f"Failed to update master GSheet with prompts link: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
