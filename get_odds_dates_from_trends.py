#!/usr/bin/env python3
"""
Get race dates directly from odds trends pages - the correct approach
"""
import requests
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

def test_odds_trends_date(race_date, venue):
    """Test if a specific date/venue has odds trends data available"""
    try:
        url = f"https://bet.hkjc.com/ch/racing/pwin/{race_date}/{venue}/1"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-HK,zh;q=0.9,en;q=0.8'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Check if we got redirected (different date in final URL)
            final_url = response.url
            if race_date not in final_url:
                return False, f"redirected_to_{final_url}"
            
            # Check content for odds data indicators
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()
            
            # Look for odds-specific content
            odds_indicators = [
                "賠率", "Odds", "投注", "Betting",
                "獨贏", "Win", "位置", "Place",
                "連贏", "Quinella"
            ]
            
            has_odds = any(indicator in page_text for indicator in odds_indicators)
            
            # Additional check: verify date appears in content
            date_formatted = race_date.replace('-', '/')
            date_in_content = date_formatted in page_text
            
            if has_odds and date_in_content:
                # Count races by checking multiple race URLs
                race_count = count_races_for_date(race_date, venue)
                return True, race_count
            else:
                return False, "no_odds_content"
        else:
            return False, f"http_{response.status_code}"
            
    except Exception as e:
        return False, f"error_{str(e)}"

def count_races_for_date(race_date, venue):
    """Count how many races are available for a specific date/venue"""
    race_count = 0
    
    # Test up to 15 races (typical maximum)
    for race_num in range(1, 16):
        try:
            url = f"https://bet.hkjc.com/ch/racing/pwin/{race_date}/{venue}/{race_num}"
            
            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }, timeout=5)
            
            if response.status_code == 200 and race_date in response.url:
                # Quick check for race content
                if f"第{race_num}場" in response.text or f"Race {race_num}" in response.text:
                    race_count = race_num
                else:
                    break  # No more races
            else:
                break  # Error or redirect
                
        except:
            break  # Error, stop counting
    
    return race_count if race_count > 0 else 12  # Default to 12 if counting fails

def scan_odds_trends_for_dates():
    """Scan odds trends pages to find available race dates"""
    print("🔍 Scanning odds trends pages for available race dates...")
    
    available_dates = []
    today = datetime.now()
    
    # Scan reasonable range: 30 days back to 7 days forward
    for i in range(-30, 8):
        check_date = today + timedelta(days=i)
        date_str = check_date.strftime("%Y-%m-%d")
        
        print(f"   Testing {date_str}...")
        
        # Test both venues (but expect only one to work per date)
        found_venue = None
        
        for venue in ['ST', 'HV']:
            has_odds, result = test_odds_trends_date(date_str, venue)
            
            if has_odds:
                venue_name = "Sha Tin" if venue == "ST" else "Happy Valley"
                race_count = result if isinstance(result, int) else 12
                
                available_dates.append({
                    "race_date": date_str,
                    "venue": venue,
                    "venue_name": venue_name,
                    "total_races": race_count,
                    "source": "odds_trends",
                    "url": f"https://bet.hkjc.com/ch/racing/pwin/{date_str}/{venue}/1"
                })
                
                found_venue = venue
                print(f"      ✅ {date_str} {venue} ({venue_name}): {race_count} races")
                break  # Only one venue per date
            else:
                print(f"      ❌ {date_str} {venue}: {result}")
        
        if not found_venue:
            print(f"      ❌ {date_str}: No odds data at any venue")
    
    return available_dates

def main():
    """Main function to get race dates from odds trends pages"""
    print("🏇 Odds Trends Race Date Scanner")
    print("=" * 50)
    print("📋 Strategy:")
    print("   1. Test odds trends URLs directly")
    print("   2. Find dates with actual odds data")
    print("   3. Count races for each valid date")
    print("=" * 50)
    
    # Scan for available dates
    available_dates = scan_odds_trends_for_dates()
    
    if available_dates:
        # Sort by date
        available_dates.sort(key=lambda x: x['race_date'])
        
        # Save results
        output = {
            "extracted_at": datetime.now().isoformat(),
            "source": "odds_trends_direct_scan",
            "method": "url_testing_with_race_counting",
            "total_dates": len(available_dates),
            "race_dates": [item["race_date"] for item in available_dates],
            "race_sessions": available_dates
        }
        
        with open('odds_trends_race_dates.json', 'w') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        # Create simple list
        simple_dates = [item["race_date"] for item in available_dates]
        with open('odds_trends_dates_simple.json', 'w') as f:
            json.dump(simple_dates, f, indent=2)
        
        print(f"\n📊 Results:")
        print(f"   📅 Total dates with odds: {len(available_dates)}")
        print(f"   💾 Detailed results: odds_trends_race_dates.json")
        print(f"   💾 Simple list: odds_trends_dates_simple.json")
        
        print(f"\n📋 Race Dates from Odds Trends:")
        for item in available_dates:
            print(f"   - {item['race_date']}: {item['venue']} ({item['venue_name']}) - {item['total_races']} races")
        
        print(f"\n✅ Found {len(available_dates)} dates with odds trends data")
        print("🎯 These are the definitive dates for odds extraction")
        
        return available_dates
        
    else:
        print("\n❌ No dates with odds trends found")
        return []

if __name__ == "__main__":
    main()
