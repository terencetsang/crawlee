#!/usr/bin/env python3
"""
Extract 2025-07-16 Odds Trends Data
==================================
Specifically extract odds trends for 2025/07/16 HV races using the working extraction logic.
"""

import asyncio
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from pocketbase import PocketBase
from playwright.async_api import async_playwright

# Load environment variables
load_dotenv()

# Configuration
POCKETBASE_URL = os.getenv("POCKETBASE_URL", "http://terence.myds.me:8081")
POCKETBASE_EMAIL = os.getenv("POCKETBASE_EMAIL", "terencetsang@hotmail.com")
POCKETBASE_PASSWORD = os.getenv("POCKETBASE_PASSWORD", "Qwertyu12345")
COLLECTION_NAME = "race_odds"
OUTPUT_DIR = "win_odds_data"

async def extract_race_odds_2025_07_16(race_number):
    """Extract odds for specific 2025-07-16 race"""
    
    print(f"🏁 Extracting Race {race_number} for 2025-07-16...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Direct URL for 2025-07-16 HV race
            url = f"https://bet.hkjc.com/ch/racing/pwin/2025-07-16/HV/{race_number}"
            print(f"   🌐 Navigating to: {url}")
            
            response = await page.goto(url)
            await page.wait_for_timeout(3000)
            
            # Check if we got redirected (race doesn't exist)
            final_url = page.url
            if f"/HV/{race_number}" not in final_url:
                print(f"   ⚠️ Race {race_number} redirected - race may not exist")
                return None
            
            # Extract odds data using the working table extraction logic
            raw_odds_data = await extract_win_odds_from_page(page)
            
            if not raw_odds_data:
                print(f"   ⚠️ No odds data found for Race {race_number}")
                return None
            
            # Convert to structured format
            horses_data = convert_to_horses_data(raw_odds_data)
            
            if not horses_data:
                print(f"   ⚠️ Could not convert odds data for Race {race_number}")
                return None
            
            # Add place odds from same table
            place_horses_data = convert_to_horses_data(raw_odds_data, is_place_odds=True)
            if place_horses_data:
                horses_data = merge_place_odds(horses_data, place_horses_data)
            
            # Create race data structure
            race_data = {
                "race_info": {
                    "race_date": "2025/07/16",
                    "racecourse": "HV",
                    "race_number": race_number,
                    "race_id": f"2025-07-16_HV_R{race_number}",
                    "source_url": url,
                    "extracted_at": datetime.now().isoformat()
                },
                "horses_data": horses_data,
                "extraction_summary": {
                    "horses_extracted": len(horses_data),
                    "data_extraction_successful": True,
                    "method": "direct_url_extraction"
                }
            }
            
            print(f"   ✅ Successfully extracted {len(horses_data)} horses")
            return race_data
            
        except Exception as e:
            print(f"   ❌ Error extracting Race {race_number}: {str(e)}")
            return None
        finally:
            await browser.close()

async def extract_win_odds_from_page(page):
    """Extract raw odds data from page (using working logic from extract_odds_trends.py)"""
    try:
        # Wait for content to load
        await page.wait_for_timeout(2000)
        
        # Get all tables
        tables = await page.query_selector_all('table')
        
        raw_data = []
        
        for i, table in enumerate(tables):
            try:
                # Get table rows
                rows = await table.query_selector_all('tr')
                
                if len(rows) < 3:  # Need header, time, and at least one horse
                    continue
                
                table_data = []
                
                for row in rows:
                    cells = await row.query_selector_all('td, th')
                    row_data = []
                    
                    for cell in cells:
                        text = await cell.text_content()
                        row_data.append(text.strip() if text else '')
                    
                    if row_data:
                        table_data.append(row_data)
                
                if table_data:
                    raw_data.append({
                        'type': 'table',
                        'data': table_data
                    })
                    
            except Exception as e:
                continue
        
        return raw_data
        
    except Exception as e:
        print(f"   ❌ Error extracting odds from page: {str(e)}")
        return []

def convert_to_horses_data(raw_odds_data, is_place_odds=False):
    """Convert raw odds data to structured format (using working logic)"""
    try:
        horses_data = []
        
        for item in raw_odds_data:
            if item.get('type') != 'table':
                continue
                
            table_data = item.get('data', [])
            if len(table_data) < 3:
                continue
            
            # Get headers and time row
            headers = table_data[0]
            time_headers = []
            
            # Look for time row (contains time patterns)
            for row in table_data[1:3]:
                if any(':' in str(cell) for cell in row):
                    time_headers = [cell for cell in row if ':' in str(cell)]
                    break
            
            if not time_headers:
                continue
            
            # Process horse rows
            for row in table_data[2:]:
                if len(row) < 8:
                    continue
                
                horse_number = str(row[0]).strip()
                horse_name = str(row[2]).strip() if len(row) > 2 else ""
                
                if not horse_number or not horse_name:
                    continue
                
                # Extract basic info
                gate = str(row[3]).strip() if len(row) > 3 else ""
                weight = str(row[4]).strip() if len(row) > 4 else ""
                jockey = str(row[5]).strip() if len(row) > 5 else ""
                trainer = str(row[6]).strip() if len(row) > 6 else ""
                
                # Extract odds
                odds_data = []
                
                if is_place_odds:
                    # Place odds in last column
                    place_col = 7 + len(time_headers)
                    if place_col < len(row):
                        place_odds = str(row[place_col]).strip()
                        if place_odds and place_odds not in ['', '-']:
                            try:
                                float(place_odds)
                                odds_data = [{"odds": place_odds}]
                            except:
                                pass
                else:
                    # Win odds in time slots
                    for j, time_slot in enumerate(time_headers):
                        odds_col = 7 + j
                        if odds_col < len(row):
                            odds_value = str(row[odds_col]).strip()
                            if odds_value and odds_value not in ['', '-']:
                                try:
                                    float(odds_value)
                                    odds_data.append({
                                        "time": time_slot,
                                        "odds": odds_value
                                    })
                                except:
                                    continue
                
                if odds_data:
                    horse_data = {
                        "horse_number": horse_number,
                        "horse_name": horse_name
                    }
                    
                    if is_place_odds:
                        horse_data["place_odds_trend"] = odds_data
                    else:
                        horse_data["win_odds_trend"] = odds_data
                        horse_data["gate"] = gate
                        horse_data["weight"] = weight
                        horse_data["jockey"] = jockey
                        horse_data["trainer"] = trainer
                    
                    horses_data.append(horse_data)
        
        return horses_data
        
    except Exception as e:
        print(f"   ❌ Error converting odds data: {str(e)}")
        return []

def merge_place_odds(win_horses_data, place_horses_data):
    """Merge place odds into win odds data"""
    try:
        place_odds_lookup = {}
        for place_horse in place_horses_data:
            horse_num = place_horse.get('horse_number')
            if horse_num and 'place_odds_trend' in place_horse:
                place_odds_lookup[horse_num] = place_horse['place_odds_trend']
        
        for win_horse in win_horses_data:
            horse_num = win_horse.get('horse_number')
            if horse_num in place_odds_lookup:
                win_horse['place_odds_trend'] = place_odds_lookup[horse_num]
        
        return win_horses_data
        
    except Exception as e:
        print(f"   ❌ Error merging place odds: {str(e)}")
        return win_horses_data

async def save_race_data(race_data, race_number):
    """Save race data to file and PocketBase"""
    
    # Save to JSON file
    filename = f"{OUTPUT_DIR}/win_odds_trends_2025_07_16_HV_R{race_number}.json"
    
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(race_data, f, indent=2, ensure_ascii=False)
        print(f"   💾 Saved to: {filename}")
    except Exception as e:
        print(f"   ❌ Error saving file: {str(e)}")
        return False
    
    # Save to PocketBase
    try:
        pb = PocketBase(POCKETBASE_URL)
        pb.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
        
        race_info = race_data['race_info']
        record_data = {
            "race_date": "2025/07/16",
            "venue": "HV",
            "race_number": race_number,
            "data_type": "win_odds_trends",
            "extraction_status": "success",
            "source_url": race_info['source_url'],
            "scraped_at": datetime.now().isoformat(),
            "complete_data": json.dumps(race_data, ensure_ascii=False)
        }
        
        # Check if exists and update/create
        try:
            existing = pb.collection(COLLECTION_NAME).get_first_list_item(
                f'race_date="2025/07/16" && venue="HV" && race_number={race_number}'
            )
            pb.collection(COLLECTION_NAME).update(existing.id, record_data)
            print(f"   ✅ Updated PocketBase record")
        except:
            pb.collection(COLLECTION_NAME).create(record_data)
            print(f"   ✅ Created PocketBase record")
            
        return True
        
    except Exception as e:
        print(f"   ⚠️ PocketBase save failed: {str(e)}")
        return True  # Still success if file saved

async def main():
    """Extract all 2025-07-16 HV races"""
    
    print("🏇 Extracting 2025-07-16 HV Odds Trends")
    print("=" * 50)
    
    success_count = 0
    total_races = 9  # HV typically has 9 races
    
    for race_num in range(1, total_races + 1):
        race_data = await extract_race_odds_2025_07_16(race_num)
        
        if race_data:
            saved = await save_race_data(race_data, race_num)
            if saved:
                success_count += 1
        else:
            print(f"   ⏭️ Race {race_num}: Skipped")
    
    print("=" * 50)
    print(f"📊 SUMMARY: {success_count}/{total_races} races extracted")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
