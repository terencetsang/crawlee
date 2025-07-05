#!/usr/bin/env python3
"""
Extract actual race dates from HKJC website dropdown options.
This provides the authoritative source of available race dates.
"""
import requests
import json
import re
from datetime import datetime
from bs4 import BeautifulSoup

def get_hkjc_dropdown_dates():
    """Extract race dates from HKJC website dropdown"""
    try:
        print("🔍 Fetching race dates from HKJC website dropdown...")
        
        # Try the main betting page that has the date dropdown
        urls_to_try = [
            "https://bet.hkjc.com/ch/racing/pwin",
            "https://bet.hkjc.com/ch/racing",
            "https://racing.hkjc.com/racing/information/Chinese/racing/RaceCard.aspx"
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-HK,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        for url in urls_to_try:
            try:
                print(f"   Trying: {url}")
                response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Look for dropdown options with dates
                    race_dates = []
                    
                    # Method 1: Look for select/option elements
                    selects = soup.find_all('select')
                    for select in selects:
                        options = select.find_all('option')
                        for option in options:
                            value = option.get('value', '')
                            text = option.get_text().strip()
                            
                            # Look for date patterns in value or text
                            date_patterns = [
                                r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
                                r'(\d{4}/\d{2}/\d{2})',  # YYYY/MM/DD
                                r'(\d{2}/\d{2}/\d{4})',  # DD/MM/YYYY
                            ]
                            
                            for pattern in date_patterns:
                                matches = re.findall(pattern, value + ' ' + text)
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
                                            
                                        standardized_date = date_obj.strftime('%Y-%m-%d')
                                        if standardized_date not in race_dates:
                                            race_dates.append(standardized_date)
                                    except ValueError:
                                        continue
                    
                    # Method 2: Look for JavaScript data or embedded JSON
                    scripts = soup.find_all('script')
                    for script in scripts:
                        if script.string:
                            # Look for date arrays or objects in JavaScript
                            js_content = script.string
                            
                            # Look for date patterns in JavaScript
                            date_matches = re.findall(r'["\'](\d{4}-\d{2}-\d{2})["\']', js_content)
                            for match in date_matches:
                                try:
                                    datetime.strptime(match, '%Y-%m-%d')
                                    if match not in race_dates:
                                        race_dates.append(match)
                                except ValueError:
                                    continue
                    
                    # Method 3: Look for links with date patterns
                    links = soup.find_all('a', href=True)
                    for link in links:
                        href = link.get('href', '')
                        # Look for URLs with date patterns
                        date_matches = re.findall(r'/(\d{4}-\d{2}-\d{2})/', href)
                        for match in date_matches:
                            try:
                                datetime.strptime(match, '%Y-%m-%d')
                                if match not in race_dates:
                                    race_dates.append(match)
                            except ValueError:
                                continue
                    
                    if race_dates:
                        # Sort and filter dates
                        race_dates = sorted(list(set(race_dates)))
                        
                        # Filter to reasonable date range (last 3 months to next month)
                        today = datetime.now()
                        filtered_dates = []
                        
                        for date_str in race_dates:
                            try:
                                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                                # Keep dates within reasonable range
                                days_diff = (date_obj - today).days
                                if -90 <= days_diff <= 30:  # 3 months back to 1 month forward
                                    filtered_dates.append(date_str)
                            except ValueError:
                                continue
                        
                        if filtered_dates:
                            print(f"   ✅ Found {len(filtered_dates)} race dates from {url}")
                            return filtered_dates
                
            except Exception as e:
                print(f"   ❌ Error with {url}: {str(e)}")
                continue
        
        print("   ⚠️ No race dates found in any URL")
        return []
        
    except Exception as e:
        print(f"❌ Error fetching dropdown dates: {str(e)}")
        return []

def get_hkjc_venue_info(race_date):
    """Get venue information for a specific race date from HKJC"""
    try:
        # Try both venues to see which one has data
        for venue in ['ST', 'HV']:
            url = f"https://bet.hkjc.com/ch/racing/pwin/{race_date}/{venue}/1"
            
            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }, timeout=10, allow_redirects=False)
            
            # If we don't get redirected, this venue likely has data
            if response.status_code == 200:
                # Check if the content actually contains race data
                if "You need to enable JavaScript" in response.text:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    page_text = soup.get_text()
                    
                    # Check if the requested date appears in the content
                    date_formatted = race_date.replace('-', '/')
                    if date_formatted in page_text:
                        return venue
        
        return None
        
    except Exception as e:
        print(f"   ❌ Error checking venue for {race_date}: {str(e)}")
        return None

def main():
    """Main function to get and display HKJC dropdown dates"""
    print("🏇 HKJC Dropdown Race Dates Extractor")
    print("=" * 50)
    
    # Get race dates from dropdown
    race_dates = get_hkjc_dropdown_dates()
    
    if not race_dates:
        print("❌ No race dates found")
        return
    
    print(f"\n✅ Found {len(race_dates)} race dates from HKJC dropdown:")
    
    # Get venue information for each date
    race_sessions = []
    for race_date in race_dates:
        print(f"\n📅 Checking {race_date}...")
        venue = get_hkjc_venue_info(race_date)
        
        if venue:
            venue_name = "Sha Tin" if venue == "ST" else "Happy Valley"
            race_sessions.append({
                "race_date": race_date,
                "venue": venue,
                "venue_name": venue_name
            })
            print(f"   ✅ {race_date}: {venue} ({venue_name})")
        else:
            print(f"   ❌ {race_date}: No venue data found")
    
    # Save results
    output = {
        "extracted_at": datetime.now().isoformat(),
        "source": "hkjc_website_dropdown",
        "total_dates": len(race_sessions),
        "race_dates": [session["race_date"] for session in race_sessions],
        "race_sessions": race_sessions
    }
    
    with open('hkjc_dropdown_dates.json', 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 Summary:")
    print(f"   📅 Total race dates: {len(race_sessions)}")
    print(f"   💾 Saved to: hkjc_dropdown_dates.json")
    
    print(f"\n📋 Race Schedule:")
    for session in race_sessions:
        print(f"   - {session['race_date']}: {session['venue']} ({session['venue_name']})")

if __name__ == "__main__":
    main()
