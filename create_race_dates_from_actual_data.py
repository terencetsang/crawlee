import json
import os
import glob
import re
from datetime import datetime

def extract_race_dates_from_prompt_files():
    """Extract actual race dates from prompt_text_files directory"""
    try:
        print("📁 Extracting race dates from prompt_text_files directory...")
        
        # Get all prompt files
        prompt_files = glob.glob("prompt_text_files/race_*_with_prompt.txt")
        
        race_dates = set()
        
        for file_path in prompt_files:
            # Extract date from filename: race_2025_04_13_ST_R1_with_prompt.txt
            filename = os.path.basename(file_path)
            match = re.search(r'race_(\d{4})_(\d{2})_(\d{2})_', filename)
            
            if match:
                year, month, day = match.groups()
                date_str = f"{year}-{month}-{day}"
                race_dates.add(date_str)
        
        sorted_dates = sorted(list(race_dates))
        print(f"✅ Found {len(sorted_dates)} unique race dates in prompt files")
        
        return sorted_dates
        
    except Exception as e:
        print(f"❌ Error extracting from prompt files: {str(e)}")
        return []

def extract_race_dates_from_race_data():
    """Extract race dates from race_data directory"""
    try:
        print("📁 Extracting race dates from race_data directory...")
        
        # Get all race data files
        race_files = glob.glob("race_data/race_*_*.json")
        
        race_dates = set()
        
        for file_path in race_files:
            # Extract date from filename: race_2025_04_13_ST_R1.json
            filename = os.path.basename(file_path)
            match = re.search(r'race_(\d{4})_(\d{2})_(\d{2})_', filename)
            
            if match:
                year, month, day = match.groups()
                date_str = f"{year}-{month}-{day}"
                race_dates.add(date_str)
        
        sorted_dates = sorted(list(race_dates))
        print(f"✅ Found {len(sorted_dates)} unique race dates in race_data files")
        
        return sorted_dates
        
    except Exception as e:
        print(f"❌ Error extracting from race_data: {str(e)}")
        return []

def create_comprehensive_race_dates():
    """Create comprehensive race_dates.json from all available data"""
    print("🏇 Creating Comprehensive Race Dates from Actual Data")
    print("=" * 60)
    
    # Extract from both sources
    prompt_dates = extract_race_dates_from_prompt_files()
    race_data_dates = extract_race_dates_from_race_data()
    
    # Combine and deduplicate
    all_dates = set(prompt_dates + race_data_dates)
    sorted_dates = sorted(list(all_dates))
    
    print(f"\n📊 Summary:")
    print(f"   📁 Prompt files dates: {len(prompt_dates)}")
    print(f"   📁 Race data dates: {len(race_data_dates)}")
    print(f"   🎯 Total unique dates: {len(sorted_dates)}")
    
    if not sorted_dates:
        print(f"❌ No race dates found")
        return False
    
    # Backup existing race_dates.json
    try:
        with open('race_dates.json', 'r') as f:
            old_data = json.load(f)
        
        backup_filename = f"race_dates_backup_actual_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_filename, 'w') as f:
            json.dump(old_data, f, indent=2)
        print(f"\n📋 Backed up existing race_dates.json to {backup_filename}")
    except FileNotFoundError:
        print(f"\n📋 No existing race_dates.json to backup")
    except Exception as e:
        print(f"\n⚠️ Could not backup existing file: {e}")
    
    # Save new race_dates.json
    try:
        with open('race_dates.json', 'w') as f:
            json.dump(sorted_dates, f, indent=2)
        
        print(f"\n✅ Created race_dates.json with {len(sorted_dates)} actual race dates")
        
        # Show the dates by month
        print(f"\n📅 Race dates by month:")
        
        current_month = None
        for date in sorted_dates:
            month = date[:7]  # YYYY-MM
            if month != current_month:
                current_month = month
                print(f"\n   📆 {month}:")
            print(f"      - {date}")
        
        # Create detailed summary
        summary = {
            "generated_at": datetime.now().isoformat(),
            "source": "actual_data_files",
            "total_dates": len(sorted_dates),
            "date_range": {
                "start": sorted_dates[0] if sorted_dates else None,
                "end": sorted_dates[-1] if sorted_dates else None
            },
            "monthly_breakdown": {},
            "race_dates": sorted_dates
        }
        
        # Count by month
        for date in sorted_dates:
            month = date[:7]
            if month not in summary["monthly_breakdown"]:
                summary["monthly_breakdown"][month] = 0
            summary["monthly_breakdown"][month] += 1
        
        with open('race_dates_actual_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n📊 Created race_dates_actual_summary.json")
        
        # Show monthly breakdown
        print(f"\n📈 Monthly breakdown:")
        for month, count in summary["monthly_breakdown"].items():
            print(f"   - {month}: {count} race dates")
        
        return True
        
    except Exception as e:
        print(f"❌ Error saving race_dates.json: {e}")
        return False

def main():
    """Main function"""
    success = create_comprehensive_race_dates()
    
    print(f"\n" + "=" * 60)
    if success:
        print(f"🎉 Successfully created race_dates.json from actual data!")
        print(f"📄 Check race_dates.json for the complete list")
        print(f"📊 Check race_dates_actual_summary.json for details")
        print(f"🎯 This file now contains all actual race dates from your data")
    else:
        print(f"❌ Failed to create race_dates.json")
    print("=" * 60)

if __name__ == '__main__':
    main()
