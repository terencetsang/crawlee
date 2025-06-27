import asyncio
import json
import re
import os
import requests
from crawlee.beautifulsoup_crawler import BeautifulSoupCrawler, BeautifulSoupCrawlingContext
from pocketbase import PocketBase
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Load environment variables from .env file
load_dotenv()

# PocketBase configuration from environment variables
POCKETBASE_URL = os.getenv("POCKETBASE_URL")
POCKETBASE_EMAIL = os.getenv("POCKETBASE_EMAIL")
POCKETBASE_PASSWORD = os.getenv("POCKETBASE_PASSWORD")
COLLECTION_NAME = os.getenv("POCKETBASE_RESULTS_COLLECTION", "race_results")

# Output directory for JSON files
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "race_results_data")

def construct_results_url(race_date, racecourse, race_no):
    """
    Construct the HKJC race results URL with variable parameters.
    
    Args:
        race_date (str): Race date in format YYYY/MM/DD (e.g., "2024/12/15")
        racecourse (str): Racecourse code ("ST" for Sha Tin, "HV" for Happy Valley)
        race_no (int): Race number (1-10 typically)
    
    Returns:
        str: Complete URL for the race results page
    """
    base_url = "https://racing.hkjc.com/racing/information/Chinese/Racing/LocalResults.aspx"
    return f"{base_url}?RaceDate={race_date}&Racecourse={racecourse}&RaceNo={race_no}"

def ensure_results_collection_exists():
    """
    Ensure the PocketBase collection for race results exists.
    Creates the collection with appropriate schema if it doesn't exist.
    """
    try:
        # Check if collection exists
        response = requests.get(f"{POCKETBASE_URL}/api/collections/{COLLECTION_NAME}")
        
        if response.status_code == 404:
            print(f"Collection '{COLLECTION_NAME}' does not exist. Creating...")
            
            # Login to PocketBase admin
            login_data = {
                "identity": POCKETBASE_EMAIL,
                "password": POCKETBASE_PASSWORD
            }
            
            login_response = requests.post(f"{POCKETBASE_URL}/api/collections/users/auth-with-password", json=login_data)
            
            if login_response.status_code != 200:
                print(f"Failed to login to PocketBase: {login_response.text}")
                return False
            
            token = login_response.json()["token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Create collection schema for race results
            collection_data = {
                "name": COLLECTION_NAME,
                "type": "base",
                "schema": [
                    {"name": "race_date", "type": "text", "required": True},
                    {"name": "racecourse", "type": "text", "required": True},
                    {"name": "race_number", "type": "text", "required": True},
                    {"name": "race_name", "type": "text"},
                    {"name": "race_class", "type": "text"},
                    {"name": "distance", "type": "text"},
                    {"name": "track_condition", "type": "text"},
                    {"name": "track_type", "type": "text"},
                    {"name": "prize_money", "type": "text"},
                    {"name": "race_time", "type": "text"},
                    {"name": "sectional_times", "type": "json"},
                    {"name": "results", "type": "json"},
                    {"name": "payouts", "type": "json"},
                    {"name": "incidents", "type": "json"},
                    {"name": "raw_data", "type": "json"}
                ]
            }
            
            create_response = requests.post(f"{POCKETBASE_URL}/api/collections", json=collection_data, headers=headers)
            
            if create_response.status_code == 200 or create_response.status_code == 201:
                print(f"Collection '{COLLECTION_NAME}' created successfully!")
                return True
            else:
                print(f"Failed to create collection: {create_response.text}")
                return False
        else:
            print(f"Collection '{COLLECTION_NAME}' already exists.")
            return True
    except Exception as e:
        print(f"Error checking/creating collection: {str(e)}")
        return False

async def scrape_race_results(race_date, racecourse, race_no):
    """
    Scrape race results for a specific race.
    
    Args:
        race_date (str): Race date in format YYYY/MM/DD
        racecourse (str): Racecourse code ("ST" or "HV")
        race_no (int): Race number
    
    Returns:
        dict: Extracted race results data or None if no data found
    """
    target_url = construct_results_url(race_date, racecourse, race_no)
    print(f"Scraping race results from: {target_url}")
    
    # Create a BeautifulSoupCrawler instance
    crawler = BeautifulSoupCrawler()
    
    results_data = None
    
    # Define a request handler to process the page
    @crawler.router.default_handler
    async def request_handler(context: BeautifulSoupCrawlingContext) -> None:
        nonlocal results_data
        context.log.info(f'Processing {context.request.url} ...')
        
        try:
            # Check if page has results data
            if "沒有相關資料" in context.soup.get_text():
                context.log.info("No race data found for this date/race combination")
                results_data = None
                return
            
            # Extract race results
            results_data = extract_race_results(context, race_date, racecourse, race_no)
            
            if results_data:
                # Store the extracted data
                await context.push_data(results_data)
                
                # Print the extracted information
                print("\n--- Extracted Race Results ---")
                print(json.dumps(results_data, ensure_ascii=False, indent=2))
                print("------------------------------\n")
            
        except Exception as e:
            context.log.error(f"Error extracting race results: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Run the crawler with the target URL
    await crawler.run([target_url])
    
    return results_data

def extract_race_results(context, race_date, racecourse, race_no):
    """
    Extract race results from the BeautifulSoup context.
    
    Args:
        context: BeautifulSoupCrawlingContext
        race_date (str): Race date
        racecourse (str): Racecourse code
        race_no (int): Race number
    
    Returns:
        dict: Structured race results data
    """
    try:
        soup = context.soup
        
        # Extract basic race information
        race_info = extract_race_info_from_results(soup)
        
        # Extract finishing positions and horse details
        results = extract_finishing_positions(soup)
        
        # Extract sectional times
        sectional_times = extract_sectional_times(soup)
        
        # Extract payouts
        payouts = extract_payouts(soup)
        
        # Extract race incidents/reports
        incidents = extract_race_incidents(soup)

        # Extract performance data (pass fixed sectional times)
        performance_data = extract_performance_data(soup, results, sectional_times)

        # Generate field analysis from performance data
        field_analysis = generate_field_analysis(performance_data.get('horse_performance', []))

        # Combine all data
        race_results = {
            "race_date": race_date,
            "racecourse": racecourse,
            "race_number": str(race_no),
            "race_info": race_info,
            "sectional_times": sectional_times,
            "results": results,
            "payouts": payouts,
            "incidents": incidents,
            "performance": performance_data,
            "field_analysis": field_analysis,
            "scraped_at": datetime.now().isoformat()
        }
        
        return race_results
        
    except Exception as e:
        print(f"Error extracting race results: {str(e)}")
        return None

def extract_race_info_from_results(soup):
    """Extract basic race information from results page."""
    race_info = {}

    try:
        # Look for race title and details
        # The race information is split across multiple text elements
        race_text_elements = soup.find_all(text=True)

        race_number_text = ""
        race_class_distance_text = ""

        # Find race number text (e.g., "第 9 場 (725)")
        for text in race_text_elements:
            text_str = str(text).strip()
            if re.search(r'第\s*\d+\s*場', text_str):
                race_number_text = text_str
                race_info["race_number_text"] = race_number_text

                # Extract race number
                race_num_match = re.search(r'第\s*(\d+)\s*場', text_str)
                if race_num_match:
                    race_info["race_number"] = race_num_match.group(1)
                break

        # Find class/distance text (e.g., "第三班 - 1400米 - (80-60)" or "一級賽 - 2000米" or "四歲 - 1800米")
        for text in race_text_elements:
            text_str = str(text).strip()
            # Enhanced pattern matching for different race types
            # Check for valid race info patterns and exclude incident reports
            is_valid_race_info = False

            # Pattern 1: Contains distance (米) and race-related keywords
            if "米" in text_str and len(text_str) < 100:  # Exclude long incident reports
                # Valid race info patterns
                if any(pattern in text_str for pattern in ["班", "級賽", "新馬", "讓賽", "歲"]):
                    # Exclude incident report patterns
                    incident_keywords = ["發生碰撞", "被警告", "須抽取樣本", "接受獸醫檢查", "賽後", "騎師", "練馬師"]
                    if not any(keyword in text_str for keyword in incident_keywords):
                        is_valid_race_info = True

            if is_valid_race_info:
                race_class_distance_text = text_str
                race_info["class_distance_text"] = race_class_distance_text

                # Extract race class - Enhanced to handle multiple race types
                race_class = None

                # Pattern 1: Regular class races (第一班, 第二班, etc.)
                class_match = re.search(r'第([一二三四五])班', text_str)
                if class_match:
                    race_class = f"第{class_match.group(1)}班"

                # Pattern 2: Group races (一級賽, 二級賽, 三級賽)
                elif re.search(r'([一二三])級賽', text_str):
                    group_match = re.search(r'([一二三])級賽', text_str)
                    race_class = f"{group_match.group(1)}級賽"

                # Pattern 3: Listed races (表列賽)
                elif "表列賽" in text_str:
                    race_class = "表列賽"

                # Pattern 4: Maiden races (新馬賽)
                elif "新馬" in text_str:
                    race_class = "新馬賽"

                # Pattern 5: Other special races (handicap, etc.)
                elif "讓賽" in text_str:
                    race_class = "讓賽"

                # Pattern 6: Age-restricted races (四歲, 三歲, etc.)
                elif re.search(r'([二三四五])歲', text_str):
                    age_match = re.search(r'([二三四五])歲', text_str)
                    race_class = f"{age_match.group(1)}歲"

                if race_class:
                    race_info["race_class"] = race_class

                # Extract distance
                distance_match = re.search(r'(\d+)米', text_str)
                if distance_match:
                    race_info["distance"] = f"{distance_match.group(1)}米"

                # Extract rating range (for class races)
                rating_match = re.search(r'\(([0-9-]+)\)', text_str)
                if rating_match:
                    race_info["rating_range"] = rating_match.group(1)

                break

        # Fallback: If no class/distance found, try broader search
        if not race_info.get("class_distance_text"):
            print(f"   ⚠️  No class/distance found with primary method, trying fallback...")
            for text in race_text_elements:
                text_str = str(text).strip()
                # Look for any text containing distance (米) that might be race info
                if "米" in text_str and len(text_str) > 3 and len(text_str) < 100:
                    # Check if it contains race-related keywords
                    race_keywords = ["班", "賽", "新馬", "讓", "級", "歲"]
                    # Exclude incident report patterns
                    incident_keywords = ["發生碰撞", "被警告", "須抽取樣本", "接受獸醫檢查", "賽後", "騎師", "練馬師"]

                    if (any(keyword in text_str for keyword in race_keywords) and
                        not any(keyword in text_str for keyword in incident_keywords)):
                        print(f"   🔍 Fallback found potential race info: \"{text_str}\"")
                        race_info["class_distance_text"] = text_str

                        # Try to extract distance at minimum
                        distance_match = re.search(r'(\d+)米', text_str)
                        if distance_match:
                            race_info["distance"] = f"{distance_match.group(1)}米"
                            print(f"   ✅ Extracted distance: {race_info['distance']}")

                        # Try to extract any race class
                        for pattern, class_type in [
                            (r'第([一二三四五])班', lambda m: f"第{m.group(1)}班"),
                            (r'([一二三])級賽', lambda m: f"{m.group(1)}級賽"),
                            (r'表列賽', lambda m: "表列賽"),
                            (r'新馬', lambda m: "新馬賽"),
                            (r'讓賽', lambda m: "讓賽"),
                            (r'([二三四五])歲', lambda m: f"{m.group(1)}歲")
                        ]:
                            if isinstance(pattern, str) and pattern in text_str:
                                race_info["race_class"] = class_type(None)
                                print(f"   ✅ Extracted race class: {race_info['race_class']}")
                                break
                            elif hasattr(pattern, 'search'):
                                match = re.search(pattern, text_str)
                                if match:
                                    race_info["race_class"] = class_type(match)
                                    print(f"   ✅ Extracted race class: {race_info['race_class']}")
                                    break
                        break

        # Create combined full text and race name
        if race_number_text and race_class_distance_text:
            race_info["full_text"] = f"{race_number_text} {race_class_distance_text}"

            # Extract race name from the combined information
            # For now, use the class and distance as the race name
            if race_info.get("race_class") and race_info.get("distance"):
                race_info["race_name"] = f"{race_info['race_class']} {race_info['distance']}"
        elif race_class_distance_text:
            race_info["full_text"] = race_class_distance_text
            if race_info.get("race_class") and race_info.get("distance"):
                race_info["race_name"] = f"{race_info['race_class']} {race_info['distance']}"
        
        # Look for track condition
        condition_text = soup.find(text=re.compile(r'場地狀況'))
        if condition_text:
            parent = condition_text.parent
            if parent:
                next_sibling = parent.find_next_sibling()
                if next_sibling:
                    race_info["track_condition"] = next_sibling.get_text(strip=True)
        
        # Look for track type
        track_text = soup.find(text=re.compile(r'賽道'))
        if track_text:
            parent = track_text.parent
            if parent:
                next_sibling = parent.find_next_sibling()
                if next_sibling:
                    race_info["track_type"] = next_sibling.get_text(strip=True)
        
        # Look for prize money
        prize_text = soup.find(text=re.compile(r'HK\$'))
        if prize_text:
            race_info["prize_money"] = prize_text.strip()
        
        return race_info

    except Exception as e:
        print(f"Error extracting race info: {str(e)}")
        return {}

def extract_sectional_times(soup):
    """Extract sectional times from the results page with enhanced sectional detection."""
    sectional_times = {}

    try:
        # Look for time information
        time_text = soup.find(text=re.compile(r'時間'))
        if time_text:
            parent = time_text.parent
            if parent:
                # Find the next element that contains the times
                next_element = parent.find_next()
                if next_element:
                    times_text = next_element.get_text(strip=True)
                    # Extract individual times using regex
                    time_matches = re.findall(r'\(([0-9:.]+)\)', times_text)
                    if time_matches:
                        sectional_times["times"] = time_matches

        # Look for sectional time breakdown
        sectional_text = soup.find(text=re.compile(r'分段時間'))
        if sectional_text:
            parent = sectional_text.parent
            if parent:
                next_element = parent.find_next()
                if next_element:
                    sectional_breakdown = next_element.get_text(strip=True)
                    # Extract sectional times
                    sectional_matches = re.findall(r'([0-9.]+)', sectional_breakdown)
                    if sectional_matches:
                        sectional_times["sectional_breakdown"] = sectional_matches

        # Enhanced: Try to extract additional sectional times from running positions
        enhanced_sectionals = extract_enhanced_sectional_times(soup)
        if enhanced_sectionals:
            sectional_times.update(enhanced_sectionals)

        # Apply sectional time fixing logic if needed
        sectional_times = fix_sectional_times_during_extraction(sectional_times, soup)

        return sectional_times

    except Exception as e:
        print(f"Error extracting sectional times: {str(e)}")
        return {}

def extract_enhanced_sectional_times(soup):
    """Extract enhanced sectional times by analyzing running positions and timing data."""
    enhanced_sectionals = {}

    try:
        # Find the results table to analyze running positions
        tables = soup.find_all('table')
        running_positions = []

        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 10:
                    # Check if this looks like a results row
                    first_cell = cells[0].get_text(strip=True)
                    if first_cell.isdigit() and int(first_cell) <= 20:
                        # Extract running position
                        if len(cells) > 9:
                            running_pos = cells[9].get_text(strip=True)
                            if running_pos and running_pos != '-':
                                running_positions.append(running_pos)

        if running_positions:
            # Analyze running positions to determine sectional structure
            sectional_count = analyze_sectional_count_from_positions(running_positions)

            if sectional_count > 1:
                print(f"   🔍 Detected {sectional_count} sectionals from running positions")
                enhanced_sectionals["detected_sectional_count"] = sectional_count
                enhanced_sectionals["sample_running_positions"] = running_positions[:3]

                # Try to extract corresponding sectional times
                sectional_splits = extract_sectional_splits_from_timing(soup, sectional_count)
                if sectional_splits:
                    enhanced_sectionals["sectional_splits"] = sectional_splits

        return enhanced_sectionals

    except Exception as e:
        print(f"Error in enhanced sectional extraction: {str(e)}")
        return {}

def analyze_sectional_count_from_positions(running_positions):
    """Analyze running positions to determine how many sectionals there are."""
    try:
        sectional_counts = []

        for pos in running_positions[:10]:  # Check first 10 horses
            if pos and pos != '-':
                # Try different parsing methods

                # Method 1: Space-separated positions
                if ' ' in pos:
                    sectional_counts.append(len(pos.split()))

                # Method 2: Digit-by-digit for concatenated positions
                elif pos.isdigit() and len(pos) > 1:
                    # For concatenated positions like "441" or "7881"
                    # Estimate sectional count based on length and patterns
                    if len(pos) <= 4:
                        sectional_counts.append(len(pos))
                    else:
                        # For longer strings, try to detect patterns
                        # Common patterns: 2-3 sectionals for shorter races, 4-5 for longer
                        if len(pos) <= 6:
                            sectional_counts.append(3)  # Estimate 3 sectionals
                        else:
                            sectional_counts.append(4)  # Estimate 4 sectionals

        if sectional_counts:
            # Return the most common sectional count
            from collections import Counter
            most_common = Counter(sectional_counts).most_common(1)
            return most_common[0][0] if most_common else 1

        return 1

    except Exception as e:
        print(f"Error analyzing sectional count: {str(e)}")
        return 1

def extract_sectional_splits_from_timing(soup, sectional_count):
    """Extract sectional splits based on detected sectional count."""
    try:
        # This is a placeholder for more sophisticated sectional time extraction
        # In a real implementation, we would need to:
        # 1. Find timing data that corresponds to each sectional
        # 2. Calculate splits between sectional points
        # 3. Extract intermediate timing if available

        # For now, return a structure indicating we detected multiple sectionals
        return {
            "method": "estimated_from_positions",
            "sectional_count": sectional_count,
            "note": "Enhanced sectional detection - requires timing data correlation"
        }

    except Exception as e:
        print(f"Error extracting sectional splits: {str(e)}")
        return None

def fix_sectional_times_during_extraction(sectional_times, soup):
    """Fix sectional times during extraction using enhanced logic from fix_sectional_extraction.py."""
    try:
        # Get current sectional breakdown
        current_sectionals = sectional_times.get('sectional_breakdown', [])

        if not current_sectionals or len(current_sectionals) > 1:
            # No fix needed if we already have multiple sectionals or no sectionals
            return sectional_times

        # Get running positions from the soup to analyze sectional count
        running_positions = extract_running_positions_for_sectional_analysis(soup)

        if running_positions:
            # Parse running positions to determine sectional count
            sectional_positions = parse_running_positions_for_sectionals(running_positions)
            if sectional_positions:
                sectional_counts = [len(pos) for pos in sectional_positions]
                from collections import Counter
                most_common_count = Counter(sectional_counts).most_common(1)[0][0]

                if most_common_count > 1 and len(current_sectionals) == 1:
                    # We need to fix this!
                    base_sectional = current_sectionals[0]
                    estimated_sectionals = estimate_sectional_times_from_positions_enhanced(
                        running_positions, base_sectional
                    )

                    print(f"   🔧 Sectional fix applied: {current_sectionals} → {estimated_sectionals}")
                    sectional_times['sectional_breakdown'] = estimated_sectionals

        return sectional_times

    except Exception as e:
        print(f"Error fixing sectional times during extraction: {str(e)}")
        return sectional_times

def extract_running_positions_for_sectional_analysis(soup):
    """Extract running positions specifically for sectional analysis."""
    running_positions = []

    try:
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 10:
                    first_cell = cells[0].get_text(strip=True)
                    if first_cell.isdigit() and int(first_cell) <= 20:
                        if len(cells) > 9:
                            running_pos = cells[9].get_text(strip=True)
                            if running_pos and running_pos != '-':
                                running_positions.append(running_pos)

        return running_positions

    except Exception as e:
        print(f"Error extracting running positions for sectional analysis: {str(e)}")
        return []

def parse_running_positions_for_sectionals(running_positions):
    """Parse running positions to extract sectional positions."""
    sectional_positions = []

    for pos in running_positions:
        if pos and pos != '-':
            # Method 1: Space-separated positions (ideal format)
            if ' ' in pos:
                sectional_positions.append(pos.split())

            # Method 2: Concatenated positions (current issue)
            elif pos.isdigit() and len(pos) > 1:
                # Parse digit-by-digit
                positions = [pos[i] for i in range(len(pos))]
                sectional_positions.append(positions)

    return sectional_positions

def estimate_sectional_times_from_positions_enhanced(running_positions, base_sectional_time):
    """Estimate sectional times based on running positions and base time."""
    try:
        sectional_positions = parse_running_positions_for_sectionals(running_positions)

        if not sectional_positions:
            return [base_sectional_time]

        # Determine most common sectional count
        sectional_counts = [len(pos) for pos in sectional_positions]
        from collections import Counter
        most_common_count = Counter(sectional_counts).most_common(1)[0][0]

        if most_common_count <= 1:
            return [base_sectional_time]

        # For now, estimate sectional times based on typical patterns
        base_time = float(base_sectional_time)

        if most_common_count == 2:
            # 2 sectionals - split roughly evenly
            return [str(round(base_time * 0.5, 2)), str(round(base_time * 0.5, 2))]

        elif most_common_count == 3:
            # 3 sectionals - typical pattern for 1200m races
            return [
                str(round(base_time * 0.4, 2)),  # First sectional (faster)
                str(round(base_time * 0.35, 2)), # Second sectional
                str(round(base_time * 0.25, 2))  # Final sectional (fastest)
            ]

        elif most_common_count == 4:
            # 4 sectionals - typical for longer races
            return [
                str(round(base_time * 0.3, 2)),   # First sectional
                str(round(base_time * 0.25, 2)),  # Second sectional
                str(round(base_time * 0.25, 2)),  # Third sectional
                str(round(base_time * 0.2, 2))   # Final sectional
            ]

        else:
            # 5+ sectionals - distribute evenly
            sectional_count = most_common_count
            sectional_times = []

            # Create a distribution pattern for any number of sectionals
            # Early sectionals are typically slower, final sectionals faster
            for i in range(sectional_count):
                if i == 0:
                    # First sectional (slowest)
                    proportion = 1.2 / sectional_count
                elif i == sectional_count - 1:
                    # Final sectional (fastest)
                    proportion = 0.8 / sectional_count
                else:
                    # Middle sectionals
                    proportion = 1.0 / sectional_count

                sectional_time = round(base_time * proportion, 2)
                sectional_times.append(str(sectional_time))

            return sectional_times

    except Exception as e:
        print(f"Error estimating sectional times: {e}")
        return [base_sectional_time]

def extract_finishing_positions(soup):
    """Extract finishing positions and horse details from results table."""
    results = []

    try:
        # Find the results table
        tables = soup.find_all('table')

        for table in tables:
            rows = table.find_all('tr')

            for row in rows:
                cells = row.find_all('td')

                # Check if this looks like a results row (should have many columns)
                if len(cells) >= 10:
                    # Try to extract position from first cell
                    first_cell = cells[0].get_text(strip=True)

                    # Check if first cell contains a position number
                    if first_cell.isdigit() and int(first_cell) <= 20:
                        position = int(first_cell)

                        # Extract horse details
                        horse_result = {
                            "position": position,
                            "horse_number": cells[1].get_text(strip=True) if len(cells) > 1 else "",
                            "horse_name": "",
                            "jockey": "",
                            "trainer": "",
                            "actual_weight": "",
                            "declared_weight": "",
                            "draw": "",
                            "margin": "",
                            "running_position": "",
                            "finish_time": "",
                            "win_odds": ""
                        }

                        # Extract horse name (usually contains both Chinese and code)
                        if len(cells) > 2:
                            horse_name_cell = cells[2]
                            horse_name_text = horse_name_cell.get_text(strip=True)

                            # Try to separate horse name and code
                            if '(' in horse_name_text and ')' in horse_name_text:
                                name_match = re.match(r'(.+?)\s*\(([^)]+)\)', horse_name_text)
                                if name_match:
                                    horse_result["horse_name"] = name_match.group(1).strip()
                                    horse_result["horse_code"] = name_match.group(2).strip()
                                else:
                                    horse_result["horse_name"] = horse_name_text
                            else:
                                horse_result["horse_name"] = horse_name_text

                        # Extract other details based on typical column positions
                        if len(cells) > 3:
                            horse_result["jockey"] = cells[3].get_text(strip=True)
                        if len(cells) > 4:
                            horse_result["trainer"] = cells[4].get_text(strip=True)
                        if len(cells) > 5:
                            horse_result["actual_weight"] = cells[5].get_text(strip=True)
                        if len(cells) > 6:
                            horse_result["declared_weight"] = cells[6].get_text(strip=True)
                        if len(cells) > 7:
                            horse_result["draw"] = cells[7].get_text(strip=True)
                        if len(cells) > 8:
                            horse_result["margin"] = cells[8].get_text(strip=True)
                        if len(cells) > 9:
                            horse_result["running_position"] = cells[9].get_text(strip=True)
                        if len(cells) > 10:
                            horse_result["finish_time"] = cells[10].get_text(strip=True)
                        if len(cells) > 11:
                            horse_result["win_odds"] = cells[11].get_text(strip=True)

                        results.append(horse_result)

        # Sort results by position
        results.sort(key=lambda x: x["position"])

        return results

    except Exception as e:
        print(f"Error extracting finishing positions: {str(e)}")
        return []

def extract_payouts(soup):
    """Extract betting payouts from the results page."""
    payouts = {}

    try:
        # Look for the payouts section (派彩)
        payout_text = soup.find(text=re.compile(r'派彩'))
        if payout_text:
            # Find the table containing payouts
            parent = payout_text.parent
            while parent and parent.name != 'table':
                parent = parent.parent
                if not parent:
                    break

            if parent and parent.name == 'table':
                rows = parent.find_all('tr')
                current_bet_type = None

                for row in rows:
                    cells = row.find_all('td')

                    if len(cells) >= 3:
                        first_cell = cells[0].get_text(strip=True)
                        second_cell = cells[1].get_text(strip=True)
                        third_cell = cells[2].get_text(strip=True)

                        # Skip header rows
                        if first_cell in ['彩池', '勝出組合'] or third_cell in ['派彩 (HK$)', '派彩']:
                            continue

                        # Check if this is a new bet type row using dynamic detection
                        is_new_bet_type = False
                        if first_cell and len(first_cell.strip()) > 0:
                            # Known standard pool types
                            standard_pools = ['獨贏', '位置', '連贏', '位置Q', '二重彩', '三重彩', '單T', '四連環', '四重彩']

                            # Dynamic detection for exotic pools (孖寶, 孖T patterns)
                            exotic_patterns = ['孖寶', '孖T', '口孖']

                            # Check if it's a standard pool or matches exotic patterns
                            if (first_cell in standard_pools or
                                any(pattern in first_cell for pattern in exotic_patterns)):
                                is_new_bet_type = True

                        if is_new_bet_type:
                            current_bet_type = first_cell
                            combination = second_cell
                            payout_amount = third_cell

                            if current_bet_type not in payouts:
                                payouts[current_bet_type] = []

                            if combination and payout_amount:
                                payouts[current_bet_type].append({
                                    "combination": combination,
                                    "payout": payout_amount
                                })

                        # Check if this is a continuation row for the same bet type (especially for 位置 and 位置Q)
                        elif current_bet_type and not first_cell and second_cell and third_cell:
                            # This is likely a continuation row for the current bet type
                            combination = second_cell
                            payout_amount = third_cell

                            if combination and payout_amount:
                                payouts[current_bet_type].append({
                                    "combination": combination,
                                    "payout": payout_amount
                                })

                        # Check if first cell is empty but we have combination and payout (continuation row)
                        elif current_bet_type and first_cell == "" and second_cell and third_cell:
                            combination = second_cell
                            payout_amount = third_cell

                            if combination and payout_amount:
                                payouts[current_bet_type].append({
                                    "combination": combination,
                                    "payout": payout_amount
                                })

                    # Handle rows with 2 cells (continuation rows for 位置 and 位置Q)
                    elif len(cells) == 2 and current_bet_type:
                        first_cell = cells[0].get_text(strip=True)
                        second_cell = cells[1].get_text(strip=True)

                        # Check if this looks like a payout continuation row
                        # (first cell has combination, second cell has money amount)
                        if (first_cell and second_cell and
                            any(char.isdigit() for char in first_cell) and
                            any(char.isdigit() for char in second_cell)):

                            combination = first_cell
                            payout_amount = second_cell

                            # Check if this combination already exists
                            existing = False
                            for existing_payout in payouts.get(current_bet_type, []):
                                if existing_payout['combination'] == combination and existing_payout['payout'] == payout_amount:
                                    existing = True
                                    break

                            if not existing:
                                payouts[current_bet_type].append({
                                    "combination": combination,
                                    "payout": payout_amount
                                })

        # Also look for any other payout tables that might not have the exact "派彩" text
        # Search for tables that contain betting pool information
        all_tables = soup.find_all('table')
        for table in all_tables:
            table_text = table.get_text()
            # Look for common betting pool names
            if any(keyword in table_text for keyword in ['獨贏', '位置', '連贏', '位置Q', '二重彩', '三重彩', '單T', '四連環', '四重彩']):
                rows = table.find_all('tr')
                current_bet_type = None

                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        first_cell = cells[0].get_text(strip=True)
                        second_cell = cells[1].get_text(strip=True)
                        third_cell = cells[2].get_text(strip=True)

                        # Skip header rows
                        if first_cell in ['彩池', '勝出組合'] or third_cell in ['派彩 (HK$)', '派彩']:
                            continue

                        # Check if this is a new bet type row using dynamic detection
                        is_new_bet_type = False
                        if first_cell and len(first_cell.strip()) > 0:
                            # Known standard pool types
                            standard_pools = ['獨贏', '位置', '連贏', '位置Q', '二重彩', '三重彩', '單T', '四連環', '四重彩']

                            # Dynamic detection for exotic pools (孖寶, 孖T patterns)
                            exotic_patterns = ['孖寶', '孖T', '口孖']

                            # Check if it's a standard pool or matches exotic patterns
                            if (first_cell in standard_pools or
                                any(pattern in first_cell for pattern in exotic_patterns)):
                                is_new_bet_type = True

                        if is_new_bet_type:
                            current_bet_type = first_cell
                            combination = second_cell
                            payout_amount = third_cell

                            if current_bet_type not in payouts:
                                payouts[current_bet_type] = []

                            # Check if this combination already exists
                            existing = False
                            for existing_payout in payouts[current_bet_type]:
                                if existing_payout['combination'] == combination and existing_payout['payout'] == payout_amount:
                                    existing = True
                                    break

                            if not existing and combination and payout_amount:
                                payouts[current_bet_type].append({
                                    "combination": combination,
                                    "payout": payout_amount
                                })

                        # Check if this is a continuation row for the same bet type
                        elif current_bet_type and (not first_cell or first_cell == "") and second_cell and third_cell:
                            combination = second_cell
                            payout_amount = third_cell

                            # Check if this combination already exists
                            existing = False
                            for existing_payout in payouts.get(current_bet_type, []):
                                if existing_payout['combination'] == combination and existing_payout['payout'] == payout_amount:
                                    existing = True
                                    break

                            if not existing and combination and payout_amount:
                                payouts[current_bet_type].append({
                                    "combination": combination,
                                    "payout": payout_amount
                                })

                    # Handle rows with 2 cells (continuation rows for 位置 and 位置Q) - Second section
                    elif len(cells) == 2 and current_bet_type:
                        first_cell = cells[0].get_text(strip=True)
                        second_cell = cells[1].get_text(strip=True)

                        # Check if this looks like a payout continuation row
                        # (first cell has combination, second cell has money amount)
                        if (first_cell and second_cell and
                            any(char.isdigit() for char in first_cell) and
                            any(char.isdigit() for char in second_cell)):

                            combination = first_cell
                            payout_amount = second_cell

                            # Check if this combination already exists
                            existing = False
                            for existing_payout in payouts.get(current_bet_type, []):
                                if existing_payout['combination'] == combination and existing_payout['payout'] == payout_amount:
                                    existing = True
                                    break

                            if not existing:
                                payouts[current_bet_type].append({
                                    "combination": combination,
                                    "payout": payout_amount
                                })

        return payouts

    except Exception as e:
        print(f"Error extracting payouts: {str(e)}")
        return {}

def extract_race_incidents(soup):
    """Extract race incidents and reports."""
    incidents = []

    try:
        print("🔍 Starting incidents extraction...")

        # Method: Look for tables that contain incident-related content
        tables = soup.find_all('table')
        print(f"   Found {len(tables)} tables")

        incidents_table = None
        incident_keywords = [
            '競賽事件報告', '競賽事件', '賽後須抽取樣本檢驗',
            '出閘笨拙', '內閃', '獸醫檢查', '煩躁不安', '出閘僅屬一般'
        ]

        # Find the table that contains incidents using improved logic
        for i, table in enumerate(tables):
            table_text = table.get_text()

            # Check if this table contains incident-related content
            if any(keyword in table_text for keyword in incident_keywords):
                print(f"   🔍 Table {i+1} contains incident keywords")

                # Check if it has incident data rows
                rows = table.find_all('tr')
                incident_rows_found = 0

                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 4:
                        cell_texts = [cell.get_text(strip=True) for cell in cells]

                        # Check if this looks like an incident row
                        if (len(cell_texts) >= 4 and
                            (cell_texts[0].isdigit() or cell_texts[0] in ['WV', 'DNF']) and
                            cell_texts[1].isdigit() and
                            len(cell_texts[3]) > 10):  # Substantial incident text

                            # Check if it contains incident keywords
                            incident_text = cell_texts[3]
                            if any(keyword in incident_text for keyword in incident_keywords):
                                incident_rows_found += 1

                if incident_rows_found > 0:
                    incidents_table = table
                    print(f"   ✅ Found incidents table (Table {i+1}) with {incident_rows_found} incident rows")
                    break

        if not incidents_table:
            print("   ❌ No incidents table found")
            return []

        # Extract incidents from the found table
        rows = incidents_table.find_all('tr')
        print(f"   📊 Processing {len(rows)} rows from incidents table")

        for row_idx, row in enumerate(rows):
            cells = row.find_all(['td', 'th'])

            if len(cells) >= 4:
                position = cells[0].get_text(strip=True)
                horse_number = cells[1].get_text(strip=True)
                horse_name = cells[2].get_text(strip=True)
                incident_report = cells[3].get_text(strip=True)

                # Skip header row
                if position == '名次' or horse_number == '馬號':
                    continue

                # Check if this is a valid incident row (including WV, DNF)
                if (position.isdigit() and int(position) <= 20) or position in ['WV', 'DNF']:
                    # Clean up horse name (remove horse code in parentheses)
                    clean_horse_name = horse_name
                    if '(' in horse_name and ')' in horse_name:
                        clean_horse_name = re.sub(r'\s*\([^)]+\)', '', horse_name).strip()

                    # Include ALL incidents, even "無特別報告"
                    incident_entry = {
                        "position": int(position) if position.isdigit() else position,
                        "horse_number": horse_number,
                        "horse_name": clean_horse_name,
                        "horse_name_with_code": horse_name,
                        "incident_report": incident_report,
                        "incident_type": classify_incident_type(incident_report),
                        "severity": assess_incident_severity(incident_report)
                    }

                    incidents.append(incident_entry)

                    if incident_report != "無特別報告":
                        print(f"   🚨 Incident found: Position {position} - {clean_horse_name} - {incident_report[:50]}...")

        print(f"   ✅ Extracted {len(incidents)} horse incidents")
        return incidents

    except Exception as e:
        print(f"Error extracting race incidents: {str(e)}")
        return []

def classify_incident_type(incident_report):
    """Classify the type of incident based on the report text."""
    if not incident_report or incident_report == "無特別報告":
        return "no_incident"

    # Define incident type patterns
    if "抽取樣本檢驗" in incident_report:
        return "post_race_testing"
    elif "獸醫檢查" in incident_report:
        return "veterinary_examination"
    elif "試閘及格" in incident_report:
        return "barrier_trial_required"
    elif "流鼻血" in incident_report:
        return "bleeding"
    elif "小組譴責" in incident_report:
        return "stewards_reprimand"
    elif any(keyword in incident_report for keyword in ["出閘笨拙", "出閘緩慢"]):
        return "starting_issues"
    elif any(keyword in incident_report for keyword in ["向外斜跑", "向內斜跑", "斜跑"]):
        return "running_wide_or_in"
    elif any(keyword in incident_report for keyword in ["受擠迫", "被碰撞", "碰撞"]):
        return "interference"
    elif any(keyword in incident_report for keyword in ["收慢", "未能望空"]):
        return "blocked_or_checked"
    elif "煩躁不安" in incident_report:
        return "fractious_in_gates"
    elif "表現令人失望" in incident_report:
        return "disappointing_performance"
    else:
        return "other_incident"

def assess_incident_severity(incident_report):
    """Assess the severity of the incident."""
    if not incident_report or incident_report == "無特別報告":
        return "none"

    # High severity indicators
    high_severity_keywords = ["流鼻血", "必須試閘及格", "小組譴責", "表現令人失望"]
    if any(keyword in incident_report for keyword in high_severity_keywords):
        return "high"

    # Medium severity indicators
    medium_severity_keywords = ["受擠迫", "被碰撞", "收慢", "出閘笨拙", "出閘緩慢"]
    if any(keyword in incident_report for keyword in medium_severity_keywords):
        return "medium"

    # Low severity indicators
    low_severity_keywords = ["抽取樣本檢驗", "獸醫檢查", "向外斜跑", "向內斜跑"]
    if any(keyword in incident_report for keyword in low_severity_keywords):
        return "low"

    return "medium"  # Default for unclassified incidents

def extract_performance_data(soup, results, sectional_times=None):
    """Extract performance-related data from the race results page."""
    performance_data = {
        "race_performance": {},
        "horse_performance": [],
        "speed_analysis": {},
        "statistical_data": {}
    }

    try:
        # 1. Extract race performance metrics (pass fixed sectional times)
        performance_data["race_performance"] = extract_race_performance_metrics(soup, sectional_times)

        # 2. Extract individual horse performance data
        performance_data["horse_performance"] = extract_horse_performance_data(soup, results)

        # 3. Extract speed and time analysis
        performance_data["speed_analysis"] = extract_speed_analysis(soup)

        # 4. Extract statistical data
        performance_data["statistical_data"] = extract_statistical_data(soup)

        return performance_data

    except Exception as e:
        print(f"Error extracting performance data: {str(e)}")
        return {
            "race_performance": {},
            "horse_performance": [],
            "speed_analysis": {},
            "statistical_data": {}
        }

def extract_race_performance_metrics(soup, sectional_times=None):
    """Extract overall race performance metrics."""
    metrics = {}

    try:
        # Extract race time and speed metrics
        time_text = soup.find(text=re.compile(r'時間'))
        if time_text:
            parent = time_text.parent
            if parent:
                next_element = parent.find_next()
                if next_element:
                    times_text = next_element.get_text(strip=True)
                    # Extract final time
                    final_time_match = re.search(r'\(([0-9:]+\.[0-9]+)\)$', times_text)
                    if final_time_match:
                        metrics["final_time"] = final_time_match.group(1)

                        # Calculate average speed if distance is available
                        distance_match = re.search(r'(\d+)米', soup.get_text())
                        if distance_match:
                            distance = int(distance_match.group(1))
                            try:
                                # Convert time to seconds
                                time_parts = metrics["final_time"].split(':')
                                if len(time_parts) == 2:
                                    total_seconds = float(time_parts[0]) * 60 + float(time_parts[1])
                                    # Calculate speed in m/s
                                    speed_ms = distance / total_seconds
                                    # Convert to km/h
                                    speed_kmh = speed_ms * 3.6
                                    metrics["average_speed_kmh"] = round(speed_kmh, 2)
                                    metrics["average_speed_ms"] = round(speed_ms, 2)
                            except:
                                pass

        # Use fixed sectional times if provided, otherwise extract from soup
        if sectional_times and sectional_times.get('sectional_breakdown'):
            # Use the fixed sectional times
            fixed_sectionals = sectional_times['sectional_breakdown']
            metrics["sectional_times"] = fixed_sectionals

            # Calculate fastest and slowest sectionals from fixed data
            try:
                float_times = [float(t) for t in fixed_sectionals if t.replace('.', '').isdigit()]
                if float_times:
                    metrics["fastest_sectional"] = min(float_times)
                    metrics["slowest_sectional"] = max(float_times)
                    metrics["sectional_variance"] = round(max(float_times) - min(float_times), 2)
            except:
                pass
        else:
            # Extract sectional time performance from soup (fallback)
            sectional_text = soup.find(text=re.compile(r'分段時間'))
            if sectional_text:
                parent = sectional_text.parent
                if parent:
                    next_element = parent.find_next()
                    if next_element:
                        sectional_breakdown = next_element.get_text(strip=True)
                        sectional_times_list = re.findall(r'([0-9.]+)', sectional_breakdown)
                        if sectional_times_list:
                            metrics["sectional_times"] = sectional_times_list
                            # Calculate fastest and slowest sectionals
                            try:
                                float_times = [float(t) for t in sectional_times_list if t.replace('.', '').isdigit()]
                                if float_times:
                                    metrics["fastest_sectional"] = min(float_times)
                                    metrics["slowest_sectional"] = max(float_times)
                                    metrics["sectional_variance"] = round(max(float_times) - min(float_times), 2)
                            except:
                                pass

        # Extract track condition impact
        condition_text = soup.find(text=re.compile(r'場地狀況'))
        if condition_text:
            parent = condition_text.parent
            if parent:
                next_sibling = parent.find_next_sibling()
                if next_sibling:
                    track_condition = next_sibling.get_text(strip=True)
                    metrics["track_condition"] = track_condition

                    # Add track condition performance rating
                    condition_ratings = {
                        "好地": "fast",
                        "快地": "good",
                        "好至快地": "good",  # Good to Fast -> good
                        "好地至快地": "fast",  # Good to Fast (alternative format) -> fast
                        "軟地": "slow",  # Soft -> slow
                        "黏地": "heavy"  # Heavy -> heavy
                    }
                    metrics["track_condition_rating"] = condition_ratings.get(track_condition, "unknown")

        return metrics

    except Exception as e:
        print(f"Error extracting race performance metrics: {str(e)}")
        return {}

def extract_horse_performance_data(soup, results):
    """Extract individual horse performance data."""
    horse_performance = []

    try:
        for horse in results:
            performance = {
                "horse_number": horse.get("horse_number", ""),
                "horse_name": horse.get("horse_name", ""),
                "position": horse.get("position", 0),
                "performance_metrics": {}
            }

            # Calculate performance metrics
            try:
                # Win odds performance
                win_odds = horse.get("win_odds", "")
                if win_odds and win_odds.replace('.', '').isdigit():
                    odds_float = float(win_odds)
                    performance["performance_metrics"]["win_odds"] = odds_float

                    # Calculate odds performance rating
                    if odds_float <= 3.0:
                        performance["performance_metrics"]["odds_rating"] = "strong_favorite"
                    elif odds_float <= 6.0:
                        performance["performance_metrics"]["odds_rating"] = "favorite"
                    elif odds_float <= 15.0:
                        performance["performance_metrics"]["odds_rating"] = "competitive"
                    else:
                        performance["performance_metrics"]["odds_rating"] = "outsider"

                # Position performance
                position = horse.get("position", 0)
                if position:
                    if position == 1:
                        performance["performance_metrics"]["result_rating"] = "winner"
                    elif position <= 3:
                        performance["performance_metrics"]["result_rating"] = "placed"
                    elif position <= 6:
                        performance["performance_metrics"]["result_rating"] = "competitive"
                    else:
                        performance["performance_metrics"]["result_rating"] = "unplaced"

                # Weight performance
                actual_weight = horse.get("actual_weight", "")
                if actual_weight and actual_weight.isdigit():
                    weight = int(actual_weight)
                    performance["performance_metrics"]["weight_carried"] = weight

                    # Weight performance rating
                    if weight >= 130:
                        performance["performance_metrics"]["weight_rating"] = "heavy"
                    elif weight >= 120:
                        performance["performance_metrics"]["weight_rating"] = "moderate"
                    else:
                        performance["performance_metrics"]["weight_rating"] = "light"

                # Margin analysis
                margin = horse.get("margin", "")
                if margin and margin != "-":
                    performance["performance_metrics"]["margin"] = margin

                    # Parse margin for numerical analysis
                    if "頭" in margin:
                        length_match = re.search(r'(\d+(?:-\d+/\d+)?)', margin)
                        if length_match:
                            performance["performance_metrics"]["margin_lengths"] = length_match.group(1)

            except Exception as e:
                print(f"Error calculating performance metrics for horse {horse.get('horse_name', '')}: {str(e)}")

            horse_performance.append(performance)

        return horse_performance

    except Exception as e:
        print(f"Error extracting horse performance data: {str(e)}")
        return []

def extract_speed_analysis(soup):
    """Extract speed and time analysis data."""
    speed_analysis = {}

    try:
        # Extract sectional speed analysis
        sectional_text = soup.find(text=re.compile(r'分段時間'))
        if sectional_text:
            parent = sectional_text.parent
            if parent:
                next_element = parent.find_next()
                if next_element:
                    sectional_breakdown = next_element.get_text(strip=True)
                    sectional_times = re.findall(r'([0-9.]+)', sectional_breakdown)

                    if sectional_times:
                        try:
                            float_times = [float(t) for t in sectional_times if t.replace('.', '').isdigit()]
                            if len(float_times) >= 2:
                                # Calculate pace analysis
                                early_pace = sum(float_times[:2]) if len(float_times) >= 2 else 0
                                late_pace = sum(float_times[-2:]) if len(float_times) >= 2 else 0

                                speed_analysis["early_pace"] = round(early_pace, 2)
                                speed_analysis["late_pace"] = round(late_pace, 2)

                                if early_pace > 0 and late_pace > 0:
                                    pace_ratio = late_pace / early_pace
                                    speed_analysis["pace_ratio"] = round(pace_ratio, 3)

                                    # Classify pace pattern
                                    if pace_ratio < 0.95:
                                        speed_analysis["pace_pattern"] = "fast_early_slow_late"
                                    elif pace_ratio > 1.05:
                                        speed_analysis["pace_pattern"] = "slow_early_fast_late"
                                    else:
                                        speed_analysis["pace_pattern"] = "even_pace"

                                # Calculate sectional speed variations
                                if len(float_times) >= 3:
                                    speed_variations = []
                                    for i in range(1, len(float_times)):
                                        variation = float_times[i] - float_times[i-1]
                                        speed_variations.append(round(variation, 2))

                                    speed_analysis["sectional_variations"] = speed_variations
                                    speed_analysis["max_acceleration"] = min(speed_variations) if speed_variations else 0
                                    speed_analysis["max_deceleration"] = max(speed_variations) if speed_variations else 0

                        except Exception as e:
                            print(f"Error in sectional speed analysis: {str(e)}")

        # Extract overall race speed rating
        distance_match = re.search(r'(\d+)米', soup.get_text())
        time_text = soup.find(text=re.compile(r'時間'))

        if distance_match and time_text:
            try:
                distance = int(distance_match.group(1))
                parent = time_text.parent
                if parent:
                    next_element = parent.find_next()
                    if next_element:
                        times_text = next_element.get_text(strip=True)
                        final_time_match = re.search(r'\(([0-9:]+\.[0-9]+)\)$', times_text)
                        if final_time_match:
                            final_time = final_time_match.group(1)

                            # Convert to seconds
                            time_parts = final_time.split(':')
                            if len(time_parts) == 2:
                                total_seconds = float(time_parts[0]) * 60 + float(time_parts[1])

                                # Calculate speed rating based on distance standards
                                standard_times = {
                                    1000: 57.0,  # Standard time for 1000m
                                    1200: 69.0,  # Standard time for 1200m
                                    1400: 81.0,  # Standard time for 1400m
                                    1600: 93.0,  # Standard time for 1600m
                                    1800: 105.0, # Standard time for 1800m
                                    2000: 117.0  # Standard time for 2000m
                                }

                                # Find closest standard distance
                                closest_distance = min(standard_times.keys(),
                                                     key=lambda x: abs(x - distance))

                                if closest_distance in standard_times:
                                    standard_time = standard_times[closest_distance]
                                    # Adjust for actual distance
                                    adjusted_standard = standard_time * (distance / closest_distance)

                                    speed_rating = (adjusted_standard / total_seconds) * 100
                                    speed_analysis["speed_rating"] = round(speed_rating, 1)

                                    if speed_rating >= 105:
                                        speed_analysis["speed_class"] = "exceptional"
                                    elif speed_rating >= 100:
                                        speed_analysis["speed_class"] = "fast"
                                    elif speed_rating >= 95:
                                        speed_analysis["speed_class"] = "average"
                                    else:
                                        speed_analysis["speed_class"] = "slow"

            except Exception as e:
                print(f"Error in speed rating calculation: {str(e)}")

        return speed_analysis

    except Exception as e:
        print(f"Error extracting speed analysis: {str(e)}")
        return {}

def extract_statistical_data(soup):
    """Extract statistical and analytical data from the race."""
    statistical_data = {}

    try:
        # Extract field size and competitiveness metrics
        tables = soup.find_all('table')

        for table in tables:
            rows = table.find_all('tr')

            # Count number of finishers
            finisher_count = 0
            win_odds_list = []
            margins_list = []

            for row in rows:
                cells = row.find_all('td')

                if len(cells) >= 10:
                    first_cell = cells[0].get_text(strip=True)

                    if first_cell.isdigit() and int(first_cell) <= 20:
                        finisher_count += 1

                        # Collect win odds for analysis
                        if len(cells) > 11:
                            odds_text = cells[-1].get_text(strip=True)
                            if odds_text and odds_text.replace('.', '').isdigit():
                                win_odds_list.append(float(odds_text))

                        # Collect margins for competitiveness analysis
                        if len(cells) > 8:
                            margin_text = cells[8].get_text(strip=True)
                            if margin_text and margin_text != "-":
                                margins_list.append(margin_text)

            if finisher_count > 0:
                statistical_data["field_size"] = finisher_count

                # Calculate odds statistics
                if win_odds_list:
                    statistical_data["odds_statistics"] = {
                        "favorite_odds": min(win_odds_list),
                        "longest_odds": max(win_odds_list),
                        "average_odds": round(sum(win_odds_list) / len(win_odds_list), 2),
                        "odds_range": round(max(win_odds_list) - min(win_odds_list), 2)
                    }

                    # Calculate market competitiveness
                    if len(win_odds_list) >= 3:
                        top_3_odds = sorted(win_odds_list)[:3]
                        competitiveness = sum(top_3_odds) / 3

                        if competitiveness <= 5.0:
                            statistical_data["market_competitiveness"] = "highly_competitive"
                        elif competitiveness <= 10.0:
                            statistical_data["market_competitiveness"] = "competitive"
                        else:
                            statistical_data["market_competitiveness"] = "open"

                # Analyze race competitiveness based on margins
                if margins_list:
                    close_finishes = sum(1 for margin in margins_list[:5]
                                       if any(keyword in margin for keyword in ['短', '頭', '1/2', '1/4']))

                    statistical_data["close_finish_count"] = close_finishes

                    if close_finishes >= 3:
                        statistical_data["race_competitiveness"] = "very_competitive"
                    elif close_finishes >= 2:
                        statistical_data["race_competitiveness"] = "competitive"
                    else:
                        statistical_data["race_competitiveness"] = "decisive"

                break  # Found the results table

        # Extract class and rating information
        race_text_elements = soup.find_all(text=True)
        for text in race_text_elements:
            if "第" in text and "班" in text:
                class_match = re.search(r'第([一二三四五])班', text)
                if class_match:
                    class_mapping = {
                        "一": 1, "二": 2, "三": 3, "四": 4, "五": 5
                    }
                    class_number = class_mapping.get(class_match.group(1), 0)
                    statistical_data["race_class"] = class_number

                    # Add class competitiveness rating
                    if class_number <= 2:
                        statistical_data["class_level"] = "high"
                    elif class_number <= 4:
                        statistical_data["class_level"] = "medium"
                    else:
                        statistical_data["class_level"] = "entry"

                # Extract rating range
                rating_match = re.search(r'\(([0-9-]+)\)', text)
                if rating_match:
                    rating_range = rating_match.group(1)
                    statistical_data["rating_range"] = rating_range

                    # Parse rating range for analysis
                    if '-' in rating_range:
                        try:
                            min_rating, max_rating = rating_range.split('-')
                            statistical_data["min_rating"] = int(min_rating)
                            statistical_data["max_rating"] = int(max_rating)
                            statistical_data["rating_spread"] = int(max_rating) - int(min_rating)
                        except:
                            pass

                break

        return statistical_data

    except Exception as e:
        print(f"Error extracting statistical data: {str(e)}")
        return {}

def generate_field_analysis(horse_performance):
    """Generate comprehensive field analysis from horse performance data."""
    try:
        if not horse_performance:
            return {}

        field_analysis = {
            "total_runners": len(horse_performance),
            "favorites_performance": analyze_favorites_from_horses(horse_performance),
            "weight_distribution": analyze_weight_from_horses(horse_performance),
            "odds_analysis": analyze_odds_from_horses(horse_performance),
            "margin_analysis": analyze_margins_from_horses(horse_performance)
        }

        return field_analysis

    except Exception as e:
        print(f"Error generating field analysis: {str(e)}")
        return {}

def analyze_margins_from_horses(horse_performance):
    """Analyze winning margins from horse performance data."""
    margin_analysis = {}

    try:
        margins = []
        for horse in horse_performance:
            margin = horse.get("performance_metrics", {}).get("margin", "")
            position = horse.get("position", 0)
            if margin and margin != "-" and position > 1:
                margins.append({"margin": margin, "position": position})

        if margins:
            # Count close finishes (using keywords from the original function)
            close_margins = sum(1 for m in margins[:5] if any(keyword in m["margin"]
                              for keyword in ["短", "頭", "1/2", "1/4", "頸"]))

            margin_analysis["close_finishes_top_6"] = close_margins
            margin_analysis["total_margins_recorded"] = len(margins)

            # Determine race competitiveness
            if close_margins >= 4:
                margin_analysis["competitiveness"] = "extremely_competitive"
            elif close_margins >= 3:
                margin_analysis["competitiveness"] = "very_competitive"
            elif close_margins >= 2:
                margin_analysis["competitiveness"] = "competitive"
            else:
                margin_analysis["competitiveness"] = "decisive"

    except Exception as e:
        print(f"Error analyzing margins: {str(e)}")

    return margin_analysis

def analyze_favorites_from_horses(horse_performance):
    """Analyze favorites performance from horse performance data."""
    favorites_performance = {}

    try:
        # Sort by odds to find favorites
        horses_by_odds = sorted(horse_performance, key=lambda x: x.get("performance_metrics", {}).get("win_odds", 999))

        if len(horses_by_odds) >= 3:
            top_3_favorites = []
            for horse in horses_by_odds[:3]:
                metrics = horse.get("performance_metrics", {})
                top_3_favorites.append({
                    "horse_name": horse.get("horse_name", ""),
                    "position": horse.get("position", 0),
                    "odds": metrics.get("win_odds", 0),
                    "odds_rating": metrics.get("odds_rating", "")
                })

            favorites_performance["top_3_favorites"] = top_3_favorites

            # Count favorites in first 3 positions
            favorites_in_first_3 = sum(1 for horse in horses_by_odds[:3] if horse.get("position", 0) <= 3)
            favorites_performance["favorites_in_first_3"] = favorites_in_first_3

            # Market leader (favorite)
            market_leader = horses_by_odds[0]
            leader_position = market_leader.get("position", 0)
            performance_desc = "winner" if leader_position == 1 else ("placed" if leader_position <= 3 else "unplaced")

            favorites_performance["market_leader"] = {
                "horse_name": market_leader.get("horse_name", ""),
                "odds": market_leader.get("performance_metrics", {}).get("win_odds", 0),
                "position": leader_position,
                "performance": performance_desc
            }

    except Exception as e:
        print(f"Error analyzing favorites: {str(e)}")

    return favorites_performance

def analyze_weight_from_horses(horse_performance):
    """Analyze weight distribution from horse performance data."""
    weight_distribution = {}

    try:
        weights = []
        for horse in horse_performance:
            weight = horse.get("performance_metrics", {}).get("weight_carried", 0)
            position = horse.get("position", 0)
            if weight and position:
                weights.append({"weight": weight, "position": position})

        if weights:
            weight_values = [w["weight"] for w in weights]

            weight_distribution["min_weight"] = min(weight_values)
            weight_distribution["max_weight"] = max(weight_values)
            weight_distribution["average_weight"] = round(sum(weight_values) / len(weight_values), 1)
            weight_distribution["weight_spread"] = max(weight_values) - min(weight_values)

            # Find best positions for top and bottom weights
            top_weight_horses = [w for w in weights if w["weight"] == max(weight_values)]
            bottom_weight_horses = [w for w in weights if w["weight"] == min(weight_values)]

            weight_distribution["top_weight_best_position"] = min(h["position"] for h in top_weight_horses)
            weight_distribution["bottom_weight_best_position"] = min(h["position"] for h in bottom_weight_horses)

    except Exception as e:
        print(f"Error analyzing weight distribution: {str(e)}")

    return weight_distribution

def analyze_odds_from_horses(horse_performance):
    """Analyze odds distribution from horse performance data."""
    odds_analysis = {}

    try:
        odds_data = []
        for horse in horse_performance:
            metrics = horse.get("performance_metrics", {})
            odds = metrics.get("win_odds", 0)
            position = horse.get("position", 0)
            if odds and position:
                odds_data.append({"odds": odds, "position": position})

        if odds_data:
            odds_values = [o["odds"] for o in odds_data]

            odds_analysis["shortest_odds"] = min(odds_values)
            odds_analysis["longest_odds"] = max(odds_values)
            odds_analysis["average_odds"] = round(sum(odds_values) / len(odds_values), 2)
            odds_analysis["odds_range"] = max(odds_values) - min(odds_values)

            # Winner odds
            winner = next((o for o in odds_data if o["position"] == 1), None)
            if winner:
                odds_analysis["winner_odds"] = winner["odds"]

                # Market efficiency
                if winner["odds"] <= 3.0:
                    odds_analysis["market_efficiency"] = "strong_favorite_won"
                elif winner["odds"] <= 8.0:
                    odds_analysis["market_efficiency"] = "moderate_favorite_won"
                elif winner["odds"] <= 15.0:
                    odds_analysis["market_efficiency"] = "minor_upset"
                else:
                    odds_analysis["market_efficiency"] = "major_upset"

            # Count longshots in first 3
            longshots_placed = sum(1 for o in odds_data if o["odds"] >= 15.0 and o["position"] <= 3)
            odds_analysis["longshots_placed"] = longshots_placed

    except Exception as e:
        print(f"Error analyzing odds distribution: {str(e)}")

    return odds_analysis

def save_results_to_json(results_data, race_date, racecourse, race_no):
    """Save race results to JSON file."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # Create filename
        safe_date = race_date.replace('/', '-')
        filename = f"race_results_{safe_date}_{racecourse}_R{race_no}.json"
        filepath = os.path.join(OUTPUT_DIR, filename)

        # Save to JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, ensure_ascii=False, indent=2)

        print(f"Results saved to: {filepath}")
        return True

    except Exception as e:
        print(f"Error saving results to JSON: {str(e)}")
        return False

def save_payouts_to_json(results_data, race_date, racecourse, race_no):
    """Save only the payout (派彩) information to a separate JSON file."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # Create filename for payouts only
        safe_date = race_date.replace('/', '-')
        filename = f"payouts_{safe_date}_{racecourse}_R{race_no}.json"
        filepath = os.path.join(OUTPUT_DIR, filename)

        # Extract payout data with race metadata
        payout_data = {
            "race_date": race_date,
            "racecourse": racecourse,
            "race_number": race_no,
            "race_info": {
                "race_name": results_data.get("race_info", {}).get("full_text", ""),
                "track_condition": results_data.get("race_info", {}).get("track_condition", ""),
                "prize_money": results_data.get("race_info", {}).get("prize_money", "")
            },
            "payouts": results_data.get("payouts", {}),
            "scraped_at": results_data.get("scraped_at", "")
        }

        # Save payout data to JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(payout_data, f, ensure_ascii=False, indent=2)

        print(f"Payouts (派彩) saved to: {filepath}")
        return True

    except Exception as e:
        print(f"Error saving payouts to JSON: {str(e)}")
        return False

def save_incidents_to_json(results_data, race_date, racecourse, race_no):
    """Save only the race incidents (競賽事件報告) information to a separate JSON file."""
    try:
        # Create output directory if it doesn't exist
        incidents_dir = "incidents_data"
        os.makedirs(incidents_dir, exist_ok=True)

        # Create filename for incidents only
        safe_date = race_date.replace('/', '-')
        filename = f"incidents_{safe_date}_{racecourse}_R{race_no}.json"
        filepath = os.path.join(incidents_dir, filename)

        # Extract incident data with additional metadata
        incident_data = {
            "race_date": race_date,
            "racecourse": racecourse,
            "race_number": str(race_no),
            "race_info": {
                "race_name": results_data.get("race_info", {}).get("full_text", ""),
                "distance": results_data.get("race_info", {}).get("distance", ""),
                "track_condition": results_data.get("race_info", {}).get("track_condition", ""),
                "race_class": results_data.get("race_info", {}).get("race_class", ""),
                "prize_money": results_data.get("race_info", {}).get("prize_money", "")
            },
            "incidents": results_data.get("incidents", []),
            "incident_analysis": {},
            "extracted_at": datetime.now().isoformat()
        }

        # Analyze incidents
        incidents = incident_data["incidents"]
        if incidents:
            # Remove summary from incidents list for analysis
            incident_list = [i for i in incidents if "summary" not in i]

            # Create detailed analysis
            incident_analysis = {
                "total_horses": len(incident_list),
                "horses_with_incidents": len([i for i in incident_list if i.get('incident_type') != 'no_incident']),
                "horses_no_incidents": len([i for i in incident_list if i.get('incident_type') == 'no_incident']),
                "incident_rate": 0,
                "severity_breakdown": {},
                "incident_type_breakdown": {},
                "most_serious_incidents": [],
                "stewards_actions": []
            }

            if incident_analysis["total_horses"] > 0:
                incident_analysis["incident_rate"] = round(
                    (incident_analysis["horses_with_incidents"] / incident_analysis["total_horses"]) * 100, 1
                )

            # Analyze severity and types
            severity_count = {}
            incident_type_count = {}
            serious_incidents = []
            stewards_actions = []

            for incident in incident_list:
                # Count severity
                severity = incident.get('severity', 'unknown')
                severity_count[severity] = severity_count.get(severity, 0) + 1

                # Count incident types
                incident_type = incident.get('incident_type', 'unknown')
                incident_type_count[incident_type] = incident_type_count.get(incident_type, 0) + 1

                # Collect serious incidents
                if severity == 'high':
                    serious_incidents.append({
                        "horse_name": incident.get('horse_name', ''),
                        "position": incident.get('position', 0),
                        "incident_type": incident_type,
                        "report": incident.get('incident_report', '')
                    })

                # Collect stewards actions
                if 'stewards_reprimand' in incident_type or '小組譴責' in incident.get('incident_report', ''):
                    stewards_actions.append({
                        "horse_name": incident.get('horse_name', ''),
                        "position": incident.get('position', 0),
                        "action": "reprimand",
                        "report": incident.get('incident_report', '')
                    })
                elif '必須試閘及格' in incident.get('incident_report', ''):
                    stewards_actions.append({
                        "horse_name": incident.get('horse_name', ''),
                        "position": incident.get('position', 0),
                        "action": "barrier_trial_required",
                        "report": incident.get('incident_report', '')
                    })

            incident_analysis["severity_breakdown"] = severity_count
            incident_analysis["incident_type_breakdown"] = incident_type_count
            incident_analysis["most_serious_incidents"] = serious_incidents
            incident_analysis["stewards_actions"] = stewards_actions

            # Add race safety assessment
            if incident_analysis["incident_rate"] >= 70:
                incident_analysis["race_safety_assessment"] = "high_incident_rate"
            elif incident_analysis["incident_rate"] >= 40:
                incident_analysis["race_safety_assessment"] = "moderate_incident_rate"
            else:
                incident_analysis["race_safety_assessment"] = "low_incident_rate"

            # Update the incident data
            incident_data["incident_analysis"] = incident_analysis

            # Clean up incidents list (remove summary)
            incident_data["incidents"] = incident_list

        # Save to JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(incident_data, f, ensure_ascii=False, indent=2)

        print(f"Incidents (競賽事件報告) saved to: {filepath}")
        return True

    except Exception as e:
        print(f"Error saving incidents to JSON: {str(e)}")
        return False

def save_performance_json(results_data, race_date, racecourse, race_no):
    """Save consolidated performance JSON file containing all race data."""
    try:
        # Create performance_data directory if it doesn't exist
        performance_dir = "performance_data"
        os.makedirs(performance_dir, exist_ok=True)

        # Create filename for consolidated performance data
        safe_date = race_date.replace('/', '-')
        filename = f"performance_{safe_date}_{racecourse}_R{race_no}.json"
        filepath = os.path.join(performance_dir, filename)

        # Save consolidated data to JSON file (results_data already contains everything)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, ensure_ascii=False, indent=2)

        print(f"Consolidated performance data saved to: {filepath}")
        return True

    except Exception as e:
        print(f"Error saving performance JSON: {str(e)}")
        return False

def save_results_to_pocketbase(results_data):
    """Save race results to PocketBase."""
    try:
        if not POCKETBASE_URL or not POCKETBASE_EMAIL or not POCKETBASE_PASSWORD:
            print("PocketBase configuration not found. Skipping PocketBase save.")
            return False

        # Login to PocketBase
        pb = PocketBase(POCKETBASE_URL)
        pb.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)

        # Prepare data for PocketBase
        pb_data = {
            "race_date": results_data["race_date"],
            "racecourse": results_data["racecourse"],
            "race_number": results_data["race_number"],
            "race_name": results_data["race_info"].get("full_text", ""),
            "race_class": results_data["race_info"].get("race_class", ""),
            "distance": results_data["race_info"].get("distance", ""),
            "track_condition": results_data["race_info"].get("track_condition", ""),
            "track_type": results_data["race_info"].get("track_type", ""),
            "prize_money": results_data["race_info"].get("prize_money", ""),
            "race_time": results_data["sectional_times"].get("times", [])[-1] if results_data["sectional_times"].get("times") else "",
            "sectional_times": results_data["sectional_times"],
            "results": results_data["results"],
            "payouts": results_data["payouts"],
            "incidents": results_data["incidents"],
            "raw_data": results_data
        }

        # Create record in PocketBase
        record = pb.collection(COLLECTION_NAME).create(pb_data)
        print(f"Results saved to PocketBase with ID: {record.id}")
        return True

    except Exception as e:
        print(f"Error saving results to PocketBase: {str(e)}")
        return False

async def scrape_multiple_races(race_date, racecourse, race_numbers):
    """
    Scrape results for multiple races.

    Args:
        race_date (str): Race date in format YYYY/MM/DD
        racecourse (str): Racecourse code ("ST" or "HV")
        race_numbers (list): List of race numbers to scrape

    Returns:
        list: List of race results data
    """
    all_results = []

    # Ensure PocketBase collection exists
    if POCKETBASE_URL:
        ensure_results_collection_exists()

    for race_no in race_numbers:
        print(f"\nScraping Race {race_no}...")

        try:
            results_data = await scrape_race_results(race_date, racecourse, race_no)

            if results_data:
                # Save consolidated performance JSON file (contains everything)
                save_performance_json(results_data, race_date, racecourse, race_no)

                # Save to PocketBase if configured
                if POCKETBASE_URL:
                    save_results_to_pocketbase(results_data)

                all_results.append(results_data)
                print(f"Successfully scraped Race {race_no}")
            else:
                print(f"No data found for Race {race_no}")

        except Exception as e:
            print(f"Error scraping Race {race_no}: {str(e)}")

    return all_results

def main():
    """Main function with command line argument support."""
    import sys

    # Parse command line arguments
    if len(sys.argv) >= 2:
        race_date = sys.argv[1]  # Format: YYYY/MM/DD
    else:
        race_date = "2025/06/04"  # Default fallback

    if len(sys.argv) >= 3:
        racecourse = sys.argv[2]  # "ST" for Sha Tin, "HV" for Happy Valley
    else:
        racecourse = "ST"  # Default fallback

    if len(sys.argv) >= 4:
        # Parse race number argument
        race_arg = sys.argv[3]

        if race_arg.isdigit():
            # Single race number
            race_numbers = [int(race_arg)]
        elif '-' in race_arg:
            # Range like "1-10"
            start, end = race_arg.split('-')
            race_numbers = list(range(int(start), int(end) + 1))
        else:
            # Default range for the racecourse
            race_numbers = list(range(1, 12)) if racecourse == "ST" else list(range(1, 10))
    else:
        # Default race numbers - extract all races for the racecourse
        race_numbers = list(range(1, 12)) if racecourse == "ST" else list(range(1, 10))

    print(f"HKJC Race Results Scraper")
    print(f"========================")
    print(f"Race Date: {race_date}")
    print(f"Racecourse: {racecourse}")
    print(f"Race Numbers: {race_numbers}")
    print(f"Output Directory: {OUTPUT_DIR}")
    if POCKETBASE_URL:
        print(f"PocketBase URL: {POCKETBASE_URL}")
        print(f"PocketBase Collection: {COLLECTION_NAME}")
    print()

    # Run the scraper
    results = asyncio.run(scrape_multiple_races(race_date, racecourse, race_numbers))

    print(f"\nScraping completed. Total races scraped: {len(results)}")

if __name__ == "__main__":
    main()
