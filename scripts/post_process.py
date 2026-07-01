import os
import re
import glob
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PostProcess")

def clean_chapter_content(text):
    # Remove YAML frontmatter if present
    text = re.sub(r"^---.*?---", "", text, flags=re.DOTALL)
    
    # Split lines and filter out headings
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip markdown headers (#, ##, ###)
        if stripped.startswith("#"):
            continue
        cleaned_lines.append(line)
        
    return "\n".join(cleaned_lines).strip()

def main():
    chapters_dir = "output/novel/chapters"
    if not os.path.exists(chapters_dir):
        # Try checking in parent if run from inside scripts
        chapters_dir = "../output/novel/chapters"
        if not os.path.exists(chapters_dir):
            # Try current directory as fallback
            chapters_dir = "output/novel/chapters"
            os.makedirs(chapters_dir, exist_ok=True)
            
    logger.info(f"Scanning chapters in: {chapters_dir}")
    md_files = glob.glob(os.path.join(chapters_dir, "*.md"))
    if not md_files:
        logger.error(f"No chapter files found in {chapters_dir}.")
        import sys
        sys.exit(1)
        
    # Sort files naturally (01.md, 02.md... 15.md)
    md_files.sort()
    
    cleaned_chapters = []
    metadata_content = ""
    
    for i, file_path in enumerate(md_files):
        logger.info(f"Processing chapter: {os.path.basename(file_path)}")
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        cleaned = clean_chapter_content(content)
        
        # Check if this is the final chapter containing the metadata block
        if "=== YOUTUBE VIDEO METADATA PACKAGE ===" in cleaned or "=========================================" in cleaned:
            logger.info("Found YouTube Metadata block in final chapter.")
            # Split at the separator
            parts = re.split(r"={10,}", cleaned)
            if len(parts) >= 2:
                # Part 0 is narrative, Part 1 is the metadata header/content
                chapter_narrative = parts[0].strip()
                # Join remaining parts as metadata
                metadata_content = "=========================================\n" + "=========================================\n".join(parts[1:]).strip()
                cleaned = chapter_narrative
                
        cleaned_chapters.append(cleaned)
        
    # Join with the pacing separator
    # The pacing dots '.........' are placed on a blank line as requested
    consolidated_script = "\n\n.........\n\n".join(cleaned_chapters)
    
    # Save output files
    with open("gdoc1.txt", "w", encoding="utf-8") as f:
        f.write(consolidated_script)
    logger.info("Saved clean voiceover script to 'gdoc1.txt'")
    
    if not metadata_content:
        # Fallback metadata if not found
        metadata_content = (
            "=========================================\n"
            "=== YOUTUBE VIDEO METADATA PACKAGE ===\n"
            "=========================================\n"
            "Default Góc Tối Pháp Luật Metadata\n"
        )
        
    with open("gdoc2.txt", "w", encoding="utf-8") as f:
        f.write(metadata_content)
    logger.info("Saved metadata package to 'gdoc2.txt'")

if __name__ == "__main__":
    main()
