#!/usr/bin/env python3
"""
Direct check of HKJC website to find available race dates
"""
import requests
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

def check_hkjc_date_availability():
    """Check HKJC for available race dates by testing recent dates"""
    print("🔍 Checking HKJC for available race dates...")
    
    available_dates = []
    today = datetime.now()
    
    # Check last 10 days and next 3 days
    for i in range(-10, 4):
        check_date = today + timedelta(days=i)
        date_str = check_date.strftime("%Y-%m-%d")
        
        print(f"   Testing {date_str}...")
        
        # Check both venues
        for venue in ['ST', 'HV']:
            url = f"https://bet.hkjc.com/ch/racing/pwin/{date_str}/{venue}/1"
            
            try:
                response = requests.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }, timeout=10)
                
                if response.status_code == 200:
                    # Check if this is actual race data or a redirect
                    soup = BeautifulSoup(response.text, 'html.parser')
                    page_text = soup.get_text()
                    
                    # Look for race-specific content
                    if "第1場" in page_text or "Race 1" in page_text:
                        # Verify the date in the content matches our request
                        date_formatted = date_str.replace('-', '/')
                        date_chinese_year = date_str[:4] + '年'
                        
                        if date_formatted in page_text or date_chinese_year in page_text:
                            venue_name = "Sha Tin" if venue == "ST" else "Happy Valley"
                            available_dates.append({
                                "race_date": date_str,
                                "venue": venue,
                                "venue_name": venue_name,
                                "url": url,
                                "verified": True
                            })
                            print(f"      ✅ {date_str} {venue} ({venue_name}) - CONFIRMED")
                            break  # Only one venue per date
                        else:
                            print(f"      🔄 {date_str} {venue} - Redirected (different date in content)")
                    else:
                        print(f"      ❌ {date_str} {venue} - No race content")
                else:
                    print(f"      ❌ {date_str} {venue} - HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"      ❌ {date_str} {venue} - Error: {str(e)}")
    
    return available_dates

def save_results(available_dates):
    """Save the results to JSON file"""
    if not available_dates:
        print("❌ No available dates found")
        return
    
    # Create output structure
    output = {
        "extracted_at": datetime.now().isoformat(),
        "source": "hkjc_direct_verification",
        "method": "url_testing_with_content_verification",
        "total_dates": len(available_dates),
        "race_dates": [item["race_date"] for item in available_dates],
        "race_sessions": available_dates
    }
    
    # Save to file
    with open('hkjc_verified_dates.json', 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 Results Summary:")
    print(f"   📅 Total verified race dates: {len(available_dates)}")
    print(f"   💾 Saved to: hkjc_verified_dates.json")
    
    print(f"\n📋 Verified Race Schedule:")
    for session in available_dates:
        print(f"   - {session['race_date']}: {session['venue']} ({session['venue_name']})")
    
    # Also create a simple list for easy use
    simple_dates = [item["race_date"] for item in available_dates]
    with open('hkjc_race_dates_simple.json', 'w') as f:
        json.dump(simple_dates, f, indent=2)
    
    print(f"   💾 Simple list saved to: hkjc_race_dates_simple.json")

def main():
    """Main function"""
    print("🏇 HKJC Direct Race Date Verification")
    print("=" * 50)
    
    available_dates = check_hkjc_date_availability()
    save_results(available_dates)
    
    if available_dates:
        print(f"\n✅ Found {len(available_dates)} verified race dates")
        print("🎯 These are the authoritative race dates from HKJC website")
    else:
        print("\n❌ No race dates could be verified")

if __name__ == "__main__":
    main()
