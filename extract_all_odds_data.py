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

def is_valid_race_date_for_odds(race_date_str):
    """
    Validate that a race date is valid for odds extraction.
    Allows completed races and races from today (which may have final odds).

    Args:
        race_date_str (str): Race date in YYYY-MM-DD format

    Returns:
        bool: True if the date is valid for odds extraction, False otherwise
    """
    try:
        race_datetime = datetime.strptime(race_date_str, "%Y-%m-%d")
        today = datetime.now().date()

        # Allow races from today and earlier (completed races + today's races with final odds)
        # Exclude future races (no odds available yet)
        return race_datetime.date() <= today

    except (ValueError, TypeError):
        return False

def get_race_info_from_hkjc():
    """Get current race information from HKJC website - only past/completed races"""
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
        
        # Validate that the race date is valid for odds extraction
        if race_date and not is_valid_race_date_for_odds(race_date):
            print(f"⚠️ Skipping future race date: {race_date} (no odds available yet)")
            return None

        if race_date and racecourse and total_races > 0:
            print(f"✅ Found completed race: Date={race_date}, Venue={racecourse}, Races={total_races}")
            return (race_date, racecourse, total_races)

        print("⚠️ Could not extract complete race information or race is in the future")
        return None
        
    except Exception as e:
        print(f"❌ Error getting race info: {str(e)}")
        return None

def get_venue_from_database(race_date):
    """
    Get the venue for a race date from PocketBase database.
    This is more reliable than web scraping since it uses actual stored data.
    """
    try:
        client = PocketBase(POCKETBASE_URL)
        client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)

        # Query for records with this race date
        records = client.collection(COLLECTION_NAME).get_list(
            1, 1,  # Just need one record to determine venue
            {
                "filter": f'race_date="{race_date}"'
            }
        )

        if records.total_items > 0:
            venue = records.items[0].venue
            print(f"   📊 Database shows {race_date} venue: {venue}")
            return venue
        else:
            print(f"   ⚠️ No database records found for {race_date}")
            return None

    except Exception as e:
        print(f"   ❌ Database query error for {race_date}: {str(e)}")
        return None

def determine_venue_for_date(race_date):
    """
    Determine which venue (ST or HV) has races for a given date.
    First tries database, then falls back to web checking.
    Returns the venue code or None if no races found.
    """
    # Method 1: Check database first (most reliable)
    venue = get_venue_from_database(race_date)
    if venue:
        return venue

    # Method 2: Fallback to web checking with better redirect detection
    print(f"   🔍 Checking web for {race_date} venue...")

    # Try both venues, but use stricter validation
    for test_venue in ["ST", "HV"]:
        if check_race_date_exists_strict(race_date, test_venue):
            print(f"   ✅ Web check confirms {race_date} venue: {test_venue}")
            return test_venue

    return None

def check_race_date_exists_strict(race_date, venue):
    """
    Stricter version of race date checking that better detects redirects.
    Checks both URL and content to ensure we're not being redirected.
    """
    try:
        url = f"https://bet.hkjc.com/ch/racing/pwin/{race_date}/{venue}/1"
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }, timeout=10, allow_redirects=False)  # Don't follow redirects

        # If we get a redirect response, it means the date/venue doesn't exist
        if response.status_code in [301, 302, 303, 307, 308]:
            print(f"   🔄 {race_date} {venue} redirected (likely doesn't exist)")
            return False

        if response.status_code == 200:
            # Check the actual URL we ended up at
            final_url = response.url if hasattr(response, 'url') else url

            # Verify the URL still contains our requested date and venue
            if race_date in final_url and venue in final_url:
                # Additional content validation
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                page_text = soup.get_text()

                # Check for race-specific content
                if "第1場" in page_text or "Race 1" in page_text:
                    # Verify the date in the content matches our request
                    date_formatted = race_date.replace('-', '/')  # 2025/07/01
                    if date_formatted in page_text:
                        return True

            print(f"   ⚠️ {race_date} {venue} content validation failed")
            return False

        return False

    except Exception as e:
        print(f"   ❌ Error checking {race_date} {venue}: {e}")
        return False

def load_verified_odds_dates():
    """Load dates that are verified to have odds data available"""
    try:
        print("📅 Loading verified odds dates from database and authoritative sources...")

        verified_sessions = []

        # Method 1: Load from database (most reliable for existing odds data)
        try:
            client = PocketBase(POCKETBASE_URL)
            client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)

            # Get unique race dates from database
            records = client.collection(COLLECTION_NAME).get_list(
                1, 500,  # Get more records to find all dates
                {
                    "sort": "-race_date",
                    "fields": "race_date,venue"
                }
            )

            # Extract unique date/venue combinations
            db_sessions = {}
            for record in records.items:
                race_date = record.race_date
                venue = record.venue

                if race_date and venue and is_valid_race_date_for_odds(race_date):
                    if race_date not in db_sessions:
                        db_sessions[race_date] = {
                            'race_date': race_date,
                            'venue': venue,
                            'venue_name': "Sha Tin" if venue == "ST" else "Happy Valley",
                            'total_races': 12,  # Standard race count
                            'source': 'database',
                            'verified': True
                        }

            verified_sessions.extend(db_sessions.values())
            print(f"✅ Found {len(db_sessions)} dates with odds data in database")

        except Exception as e:
            print(f"⚠️ Could not load from database: {str(e)}")

        # Method 2: Add from authoritative Local Results if available
        if os.path.exists('hkjc_authoritative_dates.json'):
            try:
                with open('hkjc_authoritative_dates.json', 'r') as f:
                    data = json.load(f)

                race_sessions = data.get('race_sessions', [])
                existing_dates = {session['race_date'] for session in verified_sessions}

                for session in race_sessions:
                    race_date = session.get('race_date')
                    if (race_date and
                        is_valid_race_date_for_odds(race_date) and
                        race_date not in existing_dates):

                        session['source'] = 'local_results'
                        session['verified'] = True
                        verified_sessions.append(session)
                        print(f"   + Added from Local Results: {race_date}")

            except Exception as e:
                print(f"⚠️ Could not load authoritative dates: {str(e)}")

        # Method 3: Fallback to odds_dates.json
        if not verified_sessions and os.path.exists('odds_dates.json'):
            print("⚠️ No other sources available, using odds_dates.json...")

            with open('odds_dates.json', 'r') as f:
                odds_dates = json.load(f)

            for date_str in odds_dates:
                if is_valid_race_date_for_odds(date_str):
                    verified_sessions.append({
                        'race_date': date_str,
                        'venue': None,  # To be determined
                        'venue_name': 'Unknown',
                        'total_races': 10,
                        'source': 'odds_dates_json',
                        'verified': False
                    })

        # Sort by date (newest first)
        verified_sessions.sort(key=lambda x: x['race_date'], reverse=True)

        print(f"✅ Total verified sessions: {len(verified_sessions)}")
        for session in verified_sessions[:10]:  # Show first 10
            source = session.get('source', 'unknown')
            venue_name = session.get('venue_name', 'Unknown')
            print(f"   - {session['race_date']}: {session.get('venue', '?')} ({venue_name}) [{source}]")

        if len(verified_sessions) > 10:
            print(f"   ... and {len(verified_sessions) - 10} more")

        return verified_sessions

    except Exception as e:
        print(f"❌ Error loading verified odds dates: {str(e)}")
        return []

def check_recent_race_dates():
    """Check recent dates for new race data that might not be in odds_dates.json yet"""
    print("\n🔍 Checking recent dates for new race data...")
    recent_races = []
    today = datetime.now()

    # Check last 7 days for new race data
    for i in range(7):
        check_date = today - timedelta(days=i)
        date_str = check_date.strftime("%Y-%m-%d")

        # Only check valid dates
        if not is_valid_race_date_for_odds(date_str):
            continue

        print(f"   Checking {date_str} for new race data...")

        # Determine venue for this date
        venue = determine_venue_for_date(date_str)

        if venue:
            # Check if we can get race count
            total_races = estimate_total_races(date_str, venue)
            if total_races > 0:
                recent_races.append((date_str, venue, total_races))
                venue_name = "Sha Tin" if venue == "ST" else "Happy Valley"
                print(f"   ✅ Found new race data: {date_str} {venue} ({venue_name}) with {total_races} races")
        else:
            print(f"   ❌ No race data found for {date_str}")

    return recent_races

def get_available_race_dates():
    """Get available race dates from race_entries collection (most reliable source)"""
    race_dates = []

    print("📅 Loading race dates from race_entries collection...")

    try:
        client = PocketBase(POCKETBASE_URL)
        client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)

        # Get unique race dates and venues from race_entries collection
        records = client.collection("race_entries").get_list(
            1, 500,  # Get more records to find all dates
            {
                "sort": "-race_date",
                "fields": "race_date,venue"
            }
        )

        # Extract unique date/venue combinations
        race_sessions = {}
        for record in records.items:
            race_date = record.race_date
            venue = record.venue

            if race_date and venue and is_valid_race_date_for_odds(race_date):
                if race_date not in race_sessions:
                    # Handle both English and Chinese venue codes
                    if venue in ["ST", "沙田"]:
                        venue_code = "ST"
                        venue_name = "Sha Tin"
                    elif venue in ["HV", "跑馬地"]:
                        venue_code = "HV"
                        venue_name = "Happy Valley"
                    else:
                        venue_code = venue
                        venue_name = venue

                    race_sessions[race_date] = {
                        'race_date': race_date,
                        'venue': venue_code,
                        'venue_name': venue_name,
                        'total_races': 12  # Standard race count
                    }

        # Convert to race_dates format
        for session in race_sessions.values():
            race_date = session['race_date']
            venue = session['venue']
            total_races = session['total_races']
            venue_name = session['venue_name']

            race_dates.append((race_date, venue, total_races))
            print(f"   ✅ {race_date} {venue} ({venue_name}) with {total_races} races")

        print(f"✅ Found {len(race_dates)} race sessions from race_entries collection")

    except Exception as e:
        print(f"❌ Error loading from race_entries collection: {str(e)}")

        # Fallback: try to get current race info from HKJC
        print("🔍 Falling back to HKJC current race info...")
        current_race = get_race_info_from_hkjc()
        if current_race:
            race_date, venue, total_races = current_race
            if is_valid_race_date_for_odds(race_date):
                race_dates.append(current_race)
                venue_name = "Sha Tin" if venue == "ST" else "Happy Valley"
                print(f"   ✅ Current race: {race_date} {venue} ({venue_name}) with {total_races} races")
            else:
                print(f"   ⚠️ Current race date {race_date} is not valid for odds extraction")
        else:
            print("   ❌ Could not get current race info")

    # Sort by date (newest first)
    race_dates.sort(key=lambda x: x[0], reverse=True)

    if race_dates:
        print(f"\n📊 Final race schedule ({len(race_dates)} sessions):")
        for race_date, venue, total_races in race_dates:
            venue_name = "Sha Tin" if venue == "ST" else "Happy Valley"
            print(f"   - {race_date}: {venue} ({venue_name}) - {total_races} races")
    else:
        print("\n❌ No valid race dates found")

    return race_dates

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

def extract_race_info_from_current_page(page_text):
    """Extract race date and venue from current odds page"""
    try:
        import re

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

                    # Validate date is reasonable (within last 30 days to next 7 days)
                    from datetime import datetime, timedelta
                    date_obj = datetime.strptime(race_date, '%Y-%m-%d')
                    today = datetime.now()
                    days_diff = (date_obj - today).days

                    if -30 <= days_diff <= 7:  # Reasonable range
                        break
                    else:
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
            return (race_date, venue)
        else:
            return None

    except Exception as e:
        print(f"⚠️ Error extracting race info: {str(e)}")
        return None

async def extract_current_race_odds(race_number):
    """Extract odds for current/latest race using base URL"""
    try:
        # Use base URL to get latest race data
        url = f"https://bet.hkjc.com/ch/racing/pwin/"
        print(f"🏇 Extracting Race {race_number} from latest race data")

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

                # Get the page content to extract race info
                page_text = await page.text_content('body')

                # Extract race date and venue from the current page
                race_info = extract_race_info_from_current_page(page_text)

                if not race_info:
                    print(f"⚠️ Could not extract race info from current page")
                    return None

                race_date, venue = race_info
                print(f"✅ Found current race: {race_date} {venue}")

                # Navigate to specific race if not race 1
                if race_number != 1:
                    race_url = f"https://bet.hkjc.com/ch/racing/pwin/{race_date}/{venue}/{race_number}"
                    await page.goto(race_url, wait_until='domcontentloaded', timeout=30000)
                    await page.wait_for_timeout(3000)

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
        # Final validation: ensure we don't process future dates
        if not is_valid_race_date_for_odds(race_date):
            print(f"⚠️ Skipping future race date: {race_date} {venue} (no odds available yet)")
            continue

        print(f"\n🏁 Processing {race_date} {venue} ({total_races} races)")
        print("-" * 40)
        
        for race_number in range(1, total_races + 1):
            try:
                # Extract odds data
                data = await extract_current_race_odds(race_number)
                
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
