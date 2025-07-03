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

def load_race_dates():
    """Load race dates from race_dates.json file"""
    try:
        with open('race_dates.json', 'r') as f:
            race_dates = json.load(f)
        print(f"📅 Loaded {len(race_dates)} race dates from race_dates.json:")
        for date in race_dates:
            print(f"   - {date}")
        return race_dates
    except Exception as e:
        print(f"❌ Error loading race_dates.json: {str(e)}")
        return []

def get_race_info_for_date(race_date):
    """Get race information for a specific date from HKJC website"""
    try:
        print(f"🔍 Checking race info for {race_date}...")
        
        # Convert date format for URL (YYYY-MM-DD to YYYY/MM/DD)
        url_date = race_date.replace('-', '/')
        
        # Try the racing information page
        url = f"https://racing.hkjc.com/racing/information/Chinese/Racing/Racecard.aspx?RaceDate={url_date}"
        
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }, timeout=15)
        
        if response.status_code != 200:
            print(f"   ❌ Failed to fetch race info: HTTP {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()
        
        # Extract venue information
        venue = None
        total_races = 0
        
        # Look for venue indicators
        if '沙田' in page_text:
            venue = 'ST'
        elif '跑馬地' in page_text:
            venue = 'HV'
        
        # Count race tabs or look for race information
        race_indicators = []
        
        # Method 1: Look for race tab images
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if 'racecard_rt_' in src:
                race_match = re.search(r'racecard_rt_(\d+)', src)
                if race_match:
                    race_indicators.append(int(race_match.group(1)))
        
        # Method 2: Look for race links or buttons
        if not race_indicators:
            import re
            race_patterns = [
                r'第\s*(\d+)\s*場',
                r'Race\s*(\d+)',
                r'R(\d+)'
            ]
            
            for pattern in race_patterns:
                matches = re.findall(pattern, page_text)
                if matches:
                    race_indicators.extend([int(m) for m in matches])
                    break
        
        if race_indicators:
            total_races = max(race_indicators)
        
        # If we found venue and races, return the info
        if venue and total_races > 0:
            print(f"   ✅ Found: {venue} venue with {total_races} races")
            return {
                'race_date': race_date,
                'venue': venue,
                'total_races': total_races
            }
        
        # If no clear info found, try both venues with default race count
        print(f"   ⚠️ Could not determine venue/races from page, will try both venues")
        return None
        
    except Exception as e:
        print(f"   ❌ Error getting race info for {race_date}: {str(e)}")
        return None

def verify_race_exists(race_date, venue, race_number):
    """Verify if a specific race exists by checking the betting page"""
    try:
        url = f"https://bet.hkjc.com/ch/racing/pwin/{race_date}/{venue}/{race_number}"
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }, timeout=10)
        
        if response.status_code == 200:
            # Check if it's a valid race page
            if "You need to enable JavaScript" in response.text:
                # Additional validation: check if the URL contains the expected date
                soup = BeautifulSoup(response.text, 'html.parser')
                page_text = soup.get_text()
                
                # Check if the requested date appears in the page
                date_formatted = race_date.replace('-', '/')
                if date_formatted in page_text:
                    return True
        
        return False
    except:
        return False

def get_existing_races_from_db():
    """Get existing races from PocketBase database"""
    try:
        client = PocketBase(POCKETBASE_URL)
        client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
        
        all_records = client.collection(COLLECTION_NAME).get_full_list()
        
        existing_races = {}
        for record in all_records:
            key = f"{record.race_date}_{record.venue}_{record.race_number}"
            existing_races[key] = record.id
        
        return existing_races
    except Exception as e:
        print(f"❌ Error getting existing races: {str(e)}")
        return {}

def analyze_race_coverage():
    """Analyze race coverage based on race_dates.json"""
    print("🏇 HKJC Race Coverage Analysis")
    print("=" * 60)
    
    # Load race dates from JSON
    race_dates = load_race_dates()
    if not race_dates:
        return []
    
    # Get existing races from database
    existing_races = get_existing_races_from_db()
    print(f"\n📊 Found {len(existing_races)} existing races in database")
    
    # Analyze each date
    missing_races = []
    valid_race_sessions = []
    
    for race_date in race_dates:
        print(f"\n📅 Analyzing {race_date}...")
        
        # Get race info for this date
        race_info = get_race_info_for_date(race_date)
        
        if race_info:
            # We found specific venue and race count
            venue = race_info['venue']
            total_races = race_info['total_races']
            
            print(f"   📍 Venue: {venue}, Total races: {total_races}")
            
            # Check which races exist and which are missing
            existing_count = 0
            missing_count = 0
            
            for race_number in range(1, total_races + 1):
                race_key = f"{race_date}_{venue}_{race_number}"
                if race_key in existing_races:
                    existing_count += 1
                else:
                    missing_races.append((race_date, venue, race_number))
                    missing_count += 1
            
            print(f"   ✅ Existing: {existing_count}, ❌ Missing: {missing_count}")
            valid_race_sessions.append(race_info)
            
        else:
            # Try both venues with standard race counts
            print(f"   🔍 Trying both venues for {race_date}...")
            
            for venue in ['ST', 'HV']:
                # Check if races exist for this venue
                races_found = 0
                for race_number in range(1, 13):  # Check up to 12 races
                    if verify_race_exists(race_date, venue, race_number):
                        races_found = race_number
                    else:
                        break
                
                if races_found > 0:
                    print(f"   ✅ Found {venue} venue with {races_found} races")
                    
                    # Check existing vs missing
                    existing_count = 0
                    missing_count = 0
                    
                    for race_number in range(1, races_found + 1):
                        race_key = f"{race_date}_{venue}_{race_number}"
                        if race_key in existing_races:
                            existing_count += 1
                        else:
                            missing_races.append((race_date, venue, race_number))
                            missing_count += 1
                    
                    print(f"   ✅ Existing: {existing_count}, ❌ Missing: {missing_count}")
                    valid_race_sessions.append({
                        'race_date': race_date,
                        'venue': venue,
                        'total_races': races_found
                    })
                else:
                    print(f"   ❌ No races found for {venue}")
    
    print(f"\n" + "=" * 60)
    print("📋 ANALYSIS SUMMARY:")
    print(f"✅ Valid race sessions: {len(valid_race_sessions)}")
    print(f"❌ Missing races: {len(missing_races)}")
    
    if valid_race_sessions:
        print(f"\n📅 Valid race sessions found:")
        for session in valid_race_sessions:
            print(f"   - {session['race_date']} {session['venue']}: {session['total_races']} races")
    
    if missing_races:
        print(f"\n⚠️ Missing races to extract:")
        for race_date, venue, race_number in missing_races:
            print(f"   - {race_date} {venue} Race {race_number}")
    
    return missing_races

async def extract_race_odds(race_date, venue, race_number):
    """Extract odds for a specific race"""
    try:
        url = f"https://bet.hkjc.com/ch/racing/pwin/{race_date}/{venue}/{race_number}"
        print(f"🏇 Extracting Race {race_number} - {race_date} {venue}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
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
                
                # Extract odds data
                odds_data = await extract_odds_from_page(page)
                
                if odds_data:
                    structured_data = process_odds_data(odds_data, race_date, venue, race_number, url)
                    return structured_data
                
                return None
                
            finally:
                await browser.close()
        
    except Exception as e:
        print(f"❌ Error extracting race {race_number}: {str(e)}")
        return None

# [Include the same extract_odds_from_page and process_odds_data functions from previous script]
async def extract_odds_from_page(page):
    """Extract odds data from the current page"""
    try:
        tables = await page.query_selector_all('table')
        
        for table in tables:
            table_text = await table.text_content()
            
            if '獨贏賠率走勢' in table_text or ('馬號' in table_text and '賠率' in table_text):
                rows = await table.query_selector_all('tr')
                table_data = []
                
                for row in rows:
                    cells = await row.query_selector_all('td, th')
                    if cells:
                        row_data = []
                        for cell in cells:
                            text = await cell.text_content()
                            row_data.append(text.strip() if text else "")
                        
                        if any(cell for cell in row_data):
                            table_data.append(row_data)
                
                if table_data:
                    return table_data
        
        return None
        
    except Exception as e:
        print(f"❌ Error extracting from page: {str(e)}")
        return None

def process_odds_data(raw_data, race_date, venue, race_number, source_url):
    """Process raw odds data into structured format"""
    try:
        if not raw_data or len(raw_data) < 3:
            return None
        
        # Find header and data rows
        header_row = None
        timestamp_row = None
        data_rows = []
        
        for i, row in enumerate(raw_data):
            if '馬號' in row and '獨贏賠率走勢' in row:
                header_row = row
                if i + 1 < len(raw_data):
                    next_row = raw_data[i + 1]
                    if any(':' in cell for cell in next_row):
                        timestamp_row = next_row
                        data_rows = raw_data[i + 2:]
                    else:
                        data_rows = raw_data[i + 1:]
                break
        
        if not header_row:
            return None
        
        # Extract timestamps
        timestamps = []
        if timestamp_row:
            timestamps = [cell for cell in timestamp_row if ':' in cell]
        
        if not timestamps:
            timestamps = ["07:30", "15:59", "16:02"]
        
        # Process horse data
        horses_data = []
        
        for row in data_rows:
            if len(row) < 8 or not row[0].isdigit():
                continue
            
            horse_number = row[0]
            horse_name = row[2] if len(row) > 2 else ""
            gate = row[3] if len(row) > 3 else ""
            weight = row[4] if len(row) > 4 else ""
            jockey = row[5] if len(row) > 5 else ""
            trainer = row[6] if len(row) > 6 else ""
            
            # Extract odds values
            odds_values = []
            for j in range(7, len(row)):
                cell = row[j].strip()
                if cell and cell.replace('.', '').replace(',', '').isdigit():
                    try:
                        odds_value = float(cell)
                        if 1.0 <= odds_value <= 999.0:
                            odds_values.append(cell)
                    except:
                        continue
            
            # Create win odds trend with merged timestamps
            win_odds_trend = []
            place_odds = ""
            
            if odds_values:
                if len(odds_values) > len(timestamps):
                    place_odds = odds_values[-1]
                    win_odds_values = odds_values[:-1]
                else:
                    win_odds_values = odds_values
                
                for k, odds in enumerate(win_odds_values):
                    if k < len(timestamps):
                        win_odds_trend.append({
                            "time": timestamps[k],
                            "odds": odds
                        })
            
            horses_data.append({
                "horse_number": horse_number,
                "horse_name": horse_name,
                "gate": gate,
                "weight": weight,
                "jockey": jockey,
                "trainer": trainer,
                "win_odds_trend": win_odds_trend,
                "place_odds": place_odds
            })
        
        return {
            "race_info": {
                "race_date": race_date,
                "venue": venue,
                "race_number": race_number,
                "source_url": source_url,
                "scraped_at": datetime.now().isoformat()
            },
            "horses_data": horses_data,
            "extraction_summary": {
                "total_horses": len(horses_data),
                "data_extraction_successful": len(horses_data) > 0,
                "timestamps": timestamps
            }
        }
        
    except Exception as e:
        print(f"❌ Error processing odds data: {str(e)}")
        return None

def main():
    """Main function to analyze race coverage"""
    missing_races = analyze_race_coverage()
    
    if missing_races:
        print(f"\n🔄 Found {len(missing_races)} missing races that need to be extracted.")
        print("Run the extraction part to get these missing races.")
    else:
        print(f"\n🎉 All races from race_dates.json are already extracted!")

if __name__ == '__main__':
    import re
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    main()
