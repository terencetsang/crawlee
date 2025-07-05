#!/usr/bin/env python3
"""
Use Playwright to get actual race dates from HKJC dropdown
"""
import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

async def get_hkjc_dropdown_with_playwright():
    """Use Playwright to get race dates from HKJC dropdown"""
    print("🔍 Using Playwright to get HKJC dropdown dates...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # Use headless mode
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='zh-HK'
        )
        
        page = await context.new_page()
        
        try:
            # Try the main betting page
            url = "https://bet.hkjc.com/ch/racing/pwin"
            print(f"   Loading: {url}")
            
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(5000)  # Wait for JavaScript to load
            
            # Look for date dropdown/select elements
            print("   Looking for date dropdowns...")
            
            # Method 1: Look for select elements
            selects = await page.query_selector_all('select')
            race_dates = []
            
            for select in selects:
                options = await select.query_selector_all('option')
                for option in options:
                    value = await option.get_attribute('value')
                    text = await option.text_content()
                    
                    print(f"      Option: value='{value}', text='{text}'")
                    
                    # Look for date patterns
                    if value and ('2025' in value or '2024' in value):
                        # Try to extract date
                        import re
                        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', value)
                        if date_match:
                            race_dates.append(date_match.group(1))
            
            # Method 2: Look for clickable date elements
            print("   Looking for clickable date elements...")
            
            # Look for elements that might contain dates
            date_elements = await page.query_selector_all('[data-date], .date, .race-date')
            for element in date_elements:
                text = await element.text_content()
                data_date = await element.get_attribute('data-date')
                
                if text:
                    print(f"      Date element text: '{text}'")
                if data_date:
                    print(f"      Date element data-date: '{data_date}'")
            
            # Method 3: Look in page content for date patterns
            print("   Scanning page content for dates...")
            page_content = await page.content()
            
            import re
            # Look for date patterns in the HTML
            date_patterns = [
                r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
                r'(\d{4}/\d{2}/\d{2})',  # YYYY/MM/DD
                r'(\d{2}/\d{2}/\d{4})',  # DD/MM/YYYY
            ]
            
            found_dates = set()
            for pattern in date_patterns:
                matches = re.findall(pattern, page_content)
                for match in matches:
                    try:
                        # Try to parse and standardize the date
                        if '-' in match:
                            date_obj = datetime.strptime(match, '%Y-%m-%d')
                        elif '/' in match and match.startswith('20'):
                            date_obj = datetime.strptime(match, '%Y/%m/%d')
                        elif '/' in match:
                            date_obj = datetime.strptime(match, '%d/%m/%Y')
                        else:
                            continue
                            
                        # Only include recent dates
                        today = datetime.now()
                        days_diff = (date_obj - today).days
                        if -30 <= days_diff <= 30:  # Within 30 days
                            standardized_date = date_obj.strftime('%Y-%m-%d')
                            found_dates.add(standardized_date)
                    except ValueError:
                        continue
            
            race_dates.extend(list(found_dates))
            race_dates = sorted(list(set(race_dates)))
            
            print(f"   Found {len(race_dates)} potential race dates")
            for date in race_dates:
                print(f"      - {date}")
            
            return race_dates
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            return []
            
        finally:
            await browser.close()

async def verify_race_dates(race_dates):
    """Verify which dates actually have race data"""
    print(f"\n🔍 Verifying {len(race_dates)} race dates...")
    
    verified_dates = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='zh-HK'
        )
        
        for race_date in race_dates:
            print(f"   Verifying {race_date}...")
            
            # Check both venues
            for venue in ['ST', 'HV']:
                page = await context.new_page()
                
                try:
                    url = f"https://bet.hkjc.com/ch/racing/pwin/{race_date}/{venue}/1"
                    await page.goto(url, wait_until='domcontentloaded', timeout=15000)
                    await page.wait_for_timeout(3000)
                    
                    # Check if this page has actual race content
                    page_text = await page.text_content('body')
                    
                    if "第1場" in page_text or "Race 1" in page_text:
                        # Verify the date in the content matches our request
                        date_formatted = race_date.replace('-', '/')
                        if date_formatted in page_text:
                            venue_name = "Sha Tin" if venue == "ST" else "Happy Valley"
                            verified_dates.append({
                                "race_date": race_date,
                                "venue": venue,
                                "venue_name": venue_name,
                                "url": url
                            })
                            print(f"      ✅ {race_date} {venue} ({venue_name}) - VERIFIED")
                            break  # Only one venue per date
                
                except Exception as e:
                    print(f"      ❌ {race_date} {venue} - Error: {str(e)}")
                
                finally:
                    await page.close()
        
        await browser.close()
    
    return verified_dates

async def main():
    """Main function"""
    print("🏇 HKJC Dropdown Race Dates with Playwright")
    print("=" * 50)
    
    # Get race dates from dropdown
    race_dates = await get_hkjc_dropdown_with_playwright()
    
    if not race_dates:
        print("❌ No race dates found in dropdown")
        return
    
    # Verify the dates
    verified_dates = await verify_race_dates(race_dates)
    
    if verified_dates:
        # Save results
        output = {
            "extracted_at": datetime.now().isoformat(),
            "source": "hkjc_dropdown_playwright",
            "total_dates": len(verified_dates),
            "race_dates": [item["race_date"] for item in verified_dates],
            "race_sessions": verified_dates
        }
        
        with open('hkjc_dropdown_verified.json', 'w') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n📊 Final Results:")
        print(f"   📅 Total verified race dates: {len(verified_dates)}")
        print(f"   💾 Saved to: hkjc_dropdown_verified.json")
        
        print(f"\n📋 Verified Race Schedule:")
        for session in verified_dates:
            print(f"   - {session['race_date']}: {session['venue']} ({session['venue_name']})")
        
        # Create simple list
        simple_dates = [item["race_date"] for item in verified_dates]
        with open('hkjc_dropdown_dates_simple.json', 'w') as f:
            json.dump(simple_dates, f, indent=2)
        
        print(f"   💾 Simple list: hkjc_dropdown_dates_simple.json")
    else:
        print("❌ No race dates could be verified")

if __name__ == "__main__":
    asyncio.run(main())
