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

async def get_win_odds_trends(url):
    """
    Get 獨贏賠率走勢 (Win Odds Trends) data using Playwright
    """
    
    try:
        race_date, venue, race_number = parse_url(url)
        
        print(f"Getting Win Odds Trends for Race {race_number} on {race_date} at {venue}")
        print(f"Source URL: {url}")
        
        async with async_playwright() as p:
            # Launch browser with specific settings for better success
            browser = await p.chromium.launch(
                headless=False,  # Use visible browser to better handle JS
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
                locale='zh-HK'
            )
            
            page = await context.new_page()
            
            # Capture network requests to find odds data
            odds_requests = []
            
            async def handle_response(response):
                url_lower = response.url.lower()
                # Look for requests that might contain odds data
                if any(keyword in url_lower for keyword in ['odds', 'win', 'trend', 'api', 'data']):
                    try:
                        if response.status == 200:
                            content_type = response.headers.get('content-type', '')
                            if 'json' in content_type:
                                data = await response.json()
                                odds_requests.append({
                                    'url': response.url,
                                    'method': response.request.method,
                                    'status': response.status,
                                    'data': data
                                })
                                print(f"📊 Found JSON odds data: {response.url}")
                            elif 'xml' in content_type:
                                text = await response.text()
                                odds_requests.append({
                                    'url': response.url,
                                    'method': response.request.method,
                                    'status': response.status,
                                    'data': text[:2000]  # First 2000 chars
                                })
                                print(f"📊 Found XML odds data: {response.url}")
                    except Exception as e:
                        print(f"Error processing response from {response.url}: {e}")
            
            page.on('response', handle_response)
            
            try:
                # Navigate to the page
                print("🌐 Navigating to the betting page...")
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                
                # Wait for initial load
                await page.wait_for_timeout(5000)
                
                # Try to find and click on Win Odds section
                print("🔍 Looking for Win Odds section...")
                
                # Look for elements that might contain win odds
                win_odds_selectors = [
                    'text=獨贏',
                    'text=Win',
                    '[data-testid*="win"]',
                    '[class*="win"]',
                    '[id*="win"]',
                    'text=賠率',
                    'text=Odds'
                ]
                
                win_section_found = False
                for selector in win_odds_selectors:
                    try:
                        element = await page.wait_for_selector(selector, timeout=3000)
                        if element:
                            print(f"✅ Found win odds element: {selector}")
                            await element.click()
                            win_section_found = True
                            await page.wait_for_timeout(2000)
                            break
                    except:
                        continue
                
                if not win_section_found:
                    print("⚠️ Win odds section not found, trying to extract from current page")
                
                # Look for trends/history section
                print("📈 Looking for odds trends section...")
                trends_selectors = [
                    'text=走勢',
                    'text=Trends',
                    'text=歷史',
                    'text=History',
                    '[data-testid*="trend"]',
                    '[class*="trend"]',
                    '[class*="history"]'
                ]
                
                for selector in trends_selectors:
                    try:
                        element = await page.wait_for_selector(selector, timeout=3000)
                        if element:
                            print(f"✅ Found trends element: {selector}")
                            await element.click()
                            await page.wait_for_timeout(3000)
                            break
                    except:
                        continue
                
                # Wait for any additional data to load
                print("⏳ Waiting for odds data to load...")
                await page.wait_for_timeout(5000)
                
                # Try to extract odds data from the page
                print("🔍 Extracting odds data from page...")
                
                # Look for tables or containers with odds data
                odds_data = await extract_win_odds_from_page(page)
                
                # Prepare result
                result = {
                    "race_info": {
                        "race_date": race_date,
                        "venue": venue,
                        "race_number": race_number,
                        "source_url": url,
                        "scraped_at": datetime.now().isoformat()
                    },
                    "win_odds_trends": odds_data,
                    "network_data": odds_requests,
                    "extraction_summary": {
                        "page_loaded": True,
                        "win_section_found": win_section_found,
                        "odds_data_found": len(odds_data) > 0 if odds_data else False,
                        "network_requests_captured": len(odds_requests)
                    }
                }
                
                return result
                
            except Exception as e:
                print(f"❌ Error during page processing: {str(e)}")
                return {
                    "race_info": {
                        "race_date": race_date,
                        "venue": venue,
                        "race_number": race_number,
                        "source_url": url,
                        "scraped_at": datetime.now().isoformat()
                    },
                    "error": str(e),
                    "network_data": odds_requests
                }
            
            finally:
                await browser.close()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {
            "error": str(e),
            "scraped_at": datetime.now().isoformat(),
            "source_url": url
        }

async def extract_win_odds_from_page(page):
    """Extract win odds data from the current page"""
    try:
        odds_data = []
        
        # Method 1: Look for tables with odds data
        print("🔍 Method 1: Looking for odds tables...")
        tables = await page.query_selector_all('table')
        
        for i, table in enumerate(tables):
            try:
                table_text = await table.text_content()
                
                # Check if this table contains odds-related content
                if any(keyword in table_text for keyword in ['賠率', 'odds', '獨贏', 'win', '馬', 'horse']):
                    print(f"📊 Found potential odds table {i+1}")
                    
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
            except:
                continue
        
        # Method 2: Look for specific odds elements
        print("🔍 Method 2: Looking for odds elements...")
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
                        print(f"📊 Found {len(element_data)} odds elements with selector: {selector}")
            except:
                continue
        
        # Method 3: Look for any text that looks like odds
        print("🔍 Method 3: Looking for odds patterns in text...")
        page_text = await page.text_content('body')
        
        # Look for odds patterns (numbers with decimal points that could be odds)
        odds_patterns = re.findall(r'\b\d+\.\d{1,2}\b', page_text)
        if odds_patterns:
            # Filter to likely odds values (typically between 1.0 and 999.0)
            likely_odds = [float(odds) for odds in odds_patterns if 1.0 <= float(odds) <= 999.0]
            if likely_odds:
                odds_data.append({
                    "type": "text_patterns",
                    "data": likely_odds
                })
                print(f"📊 Found {len(likely_odds)} potential odds values in text")
        
        return odds_data if odds_data else None
        
    except Exception as e:
        print(f"❌ Error extracting odds from page: {str(e)}")
        return None

def save_win_odds_to_json(data, race_date, venue, race_number):
    """Save win odds data to JSON file"""
    try:
        formatted_date = race_date.replace('-', '_')
        json_filename = f"{OUTPUT_DIR}/win_odds_trends_{formatted_date}_{venue}_R{race_number}.json"
        
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Successfully saved win odds data to: {json_filename}")
        return json_filename
    except Exception as e:
        print(f"❌ Error saving win odds data to JSON: {str(e)}")
        return None

async def main(url=None):
    """Main function to get win odds trends for a specific race"""
    if url is None:
        url = "https://bet.hkjc.com/ch/racing/pwin/2025-07-01/ST/1"
    
    try:
        race_date, venue, race_number = parse_url(url)
        
        print("🏇 HKJC Win Odds Trends Extractor")
        print("=" * 50)
        print(f"Race: {race_number} | Date: {race_date} | Venue: {venue}")
        print("=" * 50)
        
        # Get win odds trends data
        data = await get_win_odds_trends(url)
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 EXTRACTION SUMMARY:")
        
        if "error" in data:
            print(f"❌ Error: {data['error']}")
        else:
            summary = data.get("extraction_summary", {})
            print(f"✅ Page Loaded: {summary.get('page_loaded', False)}")
            print(f"🎯 Win Section Found: {summary.get('win_section_found', False)}")
            print(f"📈 Odds Data Found: {summary.get('odds_data_found', False)}")
            print(f"🌐 Network Requests: {summary.get('network_requests_captured', 0)}")
            
            if data.get("win_odds_trends"):
                print(f"📊 Odds Data Sections: {len(data['win_odds_trends'])}")
            
            if data.get("network_data"):
                print(f"🔗 API Calls Captured: {len(data['network_data'])}")
        
        # Print the extracted data
        print("\n--- Win Odds Trends Data ---")
        print(json.dumps(data, ensure_ascii=False, indent=2)[:2000] + "..." if len(json.dumps(data)) > 2000 else json.dumps(data, ensure_ascii=False, indent=2))
        print("---------------------------\n")
        
        # Save to JSON file
        json_file = save_win_odds_to_json(data, race_date, venue, race_number)
        
        if json_file:
            print(f"🎉 Win odds data saved successfully to {json_file}")
        else:
            print("❌ Failed to save win odds data to JSON file")
            
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
