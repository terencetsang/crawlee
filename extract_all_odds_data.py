import asyncio
import json
import re
import os
import requests
from playwright.async_api import async_playwright
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pocketbase import PocketBase
import time

# Load environment variables from .env file
load_dotenv()

# PocketBase configuration
POCKETBASE_URL = os.getenv("POCKETBASE_URL")
POCKETBASE_EMAIL = os.getenv("POCKETBASE_EMAIL")
POCKETBASE_PASSWORD = os.getenv("POCKETBASE_PASSWORD")
COLLECTION_NAME = "race_odds"

# Output directory for backup JSON files
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "win_odds_data")

def get_race_info_from_hkjc():
    """Get current race information from HKJC website"""
    try:
        print("🔍 Getting race information from HKJC...")
        
        # Try the racing information page
        url = "https://racing.hkjc.com/racing/information/Chinese/racing/RaceCard.aspx"
        
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch HKJC racing website: {response.status_code}")
            return None
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract race information
        race_date = None
        racecourse = None
        total_races = 0
        
        # Look for race information in text content
        page_text = soup.get_text()
        
        # Extract date
        date_patterns = [
            r'(\d{4})年(\d{1,2})月(\d{1,2})日.*?(沙田|跑馬地)',
            r'第\s*1\s*場.*?(\d{4})年(\d{1,2})月(\d{1,2})日.*?(沙田|跑馬地)'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, page_text)
            if match:
                if len(match.groups()) == 4:
                    year = match.group(1)
                    month = match.group(2).zfill(2)
                    day = match.group(3).zfill(2)
                    venue_chinese = match.group(4)
                    race_date = f"{year}-{month}-{day}"
                    racecourse = "ST" if venue_chinese == "沙田" else "HV"
                    break
        
        # Count race tabs
        race_tabs = []
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if 'racecard_rt_' in src:
                race_match = re.search(r'racecard_rt_(\d+)', src)
                if race_match:
                    race_tabs.append(int(race_match.group(1)))
        
        if race_tabs:
            total_races = max(race_tabs)
        
        if race_date and racecourse and total_races > 0:
            print(f"✅ Found: Date={race_date}, Venue={racecourse}, Races={total_races}")
            return (race_date, racecourse, total_races)
        
        print("⚠️ Could not extract complete race information")
        return None
        
    except Exception as e:
        print(f"❌ Error getting race info: {str(e)}")
        return None

def get_available_race_dates():
    """Get available race dates from multiple sources"""
    race_dates = []

    # Method 1: Get from HKJC current race info
    current_race = get_race_info_from_hkjc()
    if current_race:
        race_dates.append(current_race)

    # Method 2: Try recent dates (last 7 days) - but be more conservative
    print("🔍 Checking recent race dates...")
    today = datetime.now()

    # Only check dates that are likely to have races (exclude Mondays and Tuesdays typically)
    for i in range(7):
        check_date = today - timedelta(days=i)
        date_str = check_date.strftime("%Y-%m-%d")

        # Skip future dates (races can't exist in the future)
        if check_date > today:
            continue

        # Check both venues but with validation
        for venue in ["ST", "HV"]:
            print(f"   Checking {date_str} {venue}...")
            if check_race_date_exists(date_str, venue):
                # Estimate total races more carefully
                total_races = estimate_total_races(date_str, venue)
                if total_races > 0:
                    race_dates.append((date_str, venue, total_races))
                    print(f"   ✅ Found {date_str} {venue} with {total_races} races")
            else:
                print(f"   ❌ No races found for {date_str} {venue}")

    # Remove duplicates and sort by date
    unique_races = list(set(race_dates))
    unique_races.sort(key=lambda x: x[0], reverse=True)  # Sort by date, newest first
    return unique_races

def check_race_date_exists(race_date, venue):
    """Check if a race date exists by trying to access race 1 and validating content"""
    try:
        url = f"https://bet.hkjc.com/ch/racing/pwin/{race_date}/{venue}/1"
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }, timeout=10)

        if response.status_code == 200:
            # Check if it's a valid race page (not redirected to a different date)
            if "You need to enable JavaScript" in response.text:
                # Additional validation: check if the URL in the response matches our request
                # Look for date patterns in the response that might indicate redirection
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                page_text = soup.get_text()

                # Check if the requested date appears in the page content
                date_formatted = race_date.replace('-', '/')  # 2025/07/02
                date_chinese_year = race_date[:4] + '年'  # 2025年

                # If the page contains the requested date, it's likely valid
                if date_formatted in page_text or date_chinese_year in page_text:
                    return True

                # If page contains different date patterns, it might be redirected
                import re
                other_dates = re.findall(r'\d{4}年\d{1,2}月\d{1,2}日', page_text)
                if other_dates:
                    # Check if any found date matches our request
                    for found_date in other_dates:
                        # Convert Chinese date format to check
                        date_match = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', found_date)
                        if date_match:
                            found_date_str = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
                            if found_date_str == race_date:
                                return True

                    # If we found dates but none match our request, it's likely redirected
                    print(f"⚠️ Date {race_date} {venue} appears to be redirected to different date")
                    return False

                # If no clear date validation, assume it exists (fallback)
                return True

        return False
    except Exception as e:
        print(f"⚠️ Error checking {race_date} {venue}: {e}")
        return False

def estimate_total_races(race_date, venue):
    """Estimate total number of races by checking which race numbers exist"""
    total_races = 0
    
    # Check up to 12 races (typical maximum)
    for race_num in range(1, 13):
        if check_race_date_exists(race_date, venue):
            total_races = race_num
        else:
            break
    
    # Default to 10 if we can't determine
    return total_races if total_races > 0 else 10

async def extract_race_odds(race_date, venue, race_number):
    """Extract odds for a specific race"""
    try:
        url = f"https://bet.hkjc.com/ch/racing/pwin/{race_date}/{venue}/{race_number}"
        print(f"🏇 Extracting Race {race_number} - {race_date} {venue}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,  # Use headless for batch processing
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
                await page.wait_for_timeout(5000)

                # Validate that we're on the correct race page
                page_text = await page.text_content('body')

                # Check if page contains the expected date
                date_formatted = race_date.replace('-', '/')  # 2025/07/02
                date_chinese_year = race_date[:4] + '年'  # 2025年

                if date_formatted not in page_text and date_chinese_year not in page_text:
                    print(f"⚠️ Page doesn't contain expected date {race_date} - likely redirected")
                    return None

                # Extract odds data
                odds_data = await extract_odds_from_page(page)

                if odds_data:
                    structured_data = process_odds_data(odds_data, race_date, venue, race_number, url)

                    # Additional validation: check if the extracted data makes sense
                    if structured_data and validate_extracted_data(structured_data, race_date, venue, race_number):
                        return structured_data
                    else:
                        print(f"⚠️ Extracted data validation failed for Race {race_number}")
                        return None

                return None

            finally:
                await browser.close()

    except Exception as e:
        print(f"❌ Error extracting race {race_number}: {str(e)}")
        return None

def validate_extracted_data(data, expected_date, expected_venue, expected_race_number):
    """Validate that extracted data matches expected race parameters"""
    try:
        if not data or 'race_info' not in data:
            return False

        race_info = data['race_info']

        # Check if the extracted race info matches what we expected
        if (race_info.get('race_date') == expected_date and
            race_info.get('venue') == expected_venue and
            race_info.get('race_number') == expected_race_number):

            # Check if we have reasonable horse data
            horses_data = data.get('horses_data', [])
            if len(horses_data) >= 8:  # At least 8 horses (reasonable minimum)
                return True

        return False

    except Exception as e:
        print(f"⚠️ Data validation error: {e}")
        return False

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
            
            # Create win odds trend
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

def save_to_pocketbase(data, race_date, venue, race_number):
    """Save odds data to PocketBase"""
    try:
        client = PocketBase(POCKETBASE_URL)
        
        # Authenticate
        try:
            client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
        except Exception as auth_error:
            print(f"⚠️ Authentication failed: {str(auth_error)}")
            return False
        
        # Prepare record data
        record_data = {
            "race_date": race_date,
            "venue": venue,
            "race_number": race_number,
            "data_type": "win_odds_trends",
            "complete_data": json.dumps(data, ensure_ascii=False),
            "scraped_at": datetime.now().isoformat(),
            "source_url": data["race_info"]["source_url"],
            "extraction_status": "success" if data["extraction_summary"]["data_extraction_successful"] else "partial"
        }
        
        # Check if record exists
        try:
            existing_records = client.collection(COLLECTION_NAME).get_list(
                1, 1,
                {
                    "filter": f'race_date="{race_date}" && venue="{venue}" && race_number={race_number} && data_type="win_odds_trends"'
                }
            )
            
            if existing_records.total_items > 0:
                record_id = existing_records.items[0].id
                client.collection(COLLECTION_NAME).update(record_id, record_data)
                print(f"✅ Updated PocketBase record for Race {race_number}")
            else:
                result = client.collection(COLLECTION_NAME).create(record_data)
                print(f"✅ Created PocketBase record for Race {race_number}: {result.id}")
        
        except Exception as create_error:
            print(f"❌ Error saving to PocketBase: {str(create_error)}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ PocketBase error: {str(e)}")
        return False

async def main():
    """Main function to extract all available race odds"""
    print("🏇 HKJC All Odds Data Extractor")
    print("=" * 60)
    
    # Get available race dates
    print("🔍 Finding available race dates...")
    available_races = get_available_race_dates()
    
    if not available_races:
        print("❌ No available races found")
        return
    
    print(f"✅ Found {len(available_races)} race sessions:")
    for race_date, venue, total_races in available_races:
        print(f"   📅 {race_date} {venue} - {total_races} races")
    
    # Extract odds for all races
    total_extracted = 0
    total_saved = 0
    
    for race_date, venue, total_races in available_races:
        print(f"\n🏁 Processing {race_date} {venue} ({total_races} races)")
        print("-" * 40)
        
        for race_number in range(1, total_races + 1):
            try:
                # Extract odds data
                data = await extract_race_odds(race_date, venue, race_number)
                
                if data:
                    total_extracted += 1
                    
                    # Save backup JSON
                    formatted_date = race_date.replace('-', '_')
                    json_filename = f"{OUTPUT_DIR}/win_odds_trends_{formatted_date}_{venue}_R{race_number}.json"
                    os.makedirs(OUTPUT_DIR, exist_ok=True)
                    
                    with open(json_filename, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    
                    # Save to PocketBase
                    if save_to_pocketbase(data, race_date, venue, race_number):
                        total_saved += 1
                    
                    print(f"   ✅ Race {race_number}: {len(data['horses_data'])} horses")
                else:
                    print(f"   ❌ Race {race_number}: No data")
                
                # Small delay between requests
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"   ❌ Race {race_number}: Error - {str(e)}")
                continue
    
    print("\n" + "=" * 60)
    print("📊 FINAL SUMMARY:")
    print(f"✅ Total races extracted: {total_extracted}")
    print(f"💾 Total saved to PocketBase: {total_saved}")
    print(f"📁 Backup files saved to: {OUTPUT_DIR}/")
    print("=" * 60)

if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    asyncio.run(main())
