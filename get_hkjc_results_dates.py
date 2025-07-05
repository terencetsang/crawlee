#!/usr/bin/env python3
"""
Extract race dates from HKJC Local Results pages - the authoritative source
"""
import requests
import json
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

def get_current_race_info():
    """Get current race information from HKJC Local Results page"""
    try:
        print("🔍 Getting current race info from HKJC Local Results...")
        
        url = "https://racing.hkjc.com/racing/information/Chinese/racing/LocalResults.aspx"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-HK,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()
            
            print(f"   ✅ Successfully loaded current race results page")
            
            # Extract race date and venue information
            race_date = None
            venue = None
            
            # Look for date patterns in Chinese format
            date_patterns = [
                r'(\d{4})年(\d{1,2})月(\d{1,2})日.*?(沙田|跑馬地)',
                r'(\d{4})/(\d{1,2})/(\d{1,2}).*?(沙田|跑馬地)',
                r'(\d{1,2})/(\d{1,2})/(\d{4}).*?(沙田|跑馬地)'
            ]
            
            for pattern in date_patterns:
                matches = re.findall(pattern, page_text)
                for match in matches:
                    try:
                        if len(match) == 4:
                            if pattern.startswith(r'(\d{4})年'):
                                # YYYY年MM月DD日 format
                                year, month, day, venue_chinese = match
                                race_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                            elif pattern.startswith(r'(\d{4})/'):
                                # YYYY/MM/DD format
                                year, month, day, venue_chinese = match
                                race_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                            elif pattern.startswith(r'(\d{1,2})/'):
                                # DD/MM/YYYY format
                                day, month, year, venue_chinese = match
                                race_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                            
                            venue = "ST" if venue_chinese == "沙田" else "HV"
                            
                            print(f"   📅 Found current race: {race_date} at {venue_chinese} ({venue})")
                            return race_date, venue
                    except Exception as e:
                        continue
            
            # If no specific pattern found, look for any date in the page
            general_date_patterns = [
                r'(\d{4})-(\d{2})-(\d{2})',
                r'(\d{4})/(\d{2})/(\d{2})',
                r'(\d{2})/(\d{2})/(\d{4})'
            ]
            
            for pattern in general_date_patterns:
                matches = re.findall(pattern, page_text)
                for match in matches:
                    try:
                        if pattern.startswith(r'(\d{4})-'):
                            year, month, day = match
                            race_date = f"{year}-{month}-{day}"
                        elif pattern.startswith(r'(\d{4})/'):
                            year, month, day = match
                            race_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                        elif pattern.startswith(r'(\d{2})/'):
                            day, month, year = match
                            race_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                        
                        # Validate date is reasonable (within last 30 days)
                        date_obj = datetime.strptime(race_date, '%Y-%m-%d')
                        today = datetime.now()
                        if abs((date_obj - today).days) <= 30:
                            print(f"   📅 Found potential current race date: {race_date}")
                            return race_date, None  # Venue to be determined later
                    except Exception as e:
                        continue
            
            print("   ⚠️ Could not extract race date from current results page")
            return None, None
            
        else:
            print(f"   ❌ Failed to load current results page: HTTP {response.status_code}")
            return None, None
            
    except Exception as e:
        print(f"   ❌ Error getting current race info: {str(e)}")
        return None, None

def verify_race_date(race_date):
    """Verify a specific race date using the LocalResults URL format"""
    try:
        print(f"   🔍 Verifying {race_date}...")
        
        # Format date for URL (YYYY/MM/DD)
        date_formatted = race_date.replace('-', '/')
        url = f"https://racing.hkjc.com/racing/information/Chinese/Racing/LocalResults.aspx?RaceDate={date_formatted}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-HK,zh;q=0.9,en;q=0.8'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()
            
            # Check if this page has actual race results
            if "第1場" in page_text or "Race 1" in page_text or "第 1 場" in page_text:
                # Extract venue information
                venue = None
                if "沙田" in page_text:
                    venue = "ST"
                elif "跑馬地" in page_text:
                    venue = "HV"
                
                # Count total races
                race_count = 0
                race_patterns = [
                    r'第(\d+)場',
                    r'第 (\d+) 場',
                    r'Race (\d+)'
                ]
                
                max_race = 0
                for pattern in race_patterns:
                    matches = re.findall(pattern, page_text)
                    for match in matches:
                        try:
                            race_num = int(match)
                            max_race = max(max_race, race_num)
                        except:
                            continue
                
                race_count = max_race if max_race > 0 else 10  # Default to 10 if can't determine
                
                venue_name = "Sha Tin" if venue == "ST" else "Happy Valley" if venue == "HV" else "Unknown"
                print(f"      ✅ {race_date}: {venue} ({venue_name}) - {race_count} races")
                
                return {
                    "race_date": race_date,
                    "venue": venue,
                    "venue_name": venue_name,
                    "total_races": race_count,
                    "url": url,
                    "verified": True
                }
            else:
                print(f"      ❌ {race_date}: No race results found")
                return None
        else:
            print(f"      ❌ {race_date}: HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"      ❌ {race_date}: Error - {str(e)}")
        return None

def get_all_race_dates_from_schedule():
    """Get ALL race dates from HKJC schedule (past + upcoming)"""
    print("\n🔍 Getting complete race schedule (past + upcoming)...")

    all_races = []
    today = datetime.now()

    # Check wider range: last 30 days + next 30 days
    for i in range(-30, 31):
        check_date = today + timedelta(days=i)
        date_str = check_date.strftime("%Y-%m-%d")

        race_info = verify_race_date(date_str)
        if race_info:
            all_races.append(race_info)

    return all_races

def main():
    """Main function to get complete race schedule from HKJC Local Results"""
    print("🏇 HKJC Complete Race Schedule Extractor")
    print("=" * 60)
    print("📋 Strategy:")
    print("   1. Get ALL race dates (past + upcoming) from Local Results pages")
    print("   2. These dates will be used to check odds trends availability")
    print("📋 Sources:")
    print("   1. Current: racing.hkjc.com/racing/information/Chinese/racing/LocalResults.aspx")
    print("   2. Specific: racing.hkjc.com/racing/information/Chinese/Racing/LocalResults.aspx?RaceDate=YYYY/MM/DD")
    print("=" * 60)
    
    # Step 1: Get current race information
    current_date, current_venue = get_current_race_info()
    
    # Step 2: Get complete race schedule (past + upcoming)
    verified_races = get_all_race_dates_from_schedule()
    
    # Step 3: Add current race if not already in the list
    if current_date and current_venue:
        # Check if current race is already in verified list
        current_found = False
        for race in verified_races:
            if race["race_date"] == current_date:
                current_found = True
                break
        
        if not current_found:
            # Verify current race
            current_race_info = verify_race_date(current_date)
            if current_race_info:
                verified_races.append(current_race_info)
    
    # Step 4: Sort by date (newest first)
    verified_races.sort(key=lambda x: x["race_date"], reverse=True)
    
    # Step 5: Save results
    if verified_races:
        output = {
            "extracted_at": datetime.now().isoformat(),
            "source": "hkjc_local_results_authoritative",
            "method": "local_results_verification",
            "total_dates": len(verified_races),
            "race_dates": [race["race_date"] for race in verified_races],
            "race_sessions": verified_races
        }
        
        with open('hkjc_authoritative_dates.json', 'w') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        # Create simple list for easy use
        simple_dates = [race["race_date"] for race in verified_races]
        with open('hkjc_authoritative_dates_simple.json', 'w') as f:
            json.dump(simple_dates, f, indent=2)
        
        print(f"\n📊 Final Results:")
        print(f"   📅 Total verified race dates: {len(verified_races)}")
        print(f"   💾 Saved to: hkjc_authoritative_dates.json")
        print(f"   💾 Simple list: hkjc_authoritative_dates_simple.json")
        
        print(f"\n📋 Authoritative Race Schedule:")
        for race in verified_races:
            print(f"   - {race['race_date']}: {race['venue']} ({race['venue_name']}) - {race['total_races']} races")
        
        print(f"\n✅ Successfully extracted {len(verified_races)} authoritative race dates")
        print("🎯 These dates are verified from HKJC Local Results pages")
        
    else:
        print("\n❌ No race dates could be verified from Local Results")

if __name__ == "__main__":
    main()
