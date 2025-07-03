import asyncio
import json
import re
import os
from playwright.async_api import async_playwright
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Output directory for JSON files
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "odds_data")

def parse_url(url):
    """Parse HKJC odds URL to extract race details"""
    # URL formats:
    # https://bet.hkjc.com/ch/racing/wp/2025-07-01/ST/1
    # https://bet.hkjc.com/ch/racing/pwin/2025-07-01/ST/1
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

async def scrape_odds_with_playwright(url):
    """
    Scrape odds data using Playwright directly
    """
    
    try:
        race_date, venue, race_number = parse_url(url)
        
        print(f"Attempting to scrape odds from: {url}")
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = await context.new_page()

            # Capture network requests to see if we can find API endpoints
            network_requests = []

            async def handle_request(request):
                network_requests.append({
                    'url': request.url,
                    'method': request.method,
                    'headers': dict(request.headers)
                })

            page.on('request', handle_request)
            
            # Set timeout
            page.set_default_timeout(30000)  # 30 seconds
            
            try:
                # Navigate to the page
                print("Navigating to the page...")
                await page.goto(url, wait_until='domcontentloaded')

                # Wait for the page to load completely
                print("Waiting for page to load...")
                await page.wait_for_timeout(10000)  # Wait 10 seconds for dynamic content

                # Try to trigger JavaScript by scrolling and clicking
                print("Triggering JavaScript...")
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(3000)

                # Try clicking on the page to trigger any lazy loading
                try:
                    await page.click('body')
                    await page.wait_for_timeout(2000)
                except:
                    pass
                
                # Get page title
                page_title = await page.title()
                print(f"Page title: {page_title}")
                
                # Initialize odds data
                odds_data = {
                    "race_date": race_date,
                    "venue": venue,
                    "race_number": race_number,
                    "scraped_at": datetime.now().isoformat(),
                    "source_url": url,
                    "page_title": page_title
                }
                
                # Check if the page loaded properly
                page_content = await page.content()
                page_text = await page.text_content('body')

                # Debug: Print some of the page content
                print(f"Page content length: {len(page_content)}")
                print(f"Page text length: {len(page_text)}")
                print(f"First 500 characters of page text: {page_text[:500]}")

                # Log network requests for debugging
                print(f"Captured {len(network_requests)} network requests")

                # Look for potential data API requests
                data_requests = []
                for req in network_requests:
                    url_lower = req['url'].lower()
                    if any(keyword in url_lower for keyword in ['api', 'json', 'data', 'odds', 'bet', 'race']):
                        # Exclude common non-data requests
                        if not any(exclude in url_lower for exclude in ['font', 'css', 'js', 'image', 'icon', 'static']):
                            data_requests.append(req)

                if data_requests:
                    print("Found potential data API requests:")
                    for req in data_requests[:10]:  # Show first 10 data requests
                        print(f"  {req['method']} {req['url']}")
                else:
                    print("No obvious data API requests found")
                    # Show all unique domains to help identify potential APIs
                    domains = set()
                    for req in network_requests:
                        try:
                            from urllib.parse import urlparse
                            domain = urlparse(req['url']).netloc
                            domains.add(domain)
                        except:
                            pass
                    print(f"Unique domains accessed: {sorted(domains)}")

                if "You need to enable JavaScript" in page_content:
                    odds_data["error"] = "Page still requires JavaScript after loading"
                    odds_data["debug_content"] = page_text[:1000]  # Save some content for debugging
                    odds_data["network_requests"] = len(network_requests)
                    odds_data["data_requests"] = [req['url'] for req in data_requests[:3]]  # Save some API URLs
                    return odds_data
                
                # Try to extract race information
                print("Extracting race information...")
                race_info = await extract_race_info_playwright(page)
                if race_info:
                    odds_data["race_info"] = race_info
                
                # Try to extract odds data
                print("Extracting odds data...")
                
                # Look for Win/Place odds
                win_place_odds = await extract_win_place_odds_playwright(page)
                if win_place_odds:
                    odds_data["win_place_odds"] = win_place_odds
                
                # Look for other bet types
                other_odds = await extract_other_odds_playwright(page)
                if other_odds:
                    odds_data.update(other_odds)
                
                # Check if we found any meaningful odds data
                if any(key in odds_data for key in ["win_place_odds", "quinella_odds", "exotic_odds"]):
                    odds_data["extraction_successful"] = True
                else:
                    odds_data["extraction_successful"] = False
                    odds_data["note"] = "No odds data found - page structure may have changed"
                
                return odds_data
                
            except Exception as e:
                print(f"Error during page processing: {str(e)}")
                return {
                    "error": f"Page processing error: {str(e)}",
                    "race_date": race_date,
                    "venue": venue,
                    "race_number": race_number,
                    "scraped_at": datetime.now().isoformat(),
                    "source_url": url
                }
            
            finally:
                await browser.close()
        
    except Exception as e:
        print(f"Error scraping odds: {str(e)}")
        return {
            "error": str(e),
            "scraped_at": datetime.now().isoformat(),
            "source_url": url
        }

async def extract_race_info_playwright(page):
    """Extract race information using Playwright"""
    try:
        race_info = {}
        
        # Try different selectors for race title
        title_selectors = [
            'h1', 'h2', '.race-title', '.race-name', 
            '[class*="title"]', '[class*="race"]'
        ]
        
        for selector in title_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text and text.strip():
                        race_info['title'] = text.strip()
                        break
            except:
                continue
        
        # Try to find race time
        time_selectors = [
            '.race-time', '.start-time', '[class*="time"]'
        ]
        
        for selector in time_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text and text.strip():
                        race_info['race_time'] = text.strip()
                        break
            except:
                continue
        
        # Get all text content and look for patterns
        page_text = await page.text_content('body')
        
        # Look for race time patterns in the text
        time_patterns = [
            r'(\d{1,2}:\d{2})',
            r'開跑時間[：:]\s*(\d{1,2}:\d{2})',
            r'Race Time[：:]\s*(\d{1,2}:\d{2})'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, page_text)
            if match and 'race_time' not in race_info:
                race_info['race_time'] = match.group(1)
                break
        
        # Look for venue information
        if '沙田' in page_text:
            race_info['venue_chinese'] = '沙田'
        elif '跑馬地' in page_text:
            race_info['venue_chinese'] = '跑馬地'
        
        return race_info if race_info else None
        
    except Exception as e:
        print(f"Error extracting race info: {str(e)}")
        return None

async def extract_win_place_odds_playwright(page):
    """Extract Win and Place odds using Playwright"""
    try:
        odds_data = []
        
        # Look for tables that might contain odds
        tables = await page.query_selector_all('table')
        
        for table in tables:
            try:
                # Get table text to check if it contains odds
                table_text = await table.text_content()
                
                # Check if this table might contain odds
                if any(keyword in table_text for keyword in ['賠率', 'odds', '獨贏', 'Win', 'Place']):
                    rows = await table.query_selector_all('tr')
                    
                    for row in rows:
                        try:
                            cells = await row.query_selector_all('td, th')
                            if len(cells) >= 3:  # Need at least horse number, name, and odds
                                cell_texts = []
                                for cell in cells:
                                    text = await cell.text_content()
                                    cell_texts.append(text.strip() if text else "")
                                
                                # Check if first cell looks like a horse number
                                if cell_texts[0].isdigit() and 1 <= int(cell_texts[0]) <= 14:
                                    odds_entry = {
                                        "horse_number": cell_texts[0],
                                        "horse_name": cell_texts[1] if len(cell_texts) > 1 else "",
                                        "win_odds": cell_texts[2] if len(cell_texts) > 2 else "",
                                        "place_odds": cell_texts[3] if len(cell_texts) > 3 else ""
                                    }
                                    odds_data.append(odds_entry)
                        except:
                            continue
            except:
                continue
        
        # Also try to find odds in div/span elements
        odds_elements = await page.query_selector_all('[class*="odds"], [class*="bet"], [class*="win"], [class*="place"]')
        
        if odds_elements and not odds_data:
            # If we found odds elements but no table data, extract what we can
            odds_texts = []
            for element in odds_elements:
                try:
                    text = await element.text_content()
                    if text and text.strip():
                        odds_texts.append(text.strip())
                except:
                    continue
            
            if odds_texts:
                return {"odds_elements": odds_texts}
        
        return odds_data if odds_data else None
        
    except Exception as e:
        print(f"Error extracting win/place odds: {str(e)}")
        return None

async def extract_other_odds_playwright(page):
    """Extract other types of odds (Quinella, exotic bets, etc.)"""
    try:
        other_odds = {}
        
        # Get all text content
        page_text = await page.text_content('body')
        
        # Look for different bet types
        bet_types = {
            'quinella': ['連贏', 'Quinella', 'QIN'],
            'quinella_place': ['位置Q', 'Quinella Place', 'QPL'],
            'tierce': ['三重彩', 'Tierce', 'TCE'],
            'trio': ['三T', 'Trio', 'TRI'],
            'first4': ['四連環', 'First 4', 'F4'],
            'quartet': ['四重彩', 'Quartet', 'QTT']
        }
        
        for bet_type, keywords in bet_types.items():
            for keyword in keywords:
                if keyword in page_text:
                    # Try to find odds for this bet type
                    try:
                        # Look for elements that might contain this bet type's odds
                        selectors = [
                            f'[class*="{bet_type}"]',
                            f'[class*="{keyword.lower()}"]'
                        ]
                        
                        for selector in selectors:
                            elements = await page.query_selector_all(selector)
                            if elements:
                                bet_data = []
                                for element in elements:
                                    text = await element.text_content()
                                    if text and text.strip():
                                        bet_data.append(text.strip())
                                
                                if bet_data:
                                    other_odds[bet_type] = bet_data
                                    break
                    except:
                        continue
                    break
        
        return other_odds if other_odds else None
        
    except Exception as e:
        print(f"Error extracting other odds: {str(e)}")
        return None

def save_odds_to_json(odds_data, race_date, venue, race_number):
    """Save odds data to JSON file"""
    try:
        # Format the race date for the filename (convert from YYYY-MM-DD to YYYY_MM_DD)
        formatted_date = race_date.replace('-', '_')
        
        # Create the filename
        json_filename = f"{OUTPUT_DIR}/odds_{formatted_date}_{venue}_R{race_number}.json"
        
        # Ensure the output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Save the data to the JSON file
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(odds_data, f, ensure_ascii=False, indent=2)
        
        print(f"Successfully saved odds data to: {json_filename}")
        return json_filename
    except Exception as e:
        print(f"Error saving odds data to JSON: {str(e)}")
        return None

async def main(url=None):
    """Main function to scrape odds for a specific race"""
    if url is None:
        # Default URL from your request
        url = "https://bet.hkjc.com/ch/racing/wp/2025-07-01/ST/1"
    
    try:
        # Parse the URL to extract race details
        race_date, venue, race_number = parse_url(url)
        
        print(f"Scraping odds for Race {race_number} on {race_date} at {venue}")
        print(f"Source URL: {url}")
        
        # Scrape the odds data
        odds_data = await scrape_odds_with_playwright(url)
        
        if odds_data:
            # Print the extracted data
            print("\n--- Extracted Odds Data ---")
            print(json.dumps(odds_data, ensure_ascii=False, indent=2))
            print("---------------------------\n")
            
            # Save to JSON file
            json_file = save_odds_to_json(odds_data, race_date, venue, race_number)
            
            if json_file:
                print(f"Odds data saved successfully to {json_file}")
            else:
                print("Failed to save odds data to JSON file")
        else:
            print("No odds data was extracted")
            
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == '__main__':
    import sys
    
    # Create the output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Check if URL is provided as command line argument
    url = None
    if len(sys.argv) > 1:
        url = sys.argv[1]
    
    # Run the scraper
    asyncio.run(main(url))
