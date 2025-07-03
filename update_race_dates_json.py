import json
import os
from datetime import datetime
from dotenv import load_dotenv
from pocketbase import PocketBase

# Load environment variables from .env file
load_dotenv()

# PocketBase configuration
POCKETBASE_URL = os.getenv("POCKETBASE_URL")
POCKETBASE_EMAIL = os.getenv("POCKETBASE_EMAIL")
POCKETBASE_PASSWORD = os.getenv("POCKETBASE_PASSWORD")
COLLECTION_NAME = "race_odds"

def get_actual_race_dates_from_db():
    """Get actual race dates from the database"""
    try:
        print("🔍 Getting actual race dates from PocketBase database...")
        
        # Initialize PocketBase client
        client = PocketBase(POCKETBASE_URL)
        client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
        
        # Get all records
        all_records = client.collection(COLLECTION_NAME).get_full_list()
        
        # Extract unique race dates
        race_dates = set()
        race_sessions = {}
        
        for record in all_records:
            race_date = record.race_date
            venue = record.venue
            race_number = record.race_number
            
            race_dates.add(race_date)
            
            # Track race sessions
            session_key = f"{race_date}_{venue}"
            if session_key not in race_sessions:
                race_sessions[session_key] = []
            race_sessions[session_key].append(race_number)
        
        # Sort dates
        sorted_dates = sorted(list(race_dates))
        
        print(f"✅ Found {len(sorted_dates)} unique race dates in database:")
        for date in sorted_dates:
            print(f"   - {date}")
        
        print(f"\n📊 Race sessions breakdown:")
        for session_key in sorted(race_sessions.keys()):
            date, venue = session_key.split('_')
            race_numbers = sorted(race_sessions[session_key])
            print(f"   - {date} {venue}: {len(race_numbers)} races (R{min(race_numbers)}-R{max(race_numbers)})")
        
        return sorted_dates, race_sessions
        
    except Exception as e:
        print(f"❌ Error getting race dates from database: {str(e)}")
        return [], {}

def analyze_race_completeness(race_sessions):
    """Analyze completeness of race data"""
    print(f"\n🔍 Analyzing race data completeness...")
    
    complete_sessions = []
    incomplete_sessions = []
    missing_races = []
    
    for session_key, race_numbers in race_sessions.items():
        date, venue = session_key.split('_')
        race_numbers = sorted(race_numbers)
        
        # Check for gaps in race numbers
        expected_races = list(range(1, max(race_numbers) + 1))
        missing_in_session = [r for r in expected_races if r not in race_numbers]
        
        if missing_in_session:
            incomplete_sessions.append({
                'session': session_key,
                'date': date,
                'venue': venue,
                'total_races': len(race_numbers),
                'missing_races': missing_in_session,
                'race_numbers': race_numbers
            })
            
            # Add to missing races list
            for race_num in missing_in_session:
                missing_races.append((date, venue, race_num))
        else:
            complete_sessions.append({
                'session': session_key,
                'date': date,
                'venue': venue,
                'total_races': len(race_numbers)
            })
    
    print(f"✅ Complete sessions: {len(complete_sessions)}")
    print(f"⚠️ Incomplete sessions: {len(incomplete_sessions)}")
    print(f"❌ Total missing races: {len(missing_races)}")
    
    if incomplete_sessions:
        print(f"\n⚠️ Incomplete sessions:")
        for session in incomplete_sessions:
            print(f"   - {session['date']} {session['venue']}: Missing races {session['missing_races']}")
    
    return missing_races

def update_race_dates_json(race_dates):
    """Update race_dates.json with actual race dates"""
    try:
        print(f"\n💾 Updating race_dates.json with {len(race_dates)} actual race dates...")
        
        # Backup existing file
        if os.path.exists('race_dates.json'):
            with open('race_dates.json', 'r') as f:
                old_data = json.load(f)
            
            with open('race_dates_backup.json', 'w') as f:
                json.dump(old_data, f, indent=2)
            print(f"📋 Backed up existing race_dates.json to race_dates_backup.json")
        
        # Write new race dates
        with open('race_dates.json', 'w') as f:
            json.dump(race_dates, f, indent=2)
        
        print(f"✅ Successfully updated race_dates.json")
        
        # Show the new content
        print(f"\n📄 New race_dates.json content:")
        with open('race_dates.json', 'r') as f:
            content = f.read()
            print(content)
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating race_dates.json: {str(e)}")
        return False

def create_race_sessions_summary(race_sessions):
    """Create a detailed race sessions summary file"""
    try:
        print(f"\n📊 Creating detailed race sessions summary...")
        
        summary = {
            "generated_at": datetime.now().isoformat(),
            "total_sessions": len(race_sessions),
            "total_races": sum(len(races) for races in race_sessions.values()),
            "race_sessions": {}
        }
        
        for session_key, race_numbers in sorted(race_sessions.items()):
            date, venue = session_key.split('_')
            race_numbers = sorted(race_numbers)
            
            # Check for missing races
            expected_races = list(range(1, max(race_numbers) + 1))
            missing_races = [r for r in expected_races if r not in race_numbers]
            
            summary["race_sessions"][session_key] = {
                "date": date,
                "venue": venue,
                "venue_name": "Sha Tin" if venue == "ST" else "Happy Valley",
                "total_races": len(race_numbers),
                "race_numbers": race_numbers,
                "missing_races": missing_races,
                "is_complete": len(missing_races) == 0,
                "expected_total": max(race_numbers) if race_numbers else 0
            }
        
        # Save summary
        with open('race_sessions_summary.json', 'w') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Created race_sessions_summary.json")
        
        # Print summary stats
        complete_sessions = sum(1 for s in summary["race_sessions"].values() if s["is_complete"])
        incomplete_sessions = len(summary["race_sessions"]) - complete_sessions
        total_missing = sum(len(s["missing_races"]) for s in summary["race_sessions"].values())
        
        print(f"\n📈 Summary Statistics:")
        print(f"   📅 Total race dates: {len(set(s['date'] for s in summary['race_sessions'].values()))}")
        print(f"   🏟️ Total race sessions: {summary['total_sessions']}")
        print(f"   🏇 Total races extracted: {summary['total_races']}")
        print(f"   ✅ Complete sessions: {complete_sessions}")
        print(f"   ⚠️ Incomplete sessions: {incomplete_sessions}")
        print(f"   ❌ Missing races: {total_missing}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating race sessions summary: {str(e)}")
        return False

def main():
    """Main function to update race_dates.json and analyze data"""
    print("🏇 HKJC Race Dates JSON Updater")
    print("=" * 60)
    
    # Step 1: Get actual race dates from database
    race_dates, race_sessions = get_actual_race_dates_from_db()
    
    if not race_dates:
        print("❌ No race dates found in database")
        return
    
    # Step 2: Analyze race completeness
    missing_races = analyze_race_completeness(race_sessions)
    
    # Step 3: Update race_dates.json
    update_success = update_race_dates_json(race_dates)
    
    # Step 4: Create detailed summary
    summary_success = create_race_sessions_summary(race_sessions)
    
    # Step 5: Final recommendations
    print(f"\n" + "=" * 60)
    print("🎯 RECOMMENDATIONS:")
    
    if missing_races:
        print(f"1. 🔄 Re-extract {len(missing_races)} missing races:")
        for date, venue, race_num in missing_races[:5]:  # Show first 5
            print(f"   - {date} {venue} Race {race_num}")
        if len(missing_races) > 5:
            print(f"   ... and {len(missing_races) - 5} more")
    else:
        print(f"1. ✅ All race data is complete!")
    
    print(f"2. 📄 race_dates.json now contains actual race dates from database")
    print(f"3. 📊 Check race_sessions_summary.json for detailed breakdown")
    
    if update_success and summary_success:
        print(f"4. 🎉 All files updated successfully!")
    
    print("=" * 60)

if __name__ == '__main__':
    main()
