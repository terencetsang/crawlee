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
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "win_odds_data")

# The 2 specific missing races
MISSING_RACES = [
    ("2025-06-30", "HV", 11),  # 2025-06-30 HV Race 11
    ("2025-07-01", "HV", 1)    # 2025-07-01 HV Race 1
]

async def extract_race_odds_with_retry(race_date, venue, race_number, max_retries=3):
    """Extract odds for a specific race with retry logic"""
    
    for attempt in range(max_retries):
        try:
            url = f"https://bet.hkjc.com/ch/racing/pwin/{race_date}/{venue}/{race_number}"
            print(f"🏇 Attempt {attempt + 1}/{max_retries}: Extracting {race_date} {venue} Race {race_number}")
            print(f"   URL: {url}")
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=False,  # Use visible browser for better success
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
                    # Navigate with longer timeout
                    await page.goto(url, wait_until='domcontentloaded', timeout=45000)
                    
                    # Wait longer for page to fully load
                    print(f"   ⏳ Waiting for page to load...")
                    await page.wait_for_timeout(10000)
                    
                    # Check page content
                    page_text = await page.text_content('body')
                    print(f"   📄 Page loaded, content length: {len(page_text)}")
                    
                    # Look for race-specific content
                    if f"{race_date.replace('-', '/')}" in page_text or f"{race_date[:4]}年" in page_text:
                        print(f"   ✅ Found expected date in page content")
                    else:
                        print(f"   ⚠️ Expected date not found in page content")
                    
                    # Try to extract odds data
                    print(f"   🔍 Extracting odds data...")
                    odds_data = await extract_odds_from_page(page)
                    
                    if odds_data:
                        print(f"   ✅ Found odds table with {len(odds_data)} rows")
                        structured_data = process_odds_data(odds_data, race_date, venue, race_number, url)
                        
                        if structured_data:
                            horses_count = len(structured_data.get('horses_data', []))
                            print(f"   🎉 Successfully extracted data for {horses_count} horses")
                            return structured_data
                        else:
                            print(f"   ❌ Failed to process odds data")
                    else:
                        print(f"   ❌ No odds data found on page")
                    
                    # If we reach here, extraction failed for this attempt
                    if attempt < max_retries - 1:
                        print(f"   🔄 Retrying in 5 seconds...")
                        await asyncio.sleep(5)
                    
                finally:
                    await browser.close()
            
        except Exception as e:
            print(f"   ❌ Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                print(f"   🔄 Retrying in 5 seconds...")
                await asyncio.sleep(5)
    
    print(f"   💀 All {max_retries} attempts failed for {race_date} {venue} Race {race_number}")
    return None

async def extract_odds_from_page(page):
    """Extract odds data from the current page"""
    try:
        # Look for tables with odds data
        tables = await page.query_selector_all('table')
        print(f"   📊 Found {len(tables)} tables on page")
        
        for i, table in enumerate(tables):
            table_text = await table.text_content()
            
            # Check if this table contains odds data
            if '獨贏賠率走勢' in table_text or ('馬號' in table_text and '賠率' in table_text):
                print(f"   ✅ Found odds table {i+1}")
                
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
                    print(f"   📋 Extracted {len(table_data)} rows from odds table")
                    return table_data
        
        print(f"   ⚠️ No odds tables found")
        return None
        
    except Exception as e:
        print(f"   ❌ Error extracting from page: {str(e)}")
        return None

def process_odds_data(raw_data, race_date, venue, race_number, source_url):
    """Process raw odds data into structured format"""
    try:
        if not raw_data or len(raw_data) < 3:
            print(f"   ⚠️ Insufficient raw data: {len(raw_data) if raw_data else 0} rows")
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
            print(f"   ⚠️ No header row found")
            return None
        
        print(f"   📋 Found header row, processing {len(data_rows)} data rows")
        
        # Extract timestamps
        timestamps = []
        if timestamp_row:
            timestamps = [cell for cell in timestamp_row if ':' in cell]
        
        if not timestamps:
            timestamps = ["07:30", "15:59", "16:02"]
        
        print(f"   ⏰ Using timestamps: {timestamps}")
        
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
        
        print(f"   🐎 Processed {len(horses_data)} horses")
        
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
        print(f"   ❌ Error processing odds data: {str(e)}")
        return None

def save_to_pocketbase(data, race_date, venue, race_number):
    """Save odds data to PocketBase"""
    try:
        print(f"   💾 Saving to PocketBase...")
        
        client = PocketBase(POCKETBASE_URL)
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
        
        # Create new record
        result = client.collection(COLLECTION_NAME).create(record_data)
        print(f"   ✅ Created PocketBase record: {result.id}")
        return True
        
    except Exception as e:
        print(f"   ❌ PocketBase error: {str(e)}")
        return False

def save_backup_json(data, race_date, venue, race_number):
    """Save backup JSON file"""
    try:
        formatted_date = race_date.replace('-', '_')
        json_filename = f"{OUTPUT_DIR}/win_odds_trends_{formatted_date}_{venue}_R{race_number}.json"
        
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"   💾 Backup saved to: {json_filename}")
        return json_filename
    except Exception as e:
        print(f"   ❌ Error saving backup: {str(e)}")
        return None

async def main():
    """Main function to extract the 2 missing races"""
    print("🏇 HKJC Missing 2 Races Extractor")
    print("=" * 60)
    print("Target races:")
    for race_date, venue, race_number in MISSING_RACES:
        print(f"   - {race_date} {venue} Race {race_number}")
    print("=" * 60)
    
    successful_extractions = 0
    failed_extractions = 0
    
    for race_date, venue, race_number in MISSING_RACES:
        print(f"\n🎯 Processing {race_date} {venue} Race {race_number}")
        print("-" * 40)
        
        try:
            # Extract odds data with retry
            data = await extract_race_odds_with_retry(race_date, venue, race_number)
            
            if data:
                # Save backup JSON
                backup_file = save_backup_json(data, race_date, venue, race_number)
                
                # Save to PocketBase
                if save_to_pocketbase(data, race_date, venue, race_number):
                    successful_extractions += 1
                    horses_count = len(data['horses_data'])
                    print(f"🎉 SUCCESS: Extracted {horses_count} horses")
                else:
                    failed_extractions += 1
                    print(f"⚠️ PARTIAL: Extracted but failed to save to PocketBase")
            else:
                failed_extractions += 1
                print(f"❌ FAILED: No data extracted")
            
            # Delay between races
            if race_date != MISSING_RACES[-1][0] or venue != MISSING_RACES[-1][1] or race_number != MISSING_RACES[-1][2]:
                print(f"⏳ Waiting 10 seconds before next race...")
                await asyncio.sleep(10)
            
        except Exception as e:
            failed_extractions += 1
            print(f"❌ ERROR: {str(e)}")
    
    print(f"\n" + "=" * 60)
    print("📊 EXTRACTION SUMMARY:")
    print(f"✅ Successfully extracted: {successful_extractions}/2")
    print(f"❌ Failed extractions: {failed_extractions}/2")
    
    if successful_extractions > 0:
        print(f"🎉 Successfully recovered {successful_extractions} missing races!")
        print(f"📊 Database now has {142 + successful_extractions} total races")
    else:
        print(f"😞 No races could be extracted - data may no longer be available")
    
    print("=" * 60)

if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    asyncio.run(main())
