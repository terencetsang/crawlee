#!/usr/bin/env python3
"""
Check which race dates have odds trends data available
This is the definitive test for which dates can be processed for odds extraction
"""
import requests
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

def check_odds_trends_availability(race_date, venue):
    """Check if odds trends data is available for a specific race date and venue"""
    try:
        # Format: https://bet.hkjc.com/ch/racing/pwin/YYYY-MM-DD/VENUE/RACE_NUMBER
        url = f"https://bet.hkjc.com/ch/racing/pwin/{race_date}/{venue}/1"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-HK,zh;q=0.9,en;q=0.8'
        }
        
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()
            
            # Check if this page has actual odds data
            odds_indicators = [
                "賠率", "Odds", "投注", "Betting",
                "第1場", "Race 1", "第 1 場",
                "獨贏", "Win", "位置", "Place"
            ]
            
            has_odds_content = any(indicator in page_text for indicator in odds_indicators)
            
            if has_odds_content:
                # Additional verification: check if the date in URL matches content
                date_formatted = race_date.replace('-', '/')
                date_in_content = date_formatted in page_text
                
                # Check for redirect by comparing requested URL with final URL
                final_url = response.url
                requested_date_in_final = race_date in final_url
                
                if date_in_content and requested_date_in_final:
                    # Count total races available
                    race_count = count_available_races(race_date, venue)
                    return {
                        "race_date": race_date,
                        "venue": venue,
                        "has_odds": True,
                        "total_races": race_count,
                        "url": url,
                        "final_url": final_url
                    }
                else:
                    return {
                        "race_date": race_date,
                        "venue": venue,
                        "has_odds": False,
                        "reason": "redirected_or_date_mismatch",
                        "url": url,
                        "final_url": final_url
                    }
            else:
                return {
                    "race_date": race_date,
                    "venue": venue,
                    "has_odds": False,
                    "reason": "no_odds_content",
                    "url": url
                }
        else:
            return {
                "race_date": race_date,
                "venue": venue,
                "has_odds": False,
                "reason": f"http_error_{response.status_code}",
                "url": url
            }
            
    except Exception as e:
        return {
            "race_date": race_date,
            "venue": venue,
            "has_odds": False,
            "reason": f"error_{str(e)}",
            "url": url if 'url' in locals() else None
        }

def count_available_races(race_date, venue):
    """Count how many races are available for a given date/venue"""
    try:
        race_count = 0
        
        # Check up to 15 races (typical maximum)
        for race_num in range(1, 16):
            url = f"https://bet.hkjc.com/ch/racing/pwin/{race_date}/{venue}/{race_num}"
            
            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }, timeout=5)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                page_text = soup.get_text()
                
                # Check if this race has odds data
                if f"第{race_num}場" in page_text or f"Race {race_num}" in page_text:
                    # Verify it's not a redirect by checking the date
                    date_formatted = race_date.replace('-', '/')
                    if date_formatted in page_text and race_date in response.url:
                        race_count = race_num
                    else:
                        break  # Redirected, stop counting
                else:
                    break  # No more races
            else:
                break  # Error, stop counting
        
        return race_count
        
    except Exception as e:
        print(f"      Error counting races for {race_date} {venue}: {e}")
        return 0

def scan_for_odds_availability():
    """Scan a range of dates to find which ones have odds data available"""
    print("🔍 Scanning for odds trends availability...")
    
    available_odds = []
    today = datetime.now()
    
    # Scan wider range: 60 days back to 30 days forward
    for i in range(-60, 31):
        check_date = today + timedelta(days=i)
        date_str = check_date.strftime("%Y-%m-%d")
        
        print(f"   Checking {date_str}...")
        
        # Check both venues
        for venue in ['ST', 'HV']:
            result = check_odds_trends_availability(date_str, venue)
            
            if result['has_odds']:
                venue_name = "Sha Tin" if venue == "ST" else "Happy Valley"
                available_odds.append(result)
                print(f"      ✅ {date_str} {venue} ({venue_name}): {result['total_races']} races with odds")
                break  # Only one venue per date
            else:
                print(f"      ❌ {date_str} {venue}: {result.get('reason', 'no_odds')}")
    
    return available_odds

def main():
    """Main function to scan for odds availability"""
    print("🏇 HKJC Odds Trends Availability Scanner")
    print("=" * 60)
    print("📋 Strategy:")
    print("   1. Test odds trends URLs directly")
    print("   2. Find dates with actual odds data available")
    print("   3. These are the dates that can be processed for extraction")
    print("=" * 60)
    
    # Scan for available odds
    available_odds = scan_for_odds_availability()
    
    if available_odds:
        # Sort by date
        available_odds.sort(key=lambda x: x['race_date'])
        
        # Save results
        output = {
            "scanned_at": datetime.now().isoformat(),
            "source": "odds_trends_direct_testing",
            "method": "url_testing_with_content_verification",
            "total_dates_with_odds": len(available_odds),
            "race_dates_with_odds": [item["race_date"] for item in available_odds],
            "odds_availability": available_odds
        }
        
        with open('odds_trends_availability.json', 'w') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        # Create simple list for easy use
        simple_dates = [item["race_date"] for item in available_odds]
        with open('odds_available_dates.json', 'w') as f:
            json.dump(simple_dates, f, indent=2)
        
        print(f"\n📊 Results:")
        print(f"   📅 Total dates with odds: {len(available_odds)}")
        print(f"   💾 Detailed results: odds_trends_availability.json")
        print(f"   💾 Simple list: odds_available_dates.json")
        
        print(f"\n📋 Dates with Odds Trends Available:")
        for item in available_odds:
            venue_name = "Sha Tin" if item['venue'] == "ST" else "Happy Valley"
            print(f"   - {item['race_date']}: {item['venue']} ({venue_name}) - {item['total_races']} races")
        
        print(f"\n✅ Found {len(available_odds)} dates with odds trends data")
        print("🎯 These are the definitive dates for odds extraction")
        
    else:
        print("\n❌ No dates with odds trends found")

if __name__ == "__main__":
    main()
