"""
Script to split large JSON files into smaller chunks for GitHub compatibility.
Files larger than 500KB will be split into multiple parts.
"""
import json
import os
import shutil
from pathlib import Path

# Size threshold for splitting (80MB)
SPLIT_THRESHOLD = 80 * 1024 * 1024  # 80 MB

# Directory containing law files
LAWS_DIR = Path("scraper/laws")

def split_json_file(file_path: Path, chunk_size: int = 100):
    """
    Split a large JSON array file into smaller chunks.
    
    Args:
        file_path: Path to the JSON file to split
        chunk_size: Number of articles per chunk
    """
    print(f"Processing {file_path.name}...")
    
    # Read the original file
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        print(f"  WARNING: {file_path.name} is not an array, skipping...")
        return
    
    total_items = len(data)
    file_size = file_path.stat().st_size
    
    # Only split if file is larger than threshold
    if file_size < SPLIT_THRESHOLD:
        print(f"  OK: {file_path.name} ({file_size / 1024:.1f} KB) is under threshold, skipping...")
        return
    
    print(f"  SPLITTING: {file_path.name} ({file_size / 1024:.1f} KB, {total_items} items) into chunks...")
    
    # Get base name without extension
    base_name = file_path.stem
    extension = file_path.suffix
    
    # Create a backup directory
    backup_dir = file_path.parent / "backup"
    backup_dir.mkdir(exist_ok=True)
    
    # Backup original file
    backup_path = backup_dir / file_path.name
    shutil.copy2(file_path, backup_path)
    print(f"  BACKUP: Created {backup_path}")
    
    # Split into chunks
    chunks = []
    for i in range(0, total_items, chunk_size):
        chunk = data[i:i + chunk_size]
        chunk_num = (i // chunk_size) + 1
        total_chunks = (total_items + chunk_size - 1) // chunk_size
        
        # Create chunk filename
        chunk_filename = f"{base_name}_part{chunk_num:02d}_of_{total_chunks:02d}{extension}"
        chunk_path = file_path.parent / chunk_filename
        
        # Write chunk
        with open(chunk_path, 'w', encoding='utf-8') as f:
            json.dump(chunk, f, ensure_ascii=False, indent=4)
        
        chunk_size_kb = chunk_path.stat().st_size / 1024
        chunks.append(chunk_path)
        print(f"    CREATED: {chunk_filename} ({chunk_size_kb:.1f} KB, {len(chunk)} items)")
    
    # Create a manifest file listing all chunks
    manifest = {
        "original_file": file_path.name,
        "total_items": total_items,
        "total_chunks": len(chunks),
        "chunks": [chunk.name for chunk in chunks]
    }
    
    manifest_path = file_path.parent / f"{base_name}_manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    print(f"  MANIFEST: Created {manifest_path.name}")
    
    # Optionally remove original file (commented out for safety)
    # file_path.unlink()
    # print(f"  DELETED: Original file removed (backup available)")
    
    return chunks, manifest_path

def main():
    """Main function to process all JSON files in the laws directory."""
    print("=" * 60)
    print("Large JSON File Splitter")
    print("=" * 60)
    print()
    
    json_files = list(LAWS_DIR.glob("*.json"))
    
    if not json_files:
        print("No JSON files found in scraper/laws/")
        return
    
    print(f"Found {len(json_files)} JSON files to check...")
    print()
    
    split_files = []
    
    for file_path in sorted(json_files):
        # Skip manifest files
        if "_manifest.json" in file_path.name or "_part" in file_path.name:
            continue
        
        try:
            result = split_json_file(file_path)
            if result:
                split_files.append((file_path, result))
        except Exception as e:
            print(f"  ERROR: Processing {file_path.name}: {e}")
    
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    
    if split_files:
        print(f"SUCCESS: Split {len(split_files)} files into chunks")
        print("\nSplit files:")
        for file_path, (chunks, manifest) in split_files:
            print(f"  - {file_path.name} -> {len(chunks)} chunks")
    else:
        print("SUCCESS: No files needed splitting (all under threshold)")
    
    print()
    print("Note: Original files are backed up in scraper/laws/backup/")
    print("To restore originals, delete split files and restore from backup")

if __name__ == "__main__":
    main()

