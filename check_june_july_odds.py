import asyncio
import json
import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pocketbase import PocketBase
from bs4 import BeautifulSoup

# Load environment variables from .env file
load_dotenv()

# PocketBase configuration
POCKETBASE_URL = os.getenv("POCKETBASE_URL")
POCKETBASE_EMAIL = os.getenv("POCKETBASE_EMAIL")
POCKETBASE_PASSWORD = os.getenv("POCKETBASE_PASSWORD")
COLLECTION_NAME = "race_odds"

def check_odds_availability(race_date, venue, race_number):
    """Check if odds data is available for a specific race"""
    try:
        url = f"https://bet.hkjc.com/ch/racing/pwin/{race_date}/{venue}/{race_number}"
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }, timeout=10)
        
        if response.status_code == 200:
            if "You need to enable JavaScript" in response.text:
                # Check if the page contains the expected date
                soup = BeautifulSoup(response.text, 'html.parser')
                page_text = soup.get_text()
                
                date_formatted = race_date.replace('-', '/')
                if date_formatted in page_text:
                    return True
        
        return False
    except:
        return False

def get_june_july_dates():
    """Generate June and July 2025 dates to check"""
    dates_to_check = []
    
    # June 2025 dates
    june_dates = []
    for day in range(1, 31):  # June has 30 days
        date_str = f"2025-06-{day:02d}"
        june_dates.append(date_str)
    
    # July 2025 dates (up to today, July 2nd)
    july_dates = []
    for day in range(1, 3):  # July 1st and 2nd
        date_str = f"2025-07-{day:02d}"
        july_dates.append(date_str)
    
    dates_to_check.extend(june_dates)
    dates_to_check.extend(july_dates)
    
    return dates_to_check

def get_existing_races_from_db():
    """Get existing races from PocketBase database"""
    try:
        print("📊 Getting existing races from database...")
        
        client = PocketBase(POCKETBASE_URL)
        client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
        
        all_records = client.collection(COLLECTION_NAME).get_full_list()
        
        existing_races = {}
        race_sessions = {}
        
        for record in all_records:
            race_key = f"{record.race_date}_{record.venue}_{record.race_number}"
            existing_races[race_key] = record.id
            
            session_key = f"{record.race_date}_{record.venue}"
            if session_key not in race_sessions:
                race_sessions[session_key] = []
            race_sessions[session_key].append(record.race_number)
        
        print(f"✅ Found {len(all_records)} existing races in database")
        
        # Show existing race sessions
        print(f"\n📅 Existing race sessions:")
        for session_key in sorted(race_sessions.keys()):
            date, venue = session_key.split('_')
            race_count = len(race_sessions[session_key])
            race_numbers = sorted(race_sessions[session_key])
            print(f"   - {date} {venue}: {race_count} races (R{min(race_numbers)}-R{max(race_numbers)})")
        
        return existing_races, race_sessions
        
    except Exception as e:
        print(f"❌ Error getting existing races: {str(e)}")
        return {}, {}

def check_available_odds_data():
    """Check what odds data is available for June and July 2025"""
    print("🏇 HKJC June/July 2025 Odds Availability Checker")
    print("=" * 70)
    
    # Get dates to check
    dates_to_check = get_june_july_dates()
    print(f"🔍 Checking odds availability for {len(dates_to_check)} dates...")
    
    # Get existing races from database
    existing_races, existing_sessions = get_existing_races_from_db()
    
    # Check availability for each date
    available_sessions = []
    missing_races = []
    unavailable_dates = []
    
    print(f"\n🔍 Checking odds availability...")
    
    for date in dates_to_check:
        print(f"\n📅 Checking {date}...")
        
        date_has_races = False
        
        for venue in ['ST', 'HV']:
            # Check if any races exist for this venue on this date
            races_found = 0
            max_races_to_check = 12
            
            for race_number in range(1, max_races_to_check + 1):
                if check_odds_availability(date, venue, race_number):
                    races_found = race_number
                    date_has_races = True
                else:
                    break
            
            if races_found > 0:
                session_key = f"{date}_{venue}"
                available_sessions.append({
                    'date': date,
                    'venue': venue,
                    'total_races': races_found
                })
                
                print(f"   ✅ {venue}: {races_found} races available")
                
                # Check which races we have vs missing
                existing_race_numbers = existing_sessions.get(session_key, [])
                
                for race_number in range(1, races_found + 1):
                    race_key = f"{date}_{venue}_{race_number}"
                    if race_key not in existing_races:
                        missing_races.append((date, venue, race_number))
                
                if existing_race_numbers:
                    existing_count = len(existing_race_numbers)
                    missing_count = races_found - existing_count
                    print(f"      📊 In DB: {existing_count}, Missing: {missing_count}")
                else:
                    print(f"      📊 In DB: 0, Missing: {races_found}")
            else:
                print(f"   ❌ {venue}: No races available")
        
        if not date_has_races:
            unavailable_dates.append(date)
    
    # Summary
    print(f"\n" + "=" * 70)
    print("📋 AVAILABILITY SUMMARY:")
    print(f"✅ Available race sessions: {len(available_sessions)}")
    print(f"❌ Missing races to extract: {len(missing_races)}")
    print(f"⚠️ Dates with no races: {len(unavailable_dates)}")
    
    if available_sessions:
        print(f"\n📅 Available race sessions:")
        for session in available_sessions:
            print(f"   - {session['date']} {session['venue']}: {session['total_races']} races")
    
    if missing_races:
        print(f"\n⚠️ Missing races to extract:")
        # Group by date for better readability
        missing_by_date = {}
        for date, venue, race_number in missing_races:
            if date not in missing_by_date:
                missing_by_date[date] = {}
            if venue not in missing_by_date[date]:
                missing_by_date[date][venue] = []
            missing_by_date[date][venue].append(race_number)
        
        for date in sorted(missing_by_date.keys()):
            for venue in sorted(missing_by_date[date].keys()):
                race_numbers = sorted(missing_by_date[date][venue])
                print(f"   - {date} {venue}: Races {race_numbers}")
    
    if unavailable_dates:
        print(f"\n❌ Dates with no available races:")
        for date in unavailable_dates:
            print(f"   - {date}")
    
    # Check April dates from race_dates.json
    print(f"\n🔍 Checking April 2025 dates from race_dates.json...")
    try:
        with open('race_dates.json', 'r') as f:
            april_dates = json.load(f)
        
        april_available = []
        for date in april_dates:
            print(f"📅 Checking {date}...")
            date_has_races = False
            
            for venue in ['ST', 'HV']:
                if check_odds_availability(date, venue, 1):
                    date_has_races = True
                    print(f"   ✅ {venue}: Odds available")
                else:
                    print(f"   ❌ {venue}: No odds available")
            
            if date_has_races:
                april_available.append(date)
        
        if april_available:
            print(f"\n✅ April dates with available odds: {april_available}")
        else:
            print(f"\n❌ No April 2025 odds data available (too old)")
    
    except Exception as e:
        print(f"❌ Error checking April dates: {str(e)}")
    
    print("=" * 70)
    
    return missing_races, available_sessions

def create_missing_races_list(missing_races):
    """Create a JSON file with missing races for easy extraction"""
    try:
        if missing_races:
            missing_data = {
                "generated_at": datetime.now().isoformat(),
                "total_missing": len(missing_races),
                "missing_races": []
            }
            
            for date, venue, race_number in missing_races:
                missing_data["missing_races"].append({
                    "race_date": date,
                    "venue": venue,
                    "race_number": race_number,
                    "url": f"https://bet.hkjc.com/ch/racing/pwin/{date}/{venue}/{race_number}"
                })
            
            with open('missing_races.json', 'w') as f:
                json.dump(missing_data, f, indent=2)
            
            print(f"💾 Created missing_races.json with {len(missing_races)} races to extract")
            return True
    except Exception as e:
        print(f"❌ Error creating missing races file: {str(e)}")
        return False

def main():
    """Main function to check June/July odds availability"""
    missing_races, available_sessions = check_available_odds_data()
    
    if missing_races:
        create_missing_races_list(missing_races)
        print(f"\n🔄 Next step: Run extraction script to get {len(missing_races)} missing races")
    else:
        print(f"\n🎉 All available June/July 2025 odds data is already extracted!")

if __name__ == '__main__':
    main()
