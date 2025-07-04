import asyncio
import json
import re
import os
import glob
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
COLLECTION_NAME = os.getenv("POCKETBASE_COLLECTION")

# Race configuration from environment variables
# These are used as fallback values if get_race_info_from_hkjc() fails to extract information from HKJC website
RACE_DATE = os.getenv("RACE_DATE")
RACECOURSE = os.getenv("RACECOURSE")
TOTAL_RACES = int(os.getenv("TOTAL_RACES", "10"))

# Output directory for fallback JSON files
OUTPUT_DIR = "race_data"

def get_race_info_from_hkjc():
    """
    Scrape the HKJC racing website to get the race date and total race number.
    Returns a tuple of (race_date, racecourse, total_races) if successful, None otherwise.
    """
    global RACE_DATE, RACECOURSE, TOTAL_RACES

    try:
        print("Fetching race information from HKJC racing website...")

        # Try the racing information page instead of the betting page
        url = "https://racing.hkjc.com/racing/information/Chinese/racing/RaceCard.aspx"

        # Send a request to the HKJC racing website
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

        if response.status_code != 200:
            print(f"Failed to fetch HKJC racing website: {response.status_code}")
            return None

        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for the race date heading
        race_info_text = None
        for element in soup.find_all(text=True):
            if "第 1 場" in element and "年" in element and "月" in element and "日" in element:
                race_info_text = element.strip()
                break

        if race_info_text:
            print(f"Found race info text: {race_info_text}")

            # Extract date in format YYYY/MM/DD
            date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', race_info_text)
            if date_match:
                year = date_match.group(1)
                month = date_match.group(2).zfill(2)  # Ensure 2 digits
                day = date_match.group(3).zfill(2)    # Ensure 2 digits
                race_date = f"{year}/{month}/{day}"

                # Determine racecourse (沙田 or 跑馬地)
                racecourse_match = re.search(r'(沙田|跑馬地)', race_info_text)
                racecourse = "ST" if racecourse_match and racecourse_match.group(1) == "沙田" else "HV"

                # Count the number of race tabs
                race_tabs = []
                for img in soup.find_all('img'):
                    src = img.get('src', '')
                    if 'racecard_rt_' in src:
                        race_match = re.search(r'racecard_rt_(\d+)', src)
                        if race_match:
                            race_tabs.append(int(race_match.group(1)))

                if race_tabs:
                    total_races = max(race_tabs)

                    # Race information will be displayed in the configuration section

                    # Update global variables
                    RACE_DATE = race_date
                    RACECOURSE = racecourse
                    TOTAL_RACES = total_races

                    return (race_date, racecourse, total_races)

        # If we couldn't find the information in the main content, try looking for it in other elements
        date_heading = None
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div']):
            text = heading.get_text(strip=True)
            if "月" in text and "日" in text and ("沙田" in text or "跑馬地" in text):
                date_heading = text
                break

        if date_heading:
            print(f"Found date heading: {date_heading}")

            # Extract date components
            date_match = re.search(r'(\d{1,2})月(\d{1,2})日', date_heading)
            if date_match:
                month = date_match.group(1).zfill(2)
                day = date_match.group(2).zfill(2)
                # Assume current year if not specified
                from datetime import datetime
                year = datetime.now().year
                race_date = f"{year}/{month}/{day}"

                # Determine racecourse
                racecourse = "ST" if "沙田" in date_heading else "HV"

                # Count race tabs or links
                race_numbers = []
                for a in soup.find_all('a'):
                    href = a.get('href', '')
                    if 'RaceNo=' in href:
                        race_match = re.search(r'RaceNo=(\d+)', href)
                        if race_match:
                            race_numbers.append(int(race_match.group(1)))

                if race_numbers:
                    total_races = max(race_numbers)

                    # Race information will be displayed in the configuration section

                    # Update global variables
                    RACE_DATE = race_date
                    RACECOURSE = racecourse
                    TOTAL_RACES = total_races

                    return (race_date, racecourse, total_races)

        print("Could not extract race information from HKJC racing website")
        return None

    except Exception as e:
        print(f"Error fetching race information from HKJC: {str(e)}")
        return None

# Function to ensure the collection exists
def ensure_collection_exists():
    try:
        # Check if collection exists
        response = requests.get(f"{POCKETBASE_URL}/api/collections/{COLLECTION_NAME}")

        # If collection doesn't exist (404), create it
        if response.status_code == 404:
            print(f"Collection '{COLLECTION_NAME}' does not exist. Creating it...")

            # Define the collection schema
            collection_data = {
                "name": COLLECTION_NAME,
                "type": "base",
                "schema": [
                    {
                        "name": "race_number",
                        "type": "text",
                        "required": True
                    },
                    {
                        "name": "race_date",
                        "type": "text",
                        "required": True
                    },
                    {
                        "name": "race_name",
                        "type": "text",
                        "required": True
                    },
                    {
                        "name": "venue",
                        "type": "text",
                        "required": False
                    },
                    {
                        "name": "race_time",
                        "type": "text",
                        "required": False
                    },
                    {
                        "name": "track_type",
                        "type": "text",
                        "required": False
                    },
                    {
                        "name": "course",
                        "type": "text",
                        "required": False
                    },
                    {
                        "name": "distance",
                        "type": "text",
                        "required": False
                    },
                    {
                        "name": "prize_money",
                        "type": "text",
                        "required": False
                    },
                    {
                        "name": "rating",
                        "type": "text",
                        "required": False
                    },
                    {
                        "name": "race_class",
                        "type": "text",
                        "required": False
                    },
                    {
                        "name": "entries",
                        "type": "json",
                        "required": False
                    },
                    {
                        "name": "reserve_horses",
                        "type": "json",
                        "required": False
                    },
                    {
                        "name": "equipment_legend",
                        "type": "json",
                        "required": False
                    },
                    {
                        "name": "created_at",
                        "type": "text",
                        "required": False
                    }
                ]
            }

            # Create the collection
            create_response = requests.post(
                f"{POCKETBASE_URL}/api/collections",
                json=collection_data,
                headers={"Content-Type": "application/json"}
            )

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

async def main(race) -> None:
    # Target URL with the race information
    target_url = f"https://racing.hkjc.com/racing/information/chinese/Racing/Racecard.aspx?RaceDate={RACE_DATE}&Racecourse={RACECOURSE}&RaceNo={race}"

    # Create a BeautifulSoupCrawler instance
    crawler = BeautifulSoupCrawler()

    # Define a request handler to process the page
    @crawler.router.default_handler
    async def request_handler(context: BeautifulSoupCrawlingContext) -> None:
        context.log.info(f'Processing {context.request.url} ...')

        try:
            # Extract race information
            race_info = extract_race_info(context, race)

            # Extract horse entries
            entries = extract_horse_entries(context)

            # Extract reserve horses
            reserve_horses = extract_reserve_horses(context)

            # Create equipment legend manually
            equipment_legend = {
                "B": "戴眼罩",
                "BO": "只戴單邊眼罩",
                "CC": "喉托",
                "CP": "羊毛面箍",
                "CO": "戴單邊羊毛面箍",
                "E": "戴耳塞",
                "H": "戴頭罩",
                "P": "戴防沙眼罩",
                "PC": "戴半掩防沙眼罩",
                "PS": "戴單邊半掩防沙眼罩",
                "SB": "戴羊毛額箍",
                "SR": "鼻箍",
                "TT": "綁繫舌帶",
                "V": "戴開縫眼罩",
                "VO": "戴單邊開縫眼罩",
                "XB": "交叉鼻箍",
                "1": "首次",
                "2": "重戴",
                "-": "除去"
            }

            # Combine all data
            result = {
                "race_info": race_info,
                "entries": entries,
                "reserve_horses": reserve_horses,
                "equipment_legend": equipment_legend
            }

            # Store the extracted data
            await context.push_data(result)

            # Print the extracted information
            print("\n--- Extracted Horse Race Data ---")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            print("--------------------------------\n")

            # Save to PocketBase
            save_to_pocketbase(result, race)

        except Exception as e:
            context.log.error(f"Error extracting horse entries: {str(e)}")
            import traceback
            traceback.print_exc()

    # Run the crawler with the target URL
    await crawler.run([target_url])

def extract_race_info(context, race):
    """Extract basic race information"""
    try:
        # Look for the race information text
        race_info_element = context.soup.find(string=lambda s: f"第 {race} 場 - " in s if s else False)
        if race_info_element:
            # Get the parent element to get the full text
            parent = race_info_element.parent
            if parent:
                race_info = parent.get_text(strip=True)

                # Clean up the text
                race_info = re.sub(r'\s+', ' ', race_info).strip()

                # Extract specific information using regex patterns
                race_name_match = re.search(r'(第\s*\d+\s*場\s*-\s*[^\d,]+)', race_info)
                race_name = race_name_match.group(1).strip() if race_name_match else None

                date_match = re.search(r'(\d{4}年\d{1,2}月\d{1,2}日)', race_info)
                race_date = date_match.group(1) if date_match else None

                day_match = re.search(r'(星期[一二三四五六日])', race_info)
                race_day = day_match.group(1) if day_match else None

                venue_match = re.search(r'(沙田|跑馬地)', race_info)
                venue = venue_match.group(1) if venue_match else None

                time_match = re.search(r'(\d{1,2}:\d{2})', race_info)
                race_time = time_match.group(1) if time_match else None

                track_match = re.search(r'(草地|全天候跑道)', race_info)
                track_type = track_match.group(1) if track_match else None

                course_match = re.search(r'"([^"]+)"', race_info)
                course = course_match.group(1) if course_match else None

                distance_match = re.search(r'(\d+)米', race_info)
                distance = distance_match.group(1) if distance_match else None

                prize_match = re.search(r'獎金:\s*\$([0-9,]+)', race_info)
                prize_money = prize_match.group(1) if prize_match else None

                rating_match = re.search(r'評分:\s*([0-9-]+)', race_info)
                rating = rating_match.group(1) if rating_match else None

                class_match = re.search(r'第([一二三四五])班', race_info)
                race_class = class_match.group(1) if class_match else None

                # Create a structured data object
                data = {
                    'race_name': race_name,
                    'race_date': race_date,
                    'race_day': race_day,
                    'venue': venue,
                    'race_time': race_time,
                    'track_type': track_type,
                    'course': course,
                    'distance': distance,
                    'prize_money': prize_money,
                    'rating': rating,
                    'race_class': race_class,
                    'full_text': race_info
                }

                # Remove None values for cleaner output
                return {k: v for k, v in data.items() if v is not None}

        return {"error": "Could not find race information"}
    except Exception as e:
        return {"error": f"Error extracting race info: {str(e)}"}

def extract_horse_entries(context):
    """Extract horse entries from the table"""
    entries = []
    seen_numbers = set()  # To avoid duplicates

    # Find all tables in the page
    tables = context.soup.find_all('table')

    # Look for the table with horse entries
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) > 5:  # Assuming horse entry rows have multiple columns
                first_cell_text = cells[0].get_text(strip=True)
                # Check if first cell contains just a number (likely horse number)
                if first_cell_text.isdigit() and 1 <= int(first_cell_text) <= 14:
                    # Skip if we've already seen this horse number
                    if first_cell_text in seen_numbers:
                        continue

                    seen_numbers.add(first_cell_text)

                    # Found a horse entry row
                    entry = {
                        "horse_number": first_cell_text,
                        "recent_form": cells[1].get_text(strip=True) if len(cells) > 1 else "",
                        "horse_name": cells[3].get_text(strip=True) if len(cells) > 3 else "",
                        "horse_code": cells[4].get_text(strip=True) if len(cells) > 4 else "",
                        "weight": cells[5].get_text(strip=True) if len(cells) > 5 else "",
                        "jockey": cells[6].get_text(strip=True) if len(cells) > 6 else "",
                        "draw": cells[8].get_text(strip=True) if len(cells) > 8 else "",
                        "trainer": cells[9].get_text(strip=True) if len(cells) > 9 else "",
                        "rating": cells[11].get_text(strip=True) if len(cells) > 11 else "",
                        "rating_change": cells[12].get_text(strip=True) if len(cells) > 12 else "",
                        "best_time": cells[15].get_text(strip=True) if len(cells) > 15 else "",
                        "age": cells[16].get_text(strip=True) if len(cells) > 16 else "",
                        "season_prize": cells[19].get_text(strip=True) if len(cells) > 19 else "",
                        "days_since_last": cells[21].get_text(strip=True) if len(cells) > 21 else "",
                        "equipment": cells[22].get_text(strip=True) if len(cells) > 22 else "",
                        "owner": cells[23].get_text(strip=True) if len(cells) > 23 else "",
                        "sire": cells[24].get_text(strip=True) if len(cells) > 24 else "",
                        "dam": cells[25].get_text(strip=True) if len(cells) > 25 else "",
                        "import_type": cells[26].get_text(strip=True) if len(cells) > 26 else ""
                    }
                    entries.append(entry)

    return entries

def extract_reserve_horses(context):
    """Extract reserve horses information"""
    reserve_horses = []

    # Find the text "後 備 馬 匹" to locate the reserve horses section
    reserve_text = context.soup.find(string=lambda s: "後 備 馬 匹" in s if s else False)
    if reserve_text:
        print("Found reserve horses section")
        # First approach: Look for a table after the reserve horses text
        parent = reserve_text.parent
        reserve_table = None

        # Try to find the table containing reserve horses
        while parent:
            # Look for the next sibling element
            next_element = parent.find_next_sibling()
            if next_element and next_element.name == 'table':
                reserve_table = next_element
                break
            # If no sibling found, move up to the parent
            parent = parent.parent
            if not parent:
                break

        # If we found a table, extract data from it
        if reserve_table:
            print("Found reserve horses table")
            rows = reserve_table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 6:  # Ensure it has enough columns
                    # Get the first cell (reserve number)
                    first_cell = cells[0].get_text(strip=True)
                    # Check if it's a digit (likely a reserve horse number)
                    if first_cell.isdigit() and len(first_cell) <= 2:
                        reserve_horse = {
                            "reserve_number": first_cell,
                            "horse_name": cells[1].get_text(strip=True) if len(cells) > 1 else "",
                            "weight": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                            "rating": cells[3].get_text(strip=True) if len(cells) > 3 else "",
                            "age": cells[4].get_text(strip=True) if len(cells) > 4 else "",
                            "recent_form": cells[5].get_text(strip=True) if len(cells) > 5 else "",
                            "trainer": cells[6].get_text(strip=True) if len(cells) > 6 else "",
                            "priority": cells[7].get_text(strip=True) if len(cells) > 7 else "",
                            "equipment": cells[8].get_text(strip=True) if len(cells) > 8 else ""
                        }
                        reserve_horses.append(reserve_horse)

        # Second approach: Look for tables that might contain reserve horses
        if not reserve_horses:
            print("Trying alternative approach for reserve horses")
            # Find all tables in the document
            tables = context.soup.find_all('table')

            # Look for tables that might be near the reserve horses text
            for table in tables:
                # Check if this table is close to the reserve horses text
                if "後 備 馬 匹" in table.get_text():
                    # Process rows in this table
                    for row in table.find_all('tr'):
                        cells = row.find_all('td')
                        if len(cells) >= 6:  # Ensure it has enough columns
                            # Get the first cell (reserve number)
                            first_cell = cells[0].get_text(strip=True)
                            # Check if it's a digit (likely a reserve horse number)
                            if first_cell.isdigit() and len(first_cell) <= 2:
                                reserve_horse = {
                                    "reserve_number": first_cell,
                                    "horse_name": cells[1].get_text(strip=True) if len(cells) > 1 else "",
                                    "weight": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                                    "rating": cells[3].get_text(strip=True) if len(cells) > 3 else "",
                                    "age": cells[4].get_text(strip=True) if len(cells) > 4 else "",
                                    "recent_form": cells[5].get_text(strip=True) if len(cells) > 5 else "",
                                    "trainer": cells[6].get_text(strip=True) if len(cells) > 6 else "",
                                    "priority": cells[7].get_text(strip=True) if len(cells) > 7 else "",
                                    "equipment": cells[8].get_text(strip=True) if len(cells) > 8 else ""
                                }
                                reserve_horses.append(reserve_horse)

    return reserve_horses

def save_to_pocketbase(data, race_no):
    """Save the extracted data to PocketBase and local JSON file"""
    # First, always save to a local JSON file
    try:
        # Format the race date for the filename (convert from YYYY/MM/DD to YYYY_MM_DD)
        formatted_date = RACE_DATE.replace('/', '_')

        # Create the filename
        json_filename = f"{OUTPUT_DIR}/race_{formatted_date}_{RACECOURSE}_R{race_no}.json"

        # Ensure the output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # Save the data to the JSON file
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"Successfully saved race {race_no} to local JSON file: {json_filename}")
    except Exception as json_error:
        print(f"Error saving to local JSON file: {str(json_error)}")

    # Then, try to save to PocketBase
    try:
        # Ensure the collection exists
        if not ensure_collection_exists():
            print("Failed to ensure collection exists. Cannot save to PocketBase.")
            return

        # Initialize PocketBase client
        client = PocketBase(POCKETBASE_URL)

        # Authenticate with regular user credentials from environment variables
        try:
            user_data = client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
            print("Successfully authenticated as regular user")
            print(f"Auth token: {user_data.token}")
        except Exception as auth_error:
            print(f"User authentication failed: {str(auth_error)}")
            print("Continuing without authentication - this may work for public collections")

        # Format the race date for PocketBase (convert from YYYY/MM/DD to YYYY-MM-DD)
        formatted_date = RACE_DATE.replace('/', '-')

        # Prepare the data for PocketBase
        race_data = {
            "race_number": str(race_no),
            "race_date": formatted_date,
            "race_name": data["race_info"].get("race_name", ""),
            "venue": data["race_info"].get("venue", ""),
            "race_time": data["race_info"].get("race_time", ""),
            "track_type": data["race_info"].get("track_type", ""),
            "course": data["race_info"].get("course", ""),
            "distance": data["race_info"].get("distance", ""),
            "prize_money": data["race_info"].get("prize_money", ""),
            "rating": data["race_info"].get("rating", ""),
            "race_class": data["race_info"].get("race_class", ""),
            "full_text": data["race_info"].get("full_text", ""),
            "entries": json.dumps(data["entries"], ensure_ascii=False),
            "reserve_horses": json.dumps(data["reserve_horses"], ensure_ascii=False),
            "equipment_legend": json.dumps(data["equipment_legend"], ensure_ascii=False),
            "created_at": datetime.now().isoformat()
        }

        # Try to create a record in PocketBase
        try:
            result = client.collection(COLLECTION_NAME).create(race_data)
            print(f"Successfully saved race {race_no} to PocketBase with ID: {result.id}")
        except Exception as create_error:
            print(f"Error creating record in PocketBase: {str(create_error)}")

            # If that fails, try using the direct API approach
            try:
                print("Trying direct API approach...")
                api_url = f"{POCKETBASE_URL}/api/collections/{COLLECTION_NAME}/records"
                headers = {"Content-Type": "application/json"}
                response = requests.post(api_url, json=race_data, headers=headers)

                if response.status_code == 200 or response.status_code == 201:
                    print(f"Successfully saved race {race_no} to PocketBase using direct API")
                else:
                    print(f"Failed to save using direct API: {response.text}")
            except Exception as api_error:
                print(f"Error with direct API approach: {str(api_error)}")

    except Exception as e:
        print(f"Error saving to PocketBase: {str(e)}")

async def process_all_races(total_races):
    """Process all races sequentially in a single asyncio event loop"""
    # First, ensure the collection exists
    print("Checking if collection exists...")
    if not ensure_collection_exists():
        print("Failed to ensure collection exists. Will save to local files instead.")

    # Process each race one at a time
    for race_no in range(1, total_races +1):
        print(f"\nProcessing race {race_no}...")
        # Wait for each race to complete before starting the next one
        await main(race_no)
        print(f"Completed processing race {race_no}\n")



def generate_prompt_files():
    """Generate prompt text files from race data JSON files"""
    # Get the prompt input from environment variables
    PROMPT_INPUT = os.getenv("PROMPT_INPUT", "作為資深評馬人，根據香港賽馬, 附上以下json資料,那些馬匹可能勝出入三甲及那些馬匹不可能勝出. 6次近績,由左至右排列，左邊是最近.")

    # Output directory for prompt text files
    PROMPT_OUTPUT_DIR = "prompt_text_files"

    # Ensure the output directory exists
    os.makedirs(PROMPT_OUTPUT_DIR, exist_ok=True)

    # Get all JSON files in the input directory
    json_files = glob.glob(f"{OUTPUT_DIR}/*.json")

    print(f"\nGenerating prompt text files...")
    print(f"Found {len(json_files)} JSON files in {OUTPUT_DIR}")

    # Track counts for reporting
    created_count = 0
    skipped_count = 0

    # Process each JSON file
    for json_file in json_files:
        # Get the base filename without extension
        base_name = os.path.basename(json_file).split('.')[0]

        # Create the output filename
        output_file = f"{PROMPT_OUTPUT_DIR}/{base_name}_with_prompt.txt"

        # Check if the output file already exists
        if os.path.exists(output_file):
            # Skip this file and increment the skipped count
            print(f"  Skipping {base_name}_with_prompt.txt (already exists)")
            skipped_count += 1
            continue

        try:
            # Read the JSON file
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Create the prompt file with the prompt input and JSON data
            with open(output_file, 'w', encoding='utf-8') as f:
                # Write the prompt input
                f.write(f"{PROMPT_INPUT}\n\n")

                # Write the JSON data
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"  Created {base_name}_with_prompt.txt")
            created_count += 1

        except Exception as e:
            print(f"  Error processing {json_file}: {str(e)}")

    print(f"Prompt file generation complete:")
    print(f"  Created: {created_count} new prompt files")
    print(f"  Skipped: {skipped_count} existing prompt files")
    print(f"  Total: {created_count + skipped_count} files processed")

if __name__ == '__main__':
    # Create the output directory for fallback JSON files
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Try to get race information from HKJC website
    race_info = get_race_info_from_hkjc()

    # If we couldn't get race info from HKJC, use environment variables
    if race_info is None:
        print("Using race information from environment variables")
    else:
        print("Using race information from HKJC website")

    # Print configuration
    print(f"Configuration:")
    print(f"  PocketBase URL: {POCKETBASE_URL}")
    print(f"  PocketBase Collection: {COLLECTION_NAME}")
    print(f"  Race Date: {RACE_DATE}")
    print(f"  Racecourse: {RACECOURSE}")
    print(f"  Total Races: {TOTAL_RACES}")
    print(f"  Output Directory: {OUTPUT_DIR}")
    print()

    # Note: get_race_date is a view, so we don't need to save the race date

    # Run the crawler
    asyncio.run(process_all_races(TOTAL_RACES))

    # Generate prompt text files after crawling is complete
    generate_prompt_files()
