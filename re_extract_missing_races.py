import asyncio
import json
import os
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
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "odds_data")

def get_missing_races():
    """Identify missing races from the database"""
    try:
        print("🔍 Analyzing database to find missing races...")
        
        # Initialize PocketBase client
        client = PocketBase(POCKETBASE_URL)
        
        # Authenticate
        client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
        
        # Get all existing records
        all_records = client.collection(COLLECTION_NAME).get_full_list()
        
        # Group by date and venue
        existing_races = {}
        for record in all_records:
            date_venue_key = f"{record.race_date}_{record.venue}"
            if date_venue_key not in existing_races:
                existing_races[date_venue_key] = []
            existing_races[date_venue_key].append(record.race_number)
        
        # Define expected race sessions (based on the cleanup results)
        expected_sessions = {
            "2025-06-26_HV": 12,  # Currently has 11, missing 1
            "2025-06-26_ST": 12,  # Currently has 10, missing 2
            "2025-06-27_HV": 12,  # Complete
            "2025-06-27_ST": 12,  # Complete
            "2025-06-28_HV": 12,  # Complete
            "2025-06-28_ST": 12,  # Complete
            "2025-06-29_HV": 12,  # Currently has 11, missing 1
            "2025-06-29_ST": 12,  # Complete
            "2025-06-30_HV": 12,  # Currently has 11, missing 1
            "2025-06-30_ST": 12,  # Complete
            "2025-07-01_HV": 12,  # Currently has 11, missing 1
            "2025-07-01_ST": 12,  # Complete
        }
        
        missing_races = []
        
        for session, expected_count in expected_sessions.items():
            date, venue = session.split('_')
            existing_race_numbers = existing_races.get(session, [])
            
            # Find missing race numbers
            expected_race_numbers = list(range(1, expected_count + 1))
            missing_race_numbers = [r for r in expected_race_numbers if r not in existing_race_numbers]
            
            if missing_race_numbers:
                for race_number in missing_race_numbers:
                    missing_races.append((date, venue, race_number))
                print(f"⚠️ {date} {venue}: Missing races {missing_race_numbers}")
            else:
                print(f"✅ {date} {venue}: Complete ({len(existing_race_numbers)}/{expected_count})")
        
        print(f"\n📊 Total missing races: {len(missing_races)}")
        return missing_races
        
    except Exception as e:
        print(f"❌ Error analyzing missing races: {str(e)}")
        return []

async def extract_race_odds(race_date, venue, race_number):
    """Extract odds for a specific race (same as before but standalone)"""
    try:
        url = f"https://bet.hkjc.com/ch/racing/pwin/{race_date}/{venue}/{race_number}"
        print(f"🏇 Re-extracting Race {race_number} - {race_date} {venue}")
        
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
                await page.wait_for_timeout(8000)  # Longer wait for stability
                
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
        client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
        
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
        
        # Create new record (should not exist since it was missing)
        result = client.collection(COLLECTION_NAME).create(record_data)
        print(f"✅ Created PocketBase record for Race {race_number}: {result.id}")
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

async def main():
    """Main function to re-extract missing races"""
    print("🏇 HKJC Missing Races Re-extractor")
    print("=" * 50)
    
    # Step 1: Identify missing races
    missing_races = get_missing_races()
    
    if not missing_races:
        print("🎉 No missing races found! All data is complete.")
        return
    
    print(f"\n🔄 Re-extracting {len(missing_races)} missing races...")
    print("-" * 50)
    
    # Step 2: Re-extract missing races
    successful_extractions = 0
    failed_extractions = 0
    
    for race_date, venue, race_number in missing_races:
        try:
            # Extract odds data
            data = await extract_race_odds(race_date, venue, race_number)
            
            if data:
                # Save backup JSON
                backup_file = save_backup_json(data, race_date, venue, race_number)
                
                # Save to PocketBase
                if save_to_pocketbase(data, race_date, venue, race_number):
                    successful_extractions += 1
                    print(f"   ✅ Race {race_number}: {len(data['horses_data'])} horses")
                else:
                    failed_extractions += 1
                    print(f"   ⚠️ Race {race_number}: Extracted but failed to save to PocketBase")
            else:
                failed_extractions += 1
                print(f"   ❌ Race {race_number}: No data extracted")
            
            # Small delay between requests
            await asyncio.sleep(3)
            
        except Exception as e:
            failed_extractions += 1
            print(f"   ❌ Race {race_number}: Error - {str(e)}")
            continue
    
    print("\n" + "=" * 50)
    print("📊 RE-EXTRACTION SUMMARY:")
    print(f"✅ Successfully extracted: {successful_extractions}")
    print(f"❌ Failed extractions: {failed_extractions}")
    print(f"📁 Backup files saved to: {OUTPUT_DIR}/")
    
    if successful_extractions > 0:
        print(f"🎉 Successfully recovered {successful_extractions} missing races!")
    
    print("=" * 50)

if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    asyncio.run(main())
