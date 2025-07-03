import asyncio
import json
import os
import requests
from playwright.async_api import async_playwright
from datetime import datetime
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

# Output directory for backup JSON files
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "odds_data")

def generate_may_dates():
    """Generate all May 2025 dates to check"""
    may_dates = []
    for day in range(1, 32):  # May has 31 days
        date_str = f"2025-05-{day:02d}"
        may_dates.append(date_str)
    return may_dates

def check_odds_availability_detailed(race_date, venue, race_number):
    """Check if odds data is available for a specific race with detailed analysis"""
    try:
        url = f"https://bet.hkjc.com/ch/racing/pwin/{race_date}/{venue}/{race_number}"
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }, timeout=15)
        
        if response.status_code == 200:
            if "You need to enable JavaScript" in response.text:
                # Parse the page to check for race-specific content
                soup = BeautifulSoup(response.text, 'html.parser')
                page_text = soup.get_text()
                
                # Check multiple date formats
                date_formats = [
                    race_date.replace('-', '/'),  # 2025/05/01
                    race_date,  # 2025-05-01
                    f"{race_date[:4]}年{int(race_date[5:7])}月{int(race_date[8:10])}日"  # 2025年5月1日
                ]
                
                for date_format in date_formats:
                    if date_format in page_text:
                        return True, "Date found in page"
                
                # Check for venue-specific content
                venue_indicators = {
                    'ST': ['沙田', 'Sha Tin'],
                    'HV': ['跑馬地', 'Happy Valley']
                }
                
                venue_found = False
                for indicator in venue_indicators.get(venue, []):
                    if indicator in page_text:
                        venue_found = True
                        break
                
                if venue_found:
                    return True, "Venue found in page"
                
                return False, "No race-specific content found"
            else:
                return False, "No JavaScript requirement (likely error page)"
        else:
            return False, f"HTTP {response.status_code}"
    
    except Exception as e:
        return False, f"Request error: {str(e)}"

def get_existing_may_races():
    """Get existing May races from database"""
    try:
        client = PocketBase(POCKETBASE_URL)
        client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
        
        # Get all May 2025 records
        may_records = client.collection(COLLECTION_NAME).get_full_list(
            query_params={
                "filter": 'race_date >= "2025-05-01" && race_date <= "2025-05-31"'
            }
        )
        
        existing_races = {}
        for record in may_records:
            key = f"{record.race_date}_{record.venue}_{record.race_number}"
            existing_races[key] = record.id
        
        return existing_races
    except Exception as e:
        print(f"❌ Error getting existing May races: {str(e)}")
        return {}

def check_may_odds_availability():
    """Check May 2025 odds availability comprehensively"""
    print("🏇 HKJC May 2025 Odds Availability Checker")
    print("=" * 70)
    
    # Get May dates
    may_dates = generate_may_dates()
    print(f"🔍 Checking {len(may_dates)} May 2025 dates...")
    
    # Get existing May races
    existing_may_races = get_existing_may_races()
    print(f"📊 Found {len(existing_may_races)} existing May races in database")
    
    if existing_may_races:
        print("📅 Existing May races:")
        for race_key in sorted(existing_may_races.keys()):
            date, venue, race_num = race_key.split('_')
            print(f"   - {date} {venue} Race {race_num}")
    
    # Check availability
    available_races = []
    missing_races = []
    unavailable_dates = []
    
    print(f"\n🔍 Checking odds availability for May 2025...")
    
    for date in may_dates:
        print(f"\n📅 Checking {date}...")
        
        date_has_races = False
        
        for venue in ['ST', 'HV']:
            print(f"   🏟️ Checking {venue}...")
            
            # Check up to 12 races for this venue/date
            venue_races_found = 0
            
            for race_number in range(1, 13):
                available, _ = check_odds_availability_detailed(date, venue, race_number)
                
                if available:
                    venue_races_found = race_number
                    date_has_races = True
                    
                    # Check if we already have this race
                    race_key = f"{date}_{venue}_{race_number}"
                    if race_key not in existing_may_races:
                        missing_races.append((date, venue, race_number))
                else:
                    # If we can't find this race, stop checking higher numbers
                    break
            
            if venue_races_found > 0:
                available_races.append({
                    'date': date,
                    'venue': venue,
                    'total_races': venue_races_found
                })
                print(f"      ✅ {venue_races_found} races available")
            else:
                print(f"      ❌ No races available")
        
        if not date_has_races:
            unavailable_dates.append(date)
    
    # Summary
    print(f"\n" + "=" * 70)
    print("📋 MAY 2025 AVAILABILITY SUMMARY:")
    print(f"✅ Available race sessions: {len(available_races)}")
    print(f"❌ Missing races to extract: {len(missing_races)}")
    print(f"⚠️ Dates with no races: {len(unavailable_dates)}")
    
    if available_races:
        print(f"\n📅 Available May race sessions:")
        for session in available_races:
            print(f"   - {session['date']} {session['venue']}: {session['total_races']} races")
    
    if missing_races:
        print(f"\n⚠️ Missing May races to extract:")
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
        print(f"\n❌ May dates with no available races:")
        # Show first 10 and count
        for date in unavailable_dates[:10]:
            print(f"   - {date}")
        if len(unavailable_dates) > 10:
            print(f"   ... and {len(unavailable_dates) - 10} more dates")
    
    print("=" * 70)
    
    return missing_races, available_races

async def extract_may_race_sample(race_date, venue, race_number):
    """Extract a sample May race to verify data quality"""
    try:
        url = f"https://bet.hkjc.com/ch/racing/pwin/{race_date}/{venue}/{race_number}"
        print(f"🏇 Testing extraction: {race_date} {venue} Race {race_number}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
            )
            
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='zh-HK'
            )
            
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(8000)
                
                # Check page content
                page_text = await page.text_content('body')
                print(f"   📄 Page content length: {len(page_text)}")
                
                # Look for odds tables
                tables = await page.query_selector_all('table')
                print(f"   📊 Found {len(tables)} tables")
                
                for i, table in enumerate(tables):
                    table_text = await table.text_content()
                    if '獨贏賠率走勢' in table_text or ('馬號' in table_text and '賠率' in table_text):
                        print(f"   ✅ Found odds table {i+1}")
                        
                        rows = await table.query_selector_all('tr')
                        print(f"   📋 Table has {len(rows)} rows")
                        
                        # Extract first few rows as sample
                        sample_data = []
                        for j, row in enumerate(rows[:5]):  # First 5 rows
                            cells = await row.query_selector_all('td, th')
                            row_data = []
                            for cell in cells:
                                text = await cell.text_content()
                                row_data.append(text.strip() if text else "")
                            sample_data.append(row_data)
                        
                        print(f"   📋 Sample data:")
                        for k, row in enumerate(sample_data):
                            print(f"      Row {k+1}: {row[:5]}...")  # First 5 cells
                        
                        return True
                
                print(f"   ❌ No odds tables found")
                return False
                
            finally:
                await browser.close()
        
    except Exception as e:
        print(f"   ❌ Error testing extraction: {str(e)}")
        return False

async def main():
    """Main function to check May odds availability"""
    missing_races, available_races = check_may_odds_availability()
    
    if available_races:
        print(f"\n🧪 Testing extraction on first available race...")
        first_session = available_races[0]
        test_success = await extract_may_race_sample(
            first_session['date'], 
            first_session['venue'], 
            1
        )
        
        if test_success:
            print(f"✅ Extraction test successful!")
        else:
            print(f"❌ Extraction test failed")
    
    if missing_races:
        # Save missing races to file
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
        
        with open('missing_may_races.json', 'w') as f:
            json.dump(missing_data, f, indent=2)
        
        print(f"\n💾 Created missing_may_races.json with {len(missing_races)} races")
        print(f"🔄 Next step: Run extraction script to get May races")
    else:
        print(f"\n🎉 All available May 2025 odds data is already extracted!")

if __name__ == '__main__':
    asyncio.run(main())
