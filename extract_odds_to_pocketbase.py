import asyncio
import json
import re
import os
import requests
from playwright.async_api import async_playwright
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

# Output directory for backup JSON files
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "win_odds_data")

def parse_url(url):
    """Parse HKJC odds URL to extract race details"""
    patterns = [
        r'https://bet\.hkjc\.com/ch/racing/wp/(\d{4}-\d{2}-\d{2})/(\w+)/(\d+)',
        r'https://bet\.hkjc\.com/ch/racing/pwin/(\d{4}-\d{2}-\d{2})/(\w+)/(\d+)'
    ]
    
    for pattern in patterns:
        match = re.match(pattern, url)
        if match:
            race_date = match.group(1)
            venue = match.group(2)
            race_number = int(match.group(3))
            return race_date, venue, race_number
    
    raise ValueError(f"Invalid HKJC odds URL format: {url}")

async def extract_win_odds_trends(url):
    """Extract win odds trends data using Playwright"""
    
    try:
        race_date, venue, race_number = parse_url(url)
        
        print(f"🏇 Extracting Win Odds Trends for Race {race_number} on {race_date} at {venue}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security'
                ]
            )
            
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='zh-HK'
            )
            
            page = await context.new_page()
            
            try:
                print("🌐 Loading betting page...")
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(8000)  # Wait for page to fully load
                
                print("🔍 Extracting odds data...")
                odds_data = await extract_odds_from_page(page)
                
                if odds_data:
                    # Process and structure the data
                    structured_data = process_odds_data(odds_data, race_date, venue, race_number, url)
                    return structured_data
                else:
                    return None
                
            finally:
                await browser.close()
        
    except Exception as e:
        print(f"❌ Error extracting odds: {str(e)}")
        return None

async def extract_odds_from_page(page):
    """Extract odds data from the current page"""
    try:
        print("📊 Looking for odds tables...")
        tables = await page.query_selector_all('table')
        
        for i, table in enumerate(tables):
            table_text = await table.text_content()
            
            # Look for table with win odds trends
            if '獨贏賠率走勢' in table_text or ('馬號' in table_text and '賠率' in table_text):
                print(f"✅ Found odds table {i+1}")
                
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
        
        # Find header row and timestamp row
        header_row = None
        timestamp_row = None
        data_rows = []
        
        for i, row in enumerate(raw_data):
            if '馬號' in row and '獨贏賠率走勢' in row:
                header_row = row
                # Next row might be timestamps
                if i + 1 < len(raw_data):
                    next_row = raw_data[i + 1]
                    # Check if it looks like timestamps (contains time format)
                    if any(':' in cell for cell in next_row):
                        timestamp_row = next_row
                        data_rows = raw_data[i + 2:]
                    else:
                        data_rows = raw_data[i + 1:]
                break
        
        if not header_row:
            print("⚠️ Could not find header row")
            return None
        
        # Extract timestamps from the timestamp row or use default
        timestamps = []
        if timestamp_row:
            timestamps = [cell for cell in timestamp_row if ':' in cell]
        
        if not timestamps:
            timestamps = ["07:30", "15:59", "16:02"]  # Default timestamps
        
        # Process horse data
        horses_data = []
        
        for row in data_rows:
            if len(row) < 8:  # Skip rows that don't have enough data
                continue
            
            # Skip if first cell is not a number (horse number)
            if not row[0].isdigit():
                continue
            
            horse_number = row[0]
            horse_name = row[2] if len(row) > 2 else ""
            gate = row[3] if len(row) > 3 else ""
            weight = row[4] if len(row) > 4 else ""
            jockey = row[5] if len(row) > 5 else ""
            trainer = row[6] if len(row) > 6 else ""
            
            # Extract win odds trend (multiple odds values)
            win_odds_trend = []
            place_odds = ""
            
            # Find odds values (typically after trainer column)
            odds_start_index = 7
            odds_values = []
            
            for j in range(odds_start_index, len(row)):
                cell = row[j].strip()
                if cell and cell.replace('.', '').replace(',', '').isdigit():
                    try:
                        odds_value = float(cell)
                        if 1.0 <= odds_value <= 999.0:  # Valid odds range
                            odds_values.append(cell)
                    except:
                        continue
            
            # Map odds to timestamps
            if odds_values:
                # Last value is usually place odds
                if len(odds_values) > len(timestamps):
                    place_odds = odds_values[-1]
                    win_odds_values = odds_values[:-1]
                else:
                    win_odds_values = odds_values
                
                # Create win odds trend with timestamps
                for k, odds in enumerate(win_odds_values):
                    if k < len(timestamps):
                        win_odds_trend.append({
                            "time": timestamps[k],
                            "odds": odds
                        })
            
            horse_data = {
                "horse_number": horse_number,
                "horse_name": horse_name,
                "gate": gate,
                "weight": weight,
                "jockey": jockey,
                "trainer": trainer,
                "win_odds_trend": win_odds_trend,
                "place_odds": place_odds
            }
            
            horses_data.append(horse_data)
        
        # Create final structured data
        structured_data = {
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
                "timestamps_found": len(timestamps),
                "timestamps": timestamps
            }
        }
        
        return structured_data
        
    except Exception as e:
        print(f"❌ Error processing odds data: {str(e)}")
        return None

def save_to_pocketbase(data, race_date, venue, race_number):
    """Save odds data to PocketBase"""
    try:
        print("💾 Saving to PocketBase...")
        
        # Initialize PocketBase client
        client = PocketBase(POCKETBASE_URL)
        
        # Authenticate
        try:
            user_data = client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
            print("✅ Authenticated with PocketBase")
        except Exception as auth_error:
            print(f"⚠️ Authentication failed: {str(auth_error)}")
            print("Continuing without authentication...")
        
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
        
        # Check if record already exists
        try:
            existing_records = client.collection(COLLECTION_NAME).get_list(
                1, 1,
                {
                    "filter": f'race_date="{race_date}" && venue="{venue}" && race_number={race_number} && data_type="win_odds_trends"'
                }
            )
            
            if existing_records.total_items > 0:
                # Update existing record
                record_id = existing_records.items[0].id
                result = client.collection(COLLECTION_NAME).update(record_id, record_data)
                print(f"✅ Updated existing record in PocketBase: {result.id}")
            else:
                # Create new record
                result = client.collection(COLLECTION_NAME).create(record_data)
                print(f"✅ Created new record in PocketBase: {result.id}")
        
        except Exception as create_error:
            print(f"❌ Error saving to PocketBase: {str(create_error)}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ PocketBase error: {str(e)}")
        return False

def save_backup_json(data, race_date, venue, race_number):
    """Save backup JSON file"""
    try:
        formatted_date = race_date.replace('-', '_')
        json_filename = f"{OUTPUT_DIR}/win_odds_trends_{formatted_date}_{venue}_R{race_number}.json"
        
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Backup saved to: {json_filename}")
        return json_filename
    except Exception as e:
        print(f"❌ Error saving backup: {str(e)}")
        return None

async def main(url=None):
    """Main function to extract odds and save to PocketBase"""
    if url is None:
        url = "https://bet.hkjc.com/ch/racing/pwin/2025-07-01/ST/1"
    
    try:
        race_date, venue, race_number = parse_url(url)
        
        print("🏇 HKJC Odds Extractor to PocketBase")
        print("=" * 50)
        print(f"Race: {race_number} | Date: {race_date} | Venue: {venue}")
        print("=" * 50)
        
        # Extract odds data
        data = await extract_win_odds_trends(url)
        
        if data:
            print(f"✅ Successfully extracted data for {len(data['horses_data'])} horses")
            
            # Save backup JSON
            backup_file = save_backup_json(data, race_date, venue, race_number)
            
            # Save to PocketBase
            pocketbase_success = save_to_pocketbase(data, race_date, venue, race_number)
            
            print("\n" + "=" * 50)
            print("📊 SUMMARY:")
            print(f"✅ Data Extracted: {len(data['horses_data'])} horses")
            print(f"💾 Backup JSON: {'✅' if backup_file else '❌'}")
            print(f"🗄️ PocketBase: {'✅' if pocketbase_success else '❌'}")
            print("=" * 50)
            
        else:
            print("❌ Failed to extract odds data")
            
    except ValueError as e:
        print(f"❌ URL Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == '__main__':
    import sys
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    url = None
    if len(sys.argv) > 1:
        url = sys.argv[1]
    
    asyncio.run(main(url))
