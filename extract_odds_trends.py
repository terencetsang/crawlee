#!/usr/bin/env python3
"""
HKJC Win Odds Trends Extractor - Simplified Base URL Approach
This is the main script for extracting odds trends data using the base URL method.
"""
import asyncio
import os
import json
import re
from datetime import datetime
from playwright.async_api import async_playwright
from pocketbase import PocketBase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
POCKETBASE_URL = os.getenv("POCKETBASE_URL", "https://crawlee.pockethost.io")
POCKETBASE_EMAIL = os.getenv("POCKETBASE_EMAIL")
POCKETBASE_PASSWORD = os.getenv("POCKETBASE_PASSWORD")
COLLECTION_NAME = "race_odds"
OUTPUT_DIR = "win_odds_data"

def extract_race_info_from_page(page_text):
    """Extract race date and venue from current odds page - UPCOMING races with live odds"""
    try:
        print("   🔍 Searching for upcoming race dates with live odds in page content...")

        # Look for date patterns in various formats
        date_patterns = [
            r'(\d{2})/(\d{2})/(\d{4})',  # DD/MM/YYYY (05/07/2025)
            r'(\d{4})/(\d{2})/(\d{2})',  # YYYY/MM/DD (2025/07/05)
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',  # Chinese format
        ]
        
        race_date = None
        for pattern in date_patterns:
            matches = re.findall(pattern, page_text)
            for match in matches:
                try:
                    if pattern.startswith(r'(\d{2})/'):  # DD/MM/YYYY
                        day, month, year = match
                        race_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    elif pattern.startswith(r'(\d{4})/'):  # YYYY/MM/DD
                        year, month, day = match
                        race_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    elif pattern.endswith(r'日'):  # Chinese format
                        year, month, day = match
                        race_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    
                    # Validate date is reasonable (accept UPCOMING races - today and near future)
                    from datetime import datetime, timedelta
                    date_obj = datetime.strptime(race_date, '%Y-%m-%d').date()
                    today = datetime.now().date()
                    days_diff = (date_obj - today).days

                    # Accept recent past, today, and upcoming races within next 7 days
                    # This is where odds data might still be available
                    if -2 <= days_diff <= 7:  # Yesterday, today, and next 7 days
                        if days_diff == 0:
                            print(f"   ✅ Found today's race date: {race_date} (today)")
                        elif days_diff < 0:
                            print(f"   ✅ Found recent race date: {race_date} ({abs(days_diff)} days ago)")
                        else:
                            print(f"   ✅ Found upcoming race date: {race_date} ({days_diff} days from today)")
                        break
                    else:
                        print(f"   ⚠️ Skipping date {race_date} (days_diff: {days_diff}) - not a recent/upcoming race with odds data")
                        race_date = None
                except:
                    continue
            
            if race_date:
                break
        
        # Look for venue information
        venue = None
        if "沙田" in page_text:
            venue = "ST"
        elif "跑馬地" in page_text:
            venue = "HV"
        
        if race_date and venue:
            print(f"   ✅ Successfully extracted upcoming race info: {race_date} {venue}")
            return (race_date, venue)
        else:
            print("   ❌ Could not find upcoming race date and venue in page")
            print("   ℹ️  This may mean no upcoming races with live odds are available")
            return None
            
    except Exception as e:
        print(f"⚠️ Error extracting race info: {str(e)}")
        return None

async def extract_race_odds(race_number=1):
    """Extract odds for latest race using base URL"""
    try:
        # Use base URL to get latest race data
        base_url = "https://bet.hkjc.com/ch/racing/pwin/"
        print(f"🏇 Extracting Race {race_number} from latest race data")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )

            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='zh-HK',
                java_script_enabled=True,
                accept_downloads=False,
                ignore_https_errors=True
            )

            page = await context.new_page()

            try:
                # Load base URL to get latest race
                print("   🌐 Loading HKJC page...")
                await page.goto(base_url, wait_until='networkidle', timeout=30000)

                # Wait for JavaScript to load content with multiple strategies
                print("   ⏳ Waiting for JavaScript content to load...")

                # Strategy 1: Wait for page to be fully loaded
                await page.wait_for_load_state('networkidle', timeout=20000)

                # Strategy 2: Wait longer for dynamic content
                print("   ⏳ Waiting for dynamic content...")
                await page.wait_for_timeout(15000)

                # Strategy 3: Try to wait for specific odds-related content
                try:
                    # Wait for content that suggests odds data is present
                    await page.wait_for_function(
                        "() => document.body.textContent.length > 5000 || document.querySelectorAll('table').length > 0",
                        timeout=20000
                    )
                    print("   ✅ Content appears to be loaded")
                except:
                    print("   ⚠️ Timeout waiting for content, but continuing...")

                # Strategy 4: Check multiple times for content
                for attempt in range(3):
                    page_text = await page.text_content('body')
                    content_length = len(page_text)

                    print(f"   📋 Attempt {attempt + 1}: Content length = {content_length} chars")

                    if "You need to enable JavaScript" not in page_text and content_length > 5000:
                        print("   ✅ JavaScript content successfully loaded!")
                        break
                    elif attempt < 2:
                        print(f"   ⏳ Content still loading, waiting more... (attempt {attempt + 1}/3)")
                        await page.wait_for_timeout(10000)
                    else:
                        print("   ⚠️ Content may not be fully loaded, but proceeding with extraction...")
                        break

                # Get the page content to extract race info
                page_text = await page.text_content('body')

                # Extract race date and venue from the current page
                race_info = extract_race_info_from_page(page_text)
                
                if not race_info:
                    print(f"   ⚠️ Could not extract race info from current page")
                    return None
                
                race_date, venue = race_info
                venue_name = "Sha Tin" if venue == "ST" else "Happy Valley"
                print(f"   ✅ Found current race: {race_date} {venue} ({venue_name})")

                # Navigate to specific race if not race 1
                if race_number != 1:
                    race_url = f"https://bet.hkjc.com/ch/racing/pwin/{race_date}/{venue}/{race_number}"
                    print(f"   🔗 Navigating to: {race_url}")
                    await page.goto(race_url, wait_until='networkidle', timeout=30000)

                    # Check if URL redirected (race doesn't exist)
                    current_url = page.url
                    print(f"   📋 Current URL after navigation: {current_url}")

                    # Extract race number from current URL to check for redirect
                    url_race_match = re.search(r'/(\d+)$', current_url)
                    if url_race_match:
                        actual_race_number = int(url_race_match.group(1))
                        if actual_race_number != race_number:
                            print(f"   ⚠️ URL redirected from Race {race_number} to Race {actual_race_number}")
                            print(f"   ❌ Race {race_number} does not exist - skipping")
                            return None
                        else:
                            print(f"   ✅ Successfully navigated to Race {race_number}")

                    # Wait for race page content to load
                    print("   ⏳ Waiting for race page content...")
                    await page.wait_for_timeout(12000)

                    # Check content multiple times
                    for attempt in range(2):
                        page_text = await page.text_content('body')
                        content_length = len(page_text)

                        if "You need to enable JavaScript" not in page_text and content_length > 3000:
                            print(f"   ✅ Race page content loaded ({content_length} chars)")
                            break
                        elif attempt < 1:
                            print(f"   ⏳ Race page still loading, waiting more...")
                            await page.wait_for_timeout(10000)
                        else:
                            print(f"   ⚠️ Race page content may be limited ({content_length} chars)")
                            break

                # Extract REAL odds data from the page
                print("🔍 Extracting real odds data from HKJC page...")

                # Debug: Show current page info
                current_url = page.url
                page_title = await page.title()
                page_content = await page.text_content('body')
                print(f"   📋 Current URL: {current_url}")
                print(f"   📋 Page title: {page_title}")
                print(f"   📋 Content length: {len(page_content)} chars")

                # Show a sample of the content to see what we're getting
                if page_content:
                    # Look for Chinese characters or numbers that might indicate odds
                    sample = page_content[:500].replace('\n', ' ').strip()
                    print(f"   📋 Content sample: {sample}...")

                raw_odds_data = await extract_win_odds_from_page(page)

                # Check if any odds data was found
                has_odds_data = raw_odds_data and len(raw_odds_data) > 0

                if not has_odds_data:
                    print(f"   ⚠️ No odds data found for Race {race_number} - skipping")
                    return None

                # Convert raw odds data to structured horses_data format
                horses_data = convert_to_horses_data(raw_odds_data)

                if not horses_data:
                    print(f"   ⚠️ Could not convert odds data to horses format for Race {race_number} - skipping")
                    return None

                # Extract place odds from the same table (place odds are in the last column)
                print("🔍 Extracting place odds from same table...")
                try:
                    place_horses_data = convert_to_horses_data(raw_odds_data, is_place_odds=True)

                    if place_horses_data:
                        print(f"   ✅ Successfully extracted place odds for {len(place_horses_data)} horses")
                        # Merge place odds into win odds data
                        horses_data = merge_place_odds(horses_data, place_horses_data)
                    else:
                        print("   ⚠️ Could not extract place odds data from table")

                except Exception as e:
                    print(f"   ⚠️ Error extracting place odds: {str(e)}")
                    # Continue without place odds

                # Prepare result with structured horse data (matching 2025-07-05 format)
                race_data = {
                    "race_info": {
                        "race_date": race_date,
                        "venue": venue,
                        "race_number": race_number,
                        "source_url": page.url,
                        "scraped_at": datetime.now().isoformat()
                    },
                    "horses_data": horses_data,
                    "extraction_summary": {
                        "horses_extracted": len(horses_data),
                        "data_extraction_successful": True,
                        "method": "base_url_upcoming_race_real_extraction"
                    }
                }

                print(f"   ✅ Successfully extracted race data with {len(horses_data)} horses")
                return race_data

            finally:
                await browser.close()
                
    except Exception as e:
        print(f"   ❌ Error extracting race odds: {str(e)}")
        return None

def save_to_pocketbase(data, race_date, venue, race_number):
    """Save odds data to PocketBase with overwrite behavior"""
    try:
        client = PocketBase(POCKETBASE_URL)
        
        # Authenticate
        try:
            client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
            print(f"   ✅ Connected to PocketBase")
        except Exception as auth_error:
            print(f"   ❌ Authentication failed: {str(auth_error)}")
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
        
        # Check if record exists (overwrite behavior)
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
                client.collection(COLLECTION_NAME).update(record_id, record_data)
                print(f"   ✅ Updated existing record in PocketBase")
            else:
                # Create new record
                client.collection(COLLECTION_NAME).create(record_data)
                print(f"   ✅ Created new record in PocketBase")
            
            return True
            
        except Exception as db_error:
            print(f"   ❌ Database operation failed: {str(db_error)}")
            return False
        
    except Exception as e:
        print(f"   ❌ PocketBase error: {str(e)}")
        return False

def convert_to_horses_data(raw_odds_data, is_place_odds=False):
    """Convert raw odds data to structured horses_data format matching 2025-07-05 structure"""
    try:
        horses_data = []
        extracted_at = datetime.now().isoformat()

        # Look for table data that contains horse information
        for odds_item in raw_odds_data:
            if odds_item.get('type') == 'table' and 'data' in odds_item:
                table_data = odds_item['data']

                # Find the header row to understand column structure
                header_row = None
                for i, row in enumerate(table_data):
                    if any('馬號' in str(cell) or 'horse' in str(cell).lower() for cell in row):
                        header_row = i
                        break

                if header_row is None:
                    continue

                headers = table_data[header_row]

                # Find column indices for detailed horse information
                horse_num_col = None
                horse_name_col = None
                gate_col = None
                weight_col = None
                jockey_col = None
                trainer_col = None
                odds_time_cols = []

                # Parse header to find all columns
                for j, header in enumerate(headers):
                    header_str = str(header).strip()
                    if '馬號' in header_str:
                        horse_num_col = j
                    elif '馬名' in header_str:
                        horse_name_col = j
                    elif '檔位' in header_str:
                        gate_col = j
                    elif '負磅' in header_str:
                        weight_col = j
                    elif '騎師' in header_str:
                        jockey_col = j
                    elif '練馬師' in header_str:
                        trainer_col = j
                    elif ':' in header_str or any(keyword in header_str for keyword in ['賠率', 'odds', '獨贏']):
                        # This might be a time column for odds trends
                        odds_time_cols.append(j)

                # If columns not found by header, try to infer from position
                if horse_num_col is None and len(headers) > 0:
                    horse_num_col = 0
                if horse_name_col is None and len(headers) > 2:
                    horse_name_col = 2
                if gate_col is None and len(headers) > 3:
                    gate_col = 3
                if weight_col is None and len(headers) > 4:
                    weight_col = 4
                if jockey_col is None and len(headers) > 5:
                    jockey_col = 5
                if trainer_col is None and len(headers) > 6:
                    trainer_col = 6

                # Extract time headers for odds trends
                time_headers = []
                time_row_index = None

                # Look for the time row (usually row 1 after headers)
                for i, row in enumerate(table_data[:5]):  # Check first 5 rows
                    row_times = []
                    for cell in row:
                        cell_str = str(cell).strip()
                        # Look for time patterns like "07:30", "15:59", "16:01"
                        if re.match(r'^\d{1,2}:\d{2}$', cell_str):
                            row_times.append(cell_str)

                    # If we found multiple time values in this row, it's our time header row
                    if len(row_times) >= 2:
                        time_headers = row_times
                        time_row_index = i
                        print(f"   🕐 Found {len(time_headers)} time slots: {time_headers}")
                        break

                # If no dedicated time row found, look for times in header text
                if not time_headers:
                    header_text = ' '.join(str(cell) for cell in headers)
                    time_matches = re.findall(r'(\d{1,2}:\d{2})', header_text)
                    time_headers = time_matches

                # Process data rows (skip header and time rows)
                start_row = header_row + 1
                if time_row_index is not None and time_row_index > header_row:
                    start_row = time_row_index + 1  # Start after the time row

                for i, row in enumerate(table_data[start_row:], start=start_row):
                    if len(row) <= max(horse_num_col or 0, horse_name_col or 0):
                        continue

                    # Skip time/header rows - be more flexible
                    row_text = ' '.join(str(cell) for cell in row[:5])
                    if any(pattern in row_text for pattern in [':', '------', '馬號', '位置']):
                        continue

                    # Extract detailed horse data
                    horse_number = None
                    horse_name = None
                    gate = None
                    weight = None
                    jockey = None
                    trainer = None
                    win_odds_trend = []
                    place_odds_trend = []

                    # Extract horse number
                    if horse_num_col is not None and horse_num_col < len(row):
                        try:
                            num_str = str(row[horse_num_col]).strip()
                            num_match = re.search(r'(\d+)', num_str)
                            if num_match:
                                horse_number = num_match.group(1)  # Keep as string
                        except:
                            continue

                    # Extract horse name
                    if horse_name_col is not None and horse_name_col < len(row):
                        horse_name = str(row[horse_name_col]).strip()
                        # Clean up horse name - remove jockey/trainer info if present
                        if '騎' in horse_name:
                            horse_name = horse_name.split('騎')[0].strip()
                        if not horse_name or horse_name in ['', '-', '------']:
                            continue

                    # Extract gate (檔位)
                    if gate_col is not None and gate_col < len(row):
                        gate_str = str(row[gate_col]).strip()
                        gate_match = re.search(r'(\d+)', gate_str)
                        if gate_match:
                            gate = gate_match.group(1)

                    # Extract weight (負磅)
                    if weight_col is not None and weight_col < len(row):
                        weight_str = str(row[weight_col]).strip()
                        weight_match = re.search(r'(\d+)', weight_str)
                        if weight_match:
                            weight = weight_match.group(1)

                    # Extract jockey (騎師)
                    if jockey_col is not None and jockey_col < len(row):
                        jockey = str(row[jockey_col]).strip()
                        # Clean up jockey name - remove weight adjustments like "(-10)"
                        jockey = re.sub(r'\s*\([^)]*\)', '', jockey).strip()
                        if not jockey or jockey in ['', '-', '------']:
                            jockey = None

                    # Extract trainer (練馬師)
                    if trainer_col is not None and trainer_col < len(row):
                        trainer = str(row[trainer_col]).strip()
                        if not trainer or trainer in ['', '-', '------']:
                            trainer = None

                    # Extract odds trends - handle the new table structure
                    if time_headers:
                        # Find odds columns that correspond to time slots
                        # In the new structure, odds values are in consecutive columns after the basic horse info
                        odds_start_col = max(trainer_col or 6, 7)  # Start after trainer column

                        if is_place_odds:
                            # For place odds, get the value from the last column (after all win odds)
                            place_odds_col = odds_start_col + len(time_headers)
                            if place_odds_col < len(row):
                                place_odds_value = str(row[place_odds_col]).strip()
                                if place_odds_value and place_odds_value not in ['', '-', '------']:
                                    try:
                                        float(place_odds_value)  # Validate it's a number
                                        # For place odds, we'll create a single entry (not time-based)
                                        place_odds_trend.append({
                                            "odds": place_odds_value
                                        })
                                    except:
                                        pass
                        else:
                            # For win odds, extract time-based odds
                            for j, time_slot in enumerate(time_headers):
                                odds_col = odds_start_col + j
                                if odds_col < len(row):
                                    odds_value = str(row[odds_col]).strip()
                                    if odds_value and odds_value not in ['', '-', '------']:
                                        try:
                                            float(odds_value)  # Validate it's a number
                                            win_odds_trend.append({
                                                "time": time_slot,
                                                "odds": odds_value
                                            })
                                        except:
                                            continue

                    # Fallback: if no time headers found, try the old method
                    if not win_odds_trend:
                        for j, col_idx in enumerate(odds_time_cols):
                            if col_idx < len(row):
                                odds_value = str(row[col_idx]).strip()
                                if odds_value and odds_value not in ['', '-', '------']:
                                    try:
                                        float(odds_value)  # Validate it's a number
                                        time_str = time_headers[j] if j < len(time_headers) else f"time_{j}"
                                        win_odds_trend.append({
                                            "time": time_str,
                                            "odds": odds_value
                                        })
                                    except:
                                        continue

                    # If we have valid horse data, add it
                    if horse_number and horse_name:
                        horse_data = {
                            "horse_number": horse_number,
                            "horse_name": horse_name
                        }

                        # Add odds data based on type
                        if is_place_odds:
                            if place_odds_trend:
                                horse_data["place_odds_trend"] = place_odds_trend
                        else:
                            horse_data["win_odds_trend"] = win_odds_trend

                        # Add optional fields if available (only for win odds, not place odds)
                        if not is_place_odds:
                            if gate:
                                horse_data["gate"] = gate
                            if weight:
                                horse_data["weight"] = weight
                            if jockey:
                                horse_data["jockey"] = jockey
                            if trainer:
                                horse_data["trainer"] = trainer

                        horses_data.append(horse_data)

                # If we found horses in this table, we're done
                if horses_data:
                    break

        return horses_data

    except Exception as e:
        print(f"   ❌ Error converting odds data to horses format: {str(e)}")
        return []

def merge_place_odds(win_horses_data, place_horses_data):
    """Merge place odds data into win odds data"""
    try:
        # Create a lookup dictionary for place odds by horse number
        place_odds_lookup = {}
        for place_horse in place_horses_data:
            horse_num = place_horse.get('horse_number')
            if horse_num and 'place_odds_trend' in place_horse:
                place_odds_lookup[horse_num] = place_horse['place_odds_trend']

        # Add place odds to win horses data
        for win_horse in win_horses_data:
            horse_num = win_horse.get('horse_number')
            if horse_num in place_odds_lookup:
                win_horse['place_odds_trend'] = place_odds_lookup[horse_num]

        return win_horses_data

    except Exception as e:
        print(f"   ❌ Error merging place odds: {str(e)}")
        return win_horses_data

async def extract_win_odds_from_page(page):
    """Extract win odds data from the current page"""
    try:
        odds_data = []

        # Method 1: Look for tables with odds data
        print("   🔍 Method 1: Looking for odds tables...")
        tables = await page.query_selector_all('table')
        print(f"   📋 Found {len(tables)} tables on page")

        for i, table in enumerate(tables):
            try:
                table_text = await table.text_content()

                # Debug: Show first 100 characters of each table
                preview = table_text[:100].replace('\n', ' ').strip() if table_text else ""
                print(f"   📋 Table {i+1} preview: {preview}...")

                # Check if this table contains odds-related content
                if any(keyword in table_text for keyword in ['賠率', 'odds', '獨贏', 'win', '馬', 'horse']):
                    print(f"   📊 Found potential odds table {i+1}")

                    rows = await table.query_selector_all('tr')
                    table_data = []

                    for row in rows:
                        cells = await row.query_selector_all('td, th')
                        if cells:
                            row_data = []
                            for cell in cells:
                                text = await cell.text_content()
                                row_data.append(text.strip() if text else "")

                            if any(cell for cell in row_data):  # Skip empty rows
                                table_data.append(row_data)

                    if table_data:
                        odds_data.append({
                            "type": "table",
                            "table_index": i + 1,
                            "data": table_data
                        })
                        print(f"   ✅ Extracted {len(table_data)} rows from table {i+1}")
            except Exception as e:
                print(f"   ⚠️ Error processing table {i+1}: {str(e)}")
                continue

        # Method 2: Look for specific odds elements
        print("   🔍 Method 2: Looking for odds elements...")
        odds_selectors = [
            '[class*="odds"]',
            '[data-testid*="odds"]',
            '[class*="win"]',
            '[data-testid*="win"]',
            '.horse-odds',
            '.win-odds',
            '.odds-value'
        ]

        for selector in odds_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    element_data = []
                    for element in elements:
                        text = await element.text_content()
                        if text and text.strip():
                            element_data.append(text.strip())

                    if element_data:
                        odds_data.append({
                            "type": "elements",
                            "selector": selector,
                            "data": element_data
                        })
                        print(f"   📊 Found {len(element_data)} odds elements with selector: {selector}")
            except:
                continue

        # Method 3: Look for any text that looks like odds
        print("   🔍 Method 3: Looking for odds patterns in text...")
        page_text = await page.text_content('body')

        # Debug: Show page text length and sample
        print(f"   📋 Page text length: {len(page_text)} characters")
        if page_text:
            sample_text = page_text[:200].replace('\n', ' ').strip()
            print(f"   📋 Page text sample: {sample_text}...")

        # Look for odds patterns (numbers with decimal points that could be odds)
        odds_patterns = re.findall(r'\b\d+\.\d{1,2}\b', page_text)
        print(f"   📋 Found {len(odds_patterns)} decimal number patterns")

        if odds_patterns:
            # Filter to likely odds values (typically between 1.0 and 999.0)
            likely_odds = [float(odds) for odds in odds_patterns if 1.0 <= float(odds) <= 999.0]
            print(f"   📋 Filtered to {len(likely_odds)} likely odds values")

            if likely_odds:
                odds_data.append({
                    "type": "text_patterns",
                    "data": likely_odds
                })
                print(f"   📊 Found {len(likely_odds)} potential odds values in text")
                # Show first few odds as sample
                sample_odds = likely_odds[:5]
                print(f"   📊 Sample odds: {sample_odds}")

        return odds_data if odds_data else None

    except Exception as e:
        print(f"   ❌ Error extracting odds from page: {str(e)}")
        return None

async def main():
    """Main extraction function - extracts current/latest race data using base URL"""
    print("🏇 HKJC Win Odds Trends Extractor - LIVE ODDS FOR UPCOMING RACES")
    print("=" * 75)
    print("📋 Strategy: Extract live odds data for upcoming races (today and near future)")
    print("🎯 Target: Upcoming races with active betting and live odds")
    print("=" * 75)
    
    total_extracted = 0
    total_saved = 0
    
    # First, get the upcoming race info by checking race 1
    print("\n🔍 Getting upcoming race information with live odds...")
    
    try:
        # Extract race 1 to get race info
        first_race_data = await extract_race_odds(1)

        if not first_race_data:
            print("⚠️ No odds data found for Race 1 - will try other races")
            print("💡 This is normal if:")
            print("   • HKJC has anti-bot protection blocking odds data")
            print("   • Betting is closed for this race")
            print("   • Race has already started or finished")

            # Try to get race info from a different approach or continue anyway
            print("\n🔄 Continuing to process other races...")
            race_date = "2025-07-13"  # Default upcoming date
            venue = "ST"  # Default venue
            venue_name = "Sha Tin"
        else:
            # Extract race info from the first race data
            race_info = first_race_data.get('race_info', {})
            race_date = race_info.get('race_date')
            venue = race_info.get('venue')
            venue_name = "Sha Tin" if venue == "ST" else "Happy Valley"
        
        print(f"✅ Target races: {race_date} {venue} ({venue_name})")

        # Process all races (default to 12)
        total_races = 12
        print(f"📊 Processing {total_races} races (will skip races with no odds data)")

        # Initialize counters
        total_extracted = 0
        total_saved = 0

        # Process first race if data was found
        if first_race_data:
            total_extracted = 1

            # Save first race data
            formatted_date = race_date.replace('-', '_')
            json_filename = f"{OUTPUT_DIR}/win_odds_trends_{formatted_date}_{venue}_R1.json"
            os.makedirs(OUTPUT_DIR, exist_ok=True)

            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(first_race_data, f, ensure_ascii=False, indent=2)

            # Save to PocketBase
            if save_to_pocketbase(first_race_data, race_date, venue, 1):
                total_saved = 1

            # Count extracted horses data
            horses_data = first_race_data.get('horses_data', [])
            horses_count = len(horses_data) if horses_data else 0
            print(f"   ✅ Race 1: {horses_count} horses extracted")
        else:
            print(f"   ⏭️ Race 1: Skipped (no odds data found)")
        
        # Process remaining races
        print(f"\n🏁 Processing remaining races for {race_date} {venue}")
        print("-" * 50)
        
        for race_number in range(2, total_races + 1):
            try:
                print(f"\n🏁 Processing Race {race_number}...")
                
                # Extract odds data
                data = await extract_race_odds(race_number)

                if data:
                    total_extracted += 1

                    # Save backup JSON
                    formatted_date = race_date.replace('-', '_')
                    json_filename = f"{OUTPUT_DIR}/win_odds_trends_{formatted_date}_{venue}_R{race_number}.json"

                    with open(json_filename, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

                    # Save to PocketBase
                    if save_to_pocketbase(data, race_date, venue, race_number):
                        total_saved += 1

                    # Count extracted horses data
                    horses_data = data.get('horses_data', [])
                    horses_count = len(horses_data) if horses_data else 0
                    print(f"   ✅ Race {race_number}: {horses_count} horses extracted")
                else:
                    print(f"   ⏭️ Race {race_number}: Skipped (no odds data found)")
                
                # Small delay between requests
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"   ❌ Race {race_number}: Error - {str(e)}")
                continue
        
    except Exception as e:
        print(f"❌ Error in main extraction: {str(e)}")
    
    print("\n" + "=" * 75)
    print("📊 FINAL SUMMARY:")
    print(f"📅 Race Date: {race_date if 'race_date' in locals() else 'Unknown'}")
    print(f"🏟️ Venue: {venue} ({venue_name if 'venue_name' in locals() else 'Unknown'})")
    print(f"✅ Races with odds data: {total_extracted}/{total_races}")
    print(f"⏭️ Races skipped (no data): {total_races - total_extracted}/{total_races}")
    print(f"💾 Records saved to PocketBase: {total_saved}")
    print(f"📁 Backup files created: {total_extracted}")
    print(f"📂 Backup directory: {OUTPUT_DIR}/")
    print("🎯 Method: Skip races with no odds data (normal with anti-bot protection)")
    print("=" * 75)

if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    asyncio.run(main())
