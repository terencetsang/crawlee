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

def load_race_dates_reference():
    """Load race_dates.json as reference for expected race counts"""
    try:
        print("📋 Loading race_dates.json reference...")
        
        with open('race_dates.json', 'r') as f:
            race_dates_data = json.load(f)
        
        print(f"✅ Found {len(race_dates_data)} dates in race_dates.json")
        
        # Display the reference data
        print(f"\n📅 Race dates reference:")
        for date in race_dates_data:
            print(f"   - {date}")
        
        return race_dates_data
        
    except Exception as e:
        print(f"❌ Error loading race_dates.json: {str(e)}")
        return []

def get_current_database_races():
    """Get current races from PocketBase database"""
    try:
        print(f"\n🗄️ Getting current database races...")
        
        client = PocketBase(POCKETBASE_URL)
        client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
        
        # Get all records
        all_records = client.collection(COLLECTION_NAME).get_full_list()
        
        # Group by date and venue
        database_races = {}
        
        for record in all_records:
            date = record.race_date
            venue = record.venue
            race_number = record.race_number
            
            if date not in database_races:
                database_races[date] = {}
            if venue not in database_races[date]:
                database_races[date][venue] = []
            
            database_races[date][venue].append({
                'race_number': race_number,
                'record_id': record.id,
                'scraped_at': record.scraped_at
            })
        
        # Sort race numbers for each venue
        for date in database_races:
            for venue in database_races[date]:
                database_races[date][venue].sort(key=lambda x: x['race_number'])
        
        print(f"✅ Found races for {len(database_races)} dates in database")
        
        return database_races
        
    except Exception as e:
        print(f"❌ Error getting database races: {str(e)}")
        return {}

def check_hkjc_website_for_race_count(race_date, venue):
    """Check HKJC website to determine actual race count for a date/venue"""
    try:
        import requests
        from bs4 import BeautifulSoup
        
        # Convert date format for URL (YYYY-MM-DD to YYYY/MM/DD)
        url_date = race_date.replace('-', '/')
        
        # Try the racing information page
        url = f"https://racing.hkjc.com/racing/information/Chinese/Racing/Racecard.aspx?RaceDate={url_date}&Racecourse={venue}"
        
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for race tab images or race indicators
            race_numbers = set()
            
            # Method 1: Look for race tab images
            for img in soup.find_all('img'):
                src = img.get('src', '')
                if 'racecard_rt_' in src:
                    import re
                    race_match = re.search(r'racecard_rt_(\d+)', src)
                    if race_match:
                        race_numbers.add(int(race_match.group(1)))
            
            # Method 2: Look for race links or text patterns
            if not race_numbers:
                page_text = soup.get_text()
                import re
                
                race_patterns = [
                    r'第\s*(\d+)\s*場',
                    r'Race\s*(\d+)',
                    r'R(\d+)'
                ]
                
                for pattern in race_patterns:
                    matches = re.findall(pattern, page_text)
                    if matches:
                        race_numbers.update([int(m) for m in matches if 1 <= int(m) <= 12])
                        break
            
            if race_numbers:
                max_race = max(race_numbers)
                return max_race, f"Found races 1-{max_race}"
            else:
                return None, "No race indicators found"
        else:
            return None, f"HTTP {response.status_code}"
            
    except Exception as e:
        return None, f"Error: {str(e)}"

def cross_check_race_counts():
    """Cross-check database races with expected counts"""
    print("🏇 HKJC Race Count Cross-Check")
    print("=" * 70)
    
    # Load reference data
    race_dates_reference = load_race_dates_reference()
    
    # Get current database races
    database_races = get_current_database_races()
    
    # Cross-check each date
    print(f"\n🔍 Cross-checking race counts...")
    
    issues_found = []
    correct_dates = []
    
    # Check dates in our database
    for date in sorted(database_races.keys()):
        print(f"\n📅 Checking {date}...")
        
        # Check if this date should exist (is it in race_dates.json?)
        if date not in race_dates_reference:
            print(f"   ⚠️ Date {date} not in race_dates.json reference")
            issues_found.append({
                'type': 'extra_date',
                'date': date,
                'issue': 'Date exists in database but not in race_dates.json'
            })
            continue
        
        # Check each venue for this date
        for venue in database_races[date]:
            races = database_races[date][venue]
            race_numbers = [r['race_number'] for r in races]
            race_count = len(races)
            
            print(f"   🏟️ {venue}: {race_count} races (R{min(race_numbers)}-R{max(race_numbers)})")
            
            # Check for gaps in race numbers
            expected_races = list(range(1, max(race_numbers) + 1))
            missing_races = [r for r in expected_races if r not in race_numbers]
            extra_races = [r for r in race_numbers if r > 12]  # Typically max 12 races
            
            if missing_races:
                print(f"      ❌ Missing races: {missing_races}")
                issues_found.append({
                    'type': 'missing_races',
                    'date': date,
                    'venue': venue,
                    'missing_races': missing_races,
                    'current_races': race_numbers
                })
            
            if extra_races:
                print(f"      ❌ Unexpected high race numbers: {extra_races}")
                issues_found.append({
                    'type': 'extra_races',
                    'date': date,
                    'venue': venue,
                    'extra_races': extra_races
                })
            
            # Verify with HKJC website
            print(f"      🔍 Verifying with HKJC website...")
            actual_count, status = check_hkjc_website_for_race_count(date, venue)
            
            if actual_count:
                if race_count != actual_count:
                    print(f"      ❌ Count mismatch: DB has {race_count}, HKJC shows {actual_count}")
                    issues_found.append({
                        'type': 'count_mismatch',
                        'date': date,
                        'venue': venue,
                        'db_count': race_count,
                        'hkjc_count': actual_count,
                        'db_races': race_numbers
                    })
                else:
                    print(f"      ✅ Count matches HKJC: {actual_count} races")
                    if not missing_races and not extra_races:
                        correct_dates.append(f"{date}_{venue}")
            else:
                print(f"      ⚠️ Could not verify with HKJC: {status}")
    
    # Check for dates in race_dates.json that are missing from database
    for date in race_dates_reference:
        if date not in database_races:
            print(f"\n❌ Missing date: {date} (in race_dates.json but not in database)")
            issues_found.append({
                'type': 'missing_date',
                'date': date,
                'issue': 'Date in race_dates.json but missing from database'
            })
    
    # Summary
    print(f"\n" + "=" * 70)
    print("📊 CROSS-CHECK SUMMARY:")
    print(f"✅ Correct race sessions: {len(correct_dates)}")
    print(f"❌ Issues found: {len(issues_found)}")
    
    if correct_dates:
        print(f"\n✅ Correct sessions:")
        for session in correct_dates:
            print(f"   - {session}")
    
    if issues_found:
        print(f"\n❌ Issues to fix:")
        for issue in issues_found:
            if issue['type'] == 'missing_races':
                print(f"   - {issue['date']} {issue['venue']}: Missing races {issue['missing_races']}")
            elif issue['type'] == 'count_mismatch':
                print(f"   - {issue['date']} {issue['venue']}: DB has {issue['db_count']}, should be {issue['hkjc_count']}")
            elif issue['type'] == 'extra_races':
                print(f"   - {issue['date']} {issue['venue']}: Extra races {issue['extra_races']}")
            elif issue['type'] == 'missing_date':
                print(f"   - {issue['date']}: Missing entire date from database")
            elif issue['type'] == 'extra_date':
                print(f"   - {issue['date']}: Extra date not in race_dates.json")
    
    print("=" * 70)
    
    return issues_found

def create_cleanup_plan(issues_found):
    """Create a plan to fix the identified issues"""
    if not issues_found:
        print("🎉 No issues found - database is perfect!")
        return
    
    print(f"\n📋 CLEANUP PLAN:")
    
    # Group issues by type
    missing_races = [i for i in issues_found if i['type'] == 'missing_races']
    count_mismatches = [i for i in issues_found if i['type'] == 'count_mismatch']
    extra_races = [i for i in issues_found if i['type'] == 'extra_races']
    missing_dates = [i for i in issues_found if i['type'] == 'missing_date']
    extra_dates = [i for i in issues_found if i['type'] == 'extra_date']
    
    if extra_races:
        print(f"\n🗑️ Remove invalid high race numbers:")
        for issue in extra_races:
            print(f"   - Delete {issue['date']} {issue['venue']} races {issue['extra_races']}")
    
    if count_mismatches:
        print(f"\n🔧 Fix race count mismatches:")
        for issue in count_mismatches:
            if issue['db_count'] > issue['hkjc_count']:
                excess = issue['db_count'] - issue['hkjc_count']
                print(f"   - {issue['date']} {issue['venue']}: Remove {excess} excess races")
            else:
                missing = issue['hkjc_count'] - issue['db_count']
                print(f"   - {issue['date']} {issue['venue']}: Extract {missing} missing races")
    
    if missing_races:
        print(f"\n📥 Extract missing races:")
        for issue in missing_races:
            print(f"   - {issue['date']} {issue['venue']}: Extract races {issue['missing_races']}")
    
    if extra_dates:
        print(f"\n🗑️ Remove extra dates:")
        for issue in extra_dates:
            print(f"   - Remove all races for {issue['date']} (not in race_dates.json)")
    
    if missing_dates:
        print(f"\n📥 Extract missing dates:")
        for issue in missing_dates:
            print(f"   - Extract all races for {issue['date']}")

def main():
    """Main cross-check function"""
    issues_found = cross_check_race_counts()
    create_cleanup_plan(issues_found)

if __name__ == '__main__':
    main()
