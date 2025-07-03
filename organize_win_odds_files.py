import os
import shutil
import glob
from datetime import datetime

# Define the new folder for win odds trends
WIN_ODDS_FOLDER = "win_odds_data"

def create_win_odds_folder():
    """Create the win_odds_data folder if it doesn't exist"""
    try:
        if not os.path.exists(WIN_ODDS_FOLDER):
            os.makedirs(WIN_ODDS_FOLDER)
            print(f"✅ Created folder: {WIN_ODDS_FOLDER}")
        else:
            print(f"📁 Folder already exists: {WIN_ODDS_FOLDER}")
        return True
    except Exception as e:
        print(f"❌ Error creating folder: {e}")
        return False

def find_win_odds_files():
    """Find all win odds trends JSON files"""
    try:
        print("🔍 Searching for win odds trends files...")
        
        # Search patterns for win odds files
        search_patterns = [
            "win_odds_trends_*.json",
            "race_data/win_odds_trends_*.json",
            "odds_data/win_odds_trends_*.json"
        ]
        
        found_files = []
        
        for pattern in search_patterns:
            files = glob.glob(pattern)
            found_files.extend(files)
        
        # Remove duplicates
        found_files = list(set(found_files))
        
        print(f"✅ Found {len(found_files)} win odds trends files")
        
        if found_files:
            print("📋 Files found:")
            for file_path in sorted(found_files):
                file_size = os.path.getsize(file_path)
                print(f"   - {file_path} ({file_size:,} bytes)")
        
        return found_files
        
    except Exception as e:
        print(f"❌ Error finding files: {e}")
        return []

def move_win_odds_files(files_to_move):
    """Move win odds files to the new folder"""
    try:
        if not files_to_move:
            print("📁 No files to move")
            return True
        
        print(f"\n📦 Moving {len(files_to_move)} files to {WIN_ODDS_FOLDER}...")
        
        moved_count = 0
        failed_count = 0
        
        for file_path in files_to_move:
            try:
                # Get just the filename
                filename = os.path.basename(file_path)
                
                # Destination path
                dest_path = os.path.join(WIN_ODDS_FOLDER, filename)
                
                # Check if destination already exists
                if os.path.exists(dest_path):
                    print(f"   ⚠️ File already exists in destination: {filename}")
                    
                    # Compare file sizes
                    src_size = os.path.getsize(file_path)
                    dest_size = os.path.getsize(dest_path)
                    
                    if src_size == dest_size:
                        print(f"      🗑️ Removing duplicate source file: {file_path}")
                        os.remove(file_path)
                        moved_count += 1
                    else:
                        print(f"      📝 Size mismatch - keeping both files")
                        # Rename with timestamp
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        new_filename = f"{filename.replace('.json', '')}_{timestamp}.json"
                        dest_path = os.path.join(WIN_ODDS_FOLDER, new_filename)
                        shutil.move(file_path, dest_path)
                        print(f"      ✅ Moved to: {dest_path}")
                        moved_count += 1
                else:
                    # Move the file
                    shutil.move(file_path, dest_path)
                    print(f"   ✅ Moved: {filename}")
                    moved_count += 1
                    
            except Exception as e:
                print(f"   ❌ Failed to move {file_path}: {e}")
                failed_count += 1
        
        print(f"\n📊 Move Summary:")
        print(f"   ✅ Successfully moved: {moved_count}")
        print(f"   ❌ Failed to move: {failed_count}")
        
        return failed_count == 0
        
    except Exception as e:
        print(f"❌ Error moving files: {e}")
        return False

def update_extraction_scripts():
    """Update extraction scripts to use the new win_odds_data folder"""
    try:
        print(f"\n🔧 Updating extraction scripts to use {WIN_ODDS_FOLDER} folder...")
        
        # List of scripts that might need updating
        scripts_to_update = [
            "extract_all_odds_data.py",
            "extract_missing_2_races.py", 
            "extract_odds_to_pocketbase.py",
            "hkjc_win_odds_trends.py"
        ]
        
        updated_count = 0
        
        for script_name in scripts_to_update:
            if os.path.exists(script_name):
                try:
                    # Read the script
                    with open(script_name, 'r') as f:
                        content = f.read()
                    
                    # Check if it needs updating
                    needs_update = False
                    original_content = content
                    
                    # Update OUTPUT_DIR references
                    if 'OUTPUT_DIR = os.getenv("OUTPUT_DIR", "odds_data")' in content:
                        content = content.replace(
                            'OUTPUT_DIR = os.getenv("OUTPUT_DIR", "odds_data")',
                            f'OUTPUT_DIR = os.getenv("OUTPUT_DIR", "{WIN_ODDS_FOLDER}")'
                        )
                        needs_update = True
                    
                    if 'OUTPUT_DIR = "odds_data"' in content:
                        content = content.replace(
                            'OUTPUT_DIR = "odds_data"',
                            f'OUTPUT_DIR = "{WIN_ODDS_FOLDER}"'
                        )
                        needs_update = True
                    
                    # Update any hardcoded paths
                    if '"odds_data/' in content:
                        content = content.replace('"odds_data/', f'"{WIN_ODDS_FOLDER}/')
                        needs_update = True
                    
                    if "'odds_data/" in content:
                        content = content.replace("'odds_data/", f"'{WIN_ODDS_FOLDER}/")
                        needs_update = True
                    
                    # Save if updated
                    if needs_update:
                        # Backup original
                        backup_name = f"{script_name}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        shutil.copy2(script_name, backup_name)
                        
                        # Write updated content
                        with open(script_name, 'w') as f:
                            f.write(content)
                        
                        print(f"   ✅ Updated: {script_name} (backup: {backup_name})")
                        updated_count += 1
                    else:
                        print(f"   ℹ️ No update needed: {script_name}")
                        
                except Exception as e:
                    print(f"   ❌ Error updating {script_name}: {e}")
            else:
                print(f"   ⚠️ Script not found: {script_name}")
        
        print(f"\n📊 Script Update Summary:")
        print(f"   ✅ Scripts updated: {updated_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating scripts: {e}")
        return False

def update_env_file():
    """Update .env file to use new win_odds_data folder"""
    try:
        print(f"\n🔧 Updating .env file...")
        
        if not os.path.exists('.env'):
            print(f"   ⚠️ .env file not found")
            return True
        
        # Read .env file
        with open('.env', 'r') as f:
            lines = f.readlines()
        
        # Update OUTPUT_DIR
        updated = False
        for i, line in enumerate(lines):
            if line.startswith('OUTPUT_DIR='):
                old_line = line.strip()
                lines[i] = f'OUTPUT_DIR={WIN_ODDS_FOLDER}\n'
                print(f"   ✅ Updated: {old_line} → OUTPUT_DIR={WIN_ODDS_FOLDER}")
                updated = True
                break
        
        # If OUTPUT_DIR not found, add it
        if not updated:
            lines.append(f'\n# Win odds trends data directory\nOUTPUT_DIR={WIN_ODDS_FOLDER}\n')
            print(f"   ✅ Added: OUTPUT_DIR={WIN_ODDS_FOLDER}")
            updated = True
        
        # Save updated .env file
        if updated:
            # Backup original
            backup_name = f".env.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2('.env', backup_name)
            
            with open('.env', 'w') as f:
                f.writelines(lines)
            
            print(f"   📋 Backup created: {backup_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating .env file: {e}")
        return False

def create_folder_readme():
    """Create a README file in the win_odds_data folder"""
    try:
        readme_path = os.path.join(WIN_ODDS_FOLDER, "README.md")
        
        readme_content = f"""# Win Odds Trends Data

This folder contains HKJC 獨贏賠率走勢 (Win Odds Trends) JSON files.

## File Format
- **Filename**: `win_odds_trends_YYYY_MM_DD_VENUE_RX.json`
- **Content**: Win odds trends data with merged timestamps

## Data Structure
Each JSON file contains:
- `race_info`: Race metadata (date, venue, race number, source URL)
- `horses_data`: Array of horse data with win odds trends
- `extraction_summary`: Extraction statistics

## Coverage
- **Dates**: {datetime.now().strftime('%Y-%m-%d')} (when organized)
- **Venues**: ST (Sha Tin), HV (Happy Valley)
- **Data Type**: Win odds trends with time progression

## Usage
These files are automatically generated by the HKJC odds extraction scripts and uploaded to PocketBase.

Generated on: {datetime.now().isoformat()}
"""
        
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        
        print(f"📄 Created: {readme_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error creating README: {e}")
        return False

def main():
    """Main function to organize win odds files"""
    print("🏇 HKJC Win Odds Trends File Organizer")
    print("=" * 60)
    print(f"Organizing win odds trends files into: {WIN_ODDS_FOLDER}")
    print("=" * 60)
    
    # Step 1: Create the new folder
    if not create_win_odds_folder():
        print("❌ Failed to create folder")
        return
    
    # Step 2: Find all win odds files
    files_to_move = find_win_odds_files()
    
    # Step 3: Move the files
    move_success = move_win_odds_files(files_to_move)
    
    # Step 4: Update extraction scripts
    update_success = update_extraction_scripts()
    
    # Step 5: Update .env file
    env_success = update_env_file()
    
    # Step 6: Create README
    readme_success = create_folder_readme()
    
    # Summary
    print(f"\n" + "=" * 60)
    print("📊 ORGANIZATION SUMMARY:")
    print(f"📁 Folder creation: {'✅ Success' if os.path.exists(WIN_ODDS_FOLDER) else '❌ Failed'}")
    print(f"📦 File moving: {'✅ Success' if move_success else '❌ Failed'}")
    print(f"🔧 Script updates: {'✅ Success' if update_success else '❌ Failed'}")
    print(f"⚙️ .env update: {'✅ Success' if env_success else '❌ Failed'}")
    print(f"📄 README creation: {'✅ Success' if readme_success else '❌ Failed'}")
    
    if all([move_success, update_success, env_success, readme_success]):
        print(f"\n🎉 All win odds trends files organized successfully!")
        print(f"📁 Location: {WIN_ODDS_FOLDER}/")
        print(f"🔧 Scripts updated to use new folder")
        print(f"⚙️ .env file updated")
    else:
        print(f"\n⚠️ Some operations failed - check the logs above")
    
    print("=" * 60)

if __name__ == '__main__':
    main()
