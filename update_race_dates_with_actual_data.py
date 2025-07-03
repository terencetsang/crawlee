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

def get_actual_race_data_from_database():
    """Get actual race data from PocketBase database"""
    try:
        print("🗄️ Getting actual race data from database...")
        
        client = PocketBase(POCKETBASE_URL)
        client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
        
        # Get all records
        all_records = client.collection(COLLECTION_NAME).get_full_list()
        
        # Group by date and venue
        race_data = {}
        
        for record in all_records:
            date = record.race_date
            venue = record.venue
            race_number = record.race_number
            
            if date not in race_data:
                race_data[date] = {}
            if venue not in race_data[date]:
                race_data[date][venue] = []
            
            race_data[date][venue].append({
                'race_number': race_number,
                'record_id': record.id,
                'scraped_at': record.scraped_at
            })
        
        # Sort and analyze
        for date in race_data:
            for venue in race_data[date]:
                race_data[date][venue].sort(key=lambda x: x['race_number'])
        
        print(f"✅ Found race data for {len(race_data)} dates")
        
        return race_data
        
    except Exception as e:
        print(f"❌ Error getting race data: {str(e)}")
        return {}

def verify_race_counts_with_hkjc(race_data):
    """Verify race counts with HKJC website"""
    try:
        import requests
        from bs4 import BeautifulSoup
        import re
        
        print(f"\n🔍 Verifying race counts with HKJC website...")
        
        verified_data = {}
        
        for date in sorted(race_data.keys()):
            print(f"\n📅 Verifying {date}...")
            verified_data[date] = {}
            
            for venue in race_data[date]:
                races = race_data[date][venue]
                current_count = len(races)
                race_numbers = [r['race_number'] for r in races]
                
                print(f"   🏟️ {venue}: {current_count} races (R{min(race_numbers)}-R{max(race_numbers)})")
                
                # Check with HKJC website
                url_date = date.replace('-', '/')
                url = f"https://racing.hkjc.com/racing/information/Chinese/Racing/Racecard.aspx?RaceDate={url_date}&Racecourse={venue}"
                
                try:
                    response = requests.get(url, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }, timeout=15)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Look for race indicators
                        race_indicators = set()
                        
                        # Method 1: Race tab images
                        for img in soup.find_all('img'):
                            src = img.get('src', '')
                            if 'racecard_rt_' in src:
                                race_match = re.search(r'racecard_rt_(\d+)', src)
                                if race_match:
                                    race_indicators.add(int(race_match.group(1)))
                        
                        # Method 2: Text patterns
                        if not race_indicators:
                            page_text = soup.get_text()
                            patterns = [r'第\s*(\d+)\s*場', r'Race\s*(\d+)', r'R(\d+)']
                            
                            for pattern in patterns:
                                matches = re.findall(pattern, page_text)
                                if matches:
                                    race_indicators.update([int(m) for m in matches if 1 <= int(m) <= 12])
                                    break
                        
                        if race_indicators:
                            hkjc_count = max(race_indicators)
                            
                            if current_count == hkjc_count:
                                print(f"      ✅ Verified: {hkjc_count} races (matches database)")
                                verified_data[date][venue] = {
                                    'race_count': hkjc_count,
                                    'status': 'verified',
                                    'race_numbers': race_numbers
                                }
                            else:
                                print(f"      ⚠️ Mismatch: DB has {current_count}, HKJC shows {hkjc_count}")
                                verified_data[date][venue] = {
                                    'race_count': hkjc_count,
                                    'status': 'mismatch',
                                    'db_count': current_count,
                                    'hkjc_count': hkjc_count,
                                    'race_numbers': race_numbers
                                }
                        else:
                            print(f"      ❌ Could not verify with HKJC")
                            verified_data[date][venue] = {
                                'race_count': current_count,
                                'status': 'unverified',
                                'race_numbers': race_numbers
                            }
                    else:
                        print(f"      ❌ HKJC request failed: HTTP {response.status_code}")
                        verified_data[date][venue] = {
                            'race_count': current_count,
                            'status': 'request_failed',
                            'race_numbers': race_numbers
                        }
                        
                except Exception as e:
                    print(f"      ❌ Error checking HKJC: {str(e)}")
                    verified_data[date][venue] = {
                        'race_count': current_count,
                        'status': 'error',
                        'race_numbers': race_numbers
                    }
        
        return verified_data
        
    except Exception as e:
        print(f"❌ Error verifying with HKJC: {str(e)}")
        return {}

def update_race_dates_json(verified_data):
    """Update race_dates.json with actual available dates"""
    try:
        print(f"\n💾 Updating race_dates.json with actual race dates...")
        
        # Backup existing file
        if os.path.exists('race_dates.json'):
            with open('race_dates.json', 'r') as f:
                old_data = json.load(f)
            
            backup_filename = f"race_dates_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_filename, 'w') as f:
                json.dump(old_data, f, indent=2)
            print(f"📋 Backed up old race_dates.json to {backup_filename}")
        
        # Create new race_dates.json with actual dates
        actual_dates = sorted(verified_data.keys())
        
        with open('race_dates.json', 'w') as f:
            json.dump(actual_dates, f, indent=2)
        
        print(f"✅ Updated race_dates.json with {len(actual_dates)} actual dates")
        
        # Show the new content
        print(f"\n📄 New race_dates.json content:")
        for date in actual_dates:
            print(f"   - {date}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating race_dates.json: {str(e)}")
        return False

def create_detailed_race_summary(verified_data):
    """Create a detailed summary of race data"""
    try:
        print(f"\n📊 Creating detailed race summary...")
        
        summary = {
            "generated_at": datetime.now().isoformat(),
            "total_dates": len(verified_data),
            "race_dates": {}
        }
        
        total_races = 0
        verified_count = 0
        mismatch_count = 0
        
        for date in sorted(verified_data.keys()):
            date_summary = {
                "venues": {},
                "total_races": 0
            }
            
            for venue in verified_data[date]:
                venue_data = verified_data[date][venue]
                race_count = venue_data['race_count']
                status = venue_data['status']
                
                venue_name = "Sha Tin" if venue == "ST" else "Happy Valley"
                
                date_summary["venues"][venue] = {
                    "venue_name": venue_name,
                    "race_count": race_count,
                    "verification_status": status,
                    "race_numbers": venue_data['race_numbers']
                }
                
                if 'db_count' in venue_data:
                    date_summary["venues"][venue]["db_count"] = venue_data['db_count']
                    date_summary["venues"][venue]["hkjc_count"] = venue_data['hkjc_count']
                
                date_summary["total_races"] += race_count
                total_races += race_count
                
                if status == 'verified':
                    verified_count += 1
                elif status == 'mismatch':
                    mismatch_count += 1
            
            summary["race_dates"][date] = date_summary
        
        summary["statistics"] = {
            "total_races": total_races,
            "verified_sessions": verified_count,
            "mismatch_sessions": mismatch_count,
            "total_sessions": sum(len(verified_data[date]) for date in verified_data)
        }
        
        # Save summary
        with open('race_data_summary.json', 'w') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Created race_data_summary.json")
        
        # Print key statistics
        print(f"\n📈 Summary Statistics:")
        print(f"   📅 Total race dates: {summary['total_dates']}")
        print(f"   🏇 Total races: {summary['statistics']['total_races']}")
        print(f"   ✅ Verified sessions: {summary['statistics']['verified_sessions']}")
        print(f"   ⚠️ Mismatch sessions: {summary['statistics']['mismatch_sessions']}")
        
        return summary
        
    except Exception as e:
        print(f"❌ Error creating summary: {str(e)}")
        return None

def main():
    """Main function to update race_dates.json with actual data"""
    print("🏇 HKJC Race Dates JSON Updater (Actual Data)")
    print("=" * 70)
    print("This will update race_dates.json to match actual extracted data")
    print("=" * 70)
    
    # Step 1: Get actual race data from database
    race_data = get_actual_race_data_from_database()
    
    if not race_data:
        print("❌ No race data found in database")
        return
    
    # Step 2: Verify race counts with HKJC
    verified_data = verify_race_counts_with_hkjc(race_data)
    
    # Step 3: Update race_dates.json
    update_success = update_race_dates_json(verified_data)
    
    # Step 4: Create detailed summary
    summary = create_detailed_race_summary(verified_data)
    
    # Final summary
    print(f"\n" + "=" * 70)
    print("🎯 UPDATE SUMMARY:")
    
    if update_success:
        print(f"✅ race_dates.json updated with actual extracted dates")
    else:
        print(f"❌ Failed to update race_dates.json")
    
    if summary:
        print(f"✅ Detailed summary created in race_data_summary.json")
        
        # Check for any issues
        mismatch_sessions = summary['statistics']['mismatch_sessions']
        if mismatch_sessions > 0:
            print(f"⚠️ Found {mismatch_sessions} sessions with count mismatches")
            print(f"   Check race_data_summary.json for details")
        else:
            print(f"🎉 All race counts verified correctly!")
    
    print("=" * 70)

if __name__ == '__main__':
    main()
