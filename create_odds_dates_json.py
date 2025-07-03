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

def get_odds_dates_from_database():
    """Get actual odds dates from PocketBase database"""
    try:
        print("🗄️ Getting odds dates from PocketBase database...")
        
        client = PocketBase(POCKETBASE_URL)
        client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
        
        # Get all records
        all_records = client.collection(COLLECTION_NAME).get_full_list()
        
        # Extract unique race dates
        odds_dates = set()
        race_sessions = {}
        
        for record in all_records:
            race_date = record.race_date
            venue = record.venue
            race_number = record.race_number
            
            odds_dates.add(race_date)
            
            # Track race sessions
            session_key = f"{race_date}_{venue}"
            if session_key not in race_sessions:
                race_sessions[session_key] = []
            race_sessions[session_key].append(race_number)
        
        # Sort dates
        sorted_dates = sorted(list(odds_dates))
        
        print(f"✅ Found {len(sorted_dates)} unique odds dates in database:")
        for date in sorted_dates:
            print(f"   - {date}")
        
        print(f"\n📊 Odds race sessions breakdown:")
        for session_key in sorted(race_sessions.keys()):
            date, venue = session_key.split('_')
            race_numbers = sorted(race_sessions[session_key])
            venue_name = "Sha Tin" if venue == "ST" else "Happy Valley"
            print(f"   - {date} {venue} ({venue_name}): {len(race_numbers)} races (R{min(race_numbers)}-R{max(race_numbers)})")
        
        return sorted_dates, race_sessions
        
    except Exception as e:
        print(f"❌ Error getting odds dates from database: {str(e)}")
        return [], {}

def create_odds_dates_json():
    """Create odds_dates.json specifically for odds data"""
    print("🏇 HKJC Odds Dates JSON Creator")
    print("=" * 60)
    print("Creating odds_dates.json for 獨贏賠率走勢 (Win Odds Trends) data")
    print("=" * 60)
    
    # Get odds dates from database
    odds_dates, race_sessions = get_odds_dates_from_database()
    
    if not odds_dates:
        print("❌ No odds dates found in database")
        return False
    
    # Create odds_dates.json
    try:
        with open('odds_dates.json', 'w') as f:
            json.dump(odds_dates, f, indent=2)
        
        print(f"\n✅ Created odds_dates.json with {len(odds_dates)} dates")
        
        # Show the dates
        print(f"\n📅 Odds dates:")
        for date in odds_dates:
            print(f"   - {date}")
        
        # Create detailed summary
        summary = {
            "generated_at": datetime.now().isoformat(),
            "data_type": "win_odds_trends",
            "source": "pocketbase_race_odds_collection",
            "total_dates": len(odds_dates),
            "total_races": sum(len(races) for races in race_sessions.values()),
            "date_range": {
                "start": odds_dates[0] if odds_dates else None,
                "end": odds_dates[-1] if odds_dates else None
            },
            "race_sessions": {},
            "odds_dates": odds_dates
        }
        
        # Add race session details
        for session_key, race_numbers in race_sessions.items():
            date, venue = session_key.split('_')
            venue_name = "Sha Tin" if venue == "ST" else "Happy Valley"
            
            summary["race_sessions"][session_key] = {
                "date": date,
                "venue": venue,
                "venue_name": venue_name,
                "total_races": len(race_numbers),
                "race_numbers": sorted(race_numbers)
            }
        
        with open('odds_dates_summary.json', 'w') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Created odds_dates_summary.json")
        
        # Show summary stats
        print(f"\n📈 Odds Data Summary:")
        print(f"   📅 Total odds dates: {summary['total_dates']}")
        print(f"   🏇 Total races with odds: {summary['total_races']}")
        print(f"   🏟️ Total race sessions: {len(race_sessions)}")
        print(f"   📊 Date range: {summary['date_range']['start']} to {summary['date_range']['end']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating odds_dates.json: {e}")
        return False

def compare_with_race_dates():
    """Compare odds_dates.json with race_dates.json"""
    try:
        print(f"\n🔍 Comparing odds dates with race entries dates...")
        
        # Load race_dates.json
        try:
            with open('race_dates.json', 'r') as f:
                race_dates = json.load(f)
            print(f"📋 race_dates.json: {len(race_dates)} dates (race entries)")
        except FileNotFoundError:
            print(f"⚠️ race_dates.json not found")
            return
        
        # Load odds_dates.json
        try:
            with open('odds_dates.json', 'r') as f:
                odds_dates = json.load(f)
            print(f"📊 odds_dates.json: {len(odds_dates)} dates (odds data)")
        except FileNotFoundError:
            print(f"❌ odds_dates.json not found")
            return
        
        # Compare
        race_dates_set = set(race_dates)
        odds_dates_set = set(odds_dates)
        
        # Find overlaps and differences
        common_dates = race_dates_set & odds_dates_set
        only_race_entries = race_dates_set - odds_dates_set
        only_odds = odds_dates_set - race_dates_set
        
        print(f"\n📊 Comparison Results:")
        print(f"   ✅ Common dates (both entries & odds): {len(common_dates)}")
        print(f"   📋 Only race entries: {len(only_race_entries)}")
        print(f"   📈 Only odds data: {len(only_odds)}")
        
        if common_dates:
            print(f"\n✅ Dates with both race entries and odds data:")
            for date in sorted(common_dates):
                print(f"   - {date}")
        
        if only_race_entries:
            print(f"\n📋 Dates with only race entries (no odds):")
            for date in sorted(only_race_entries):
                print(f"   - {date}")
        
        if only_odds:
            print(f"\n📈 Dates with only odds data (no race entries):")
            for date in sorted(only_odds):
                print(f"   - {date}")
        
        # Create comparison summary
        comparison = {
            "generated_at": datetime.now().isoformat(),
            "race_entries_dates": len(race_dates),
            "odds_dates": len(odds_dates),
            "common_dates": len(common_dates),
            "only_race_entries": len(only_race_entries),
            "only_odds": len(only_odds),
            "details": {
                "common_dates": sorted(list(common_dates)),
                "only_race_entries": sorted(list(only_race_entries)),
                "only_odds": sorted(list(only_odds))
            }
        }
        
        with open('dates_comparison.json', 'w') as f:
            json.dump(comparison, f, indent=2)
        
        print(f"\n📊 Created dates_comparison.json")
        
    except Exception as e:
        print(f"❌ Error comparing dates: {e}")

def main():
    """Main function"""
    success = create_odds_dates_json()
    
    if success:
        compare_with_race_dates()
    
    print(f"\n" + "=" * 60)
    if success:
        print(f"🎉 Successfully created odds_dates.json!")
        print(f"📄 odds_dates.json: Contains dates with 獨贏賠率走勢 (Win Odds Trends)")
        print(f"📋 race_dates.json: Contains all race entries dates")
        print(f"📊 odds_dates_summary.json: Detailed odds data breakdown")
        print(f"🔍 dates_comparison.json: Comparison between both files")
        print(f"\n🎯 Use odds_dates.json for odds-related operations")
        print(f"🎯 Use race_dates.json for race entries operations")
    else:
        print(f"❌ Failed to create odds_dates.json")
    print("=" * 60)

if __name__ == '__main__':
    main()
