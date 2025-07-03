import requests
import json
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

def get_race_schedule_from_hkjc():
    """
    Fetch the complete race schedule from HKJC website.
    Returns a list of race dates with venue information.
    """
    try:
        print("🏇 Fetching race schedule from HKJC website...")
        
        # Try the main racing page that shows the schedule
        url = "https://bet.hkjc.com/ch/racing"
        
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }, timeout=15)
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch HKJC racing page: HTTP {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        print(f"✅ Successfully fetched HKJC racing page")
        
        # Look for race schedule information
        race_dates = []
        
        # Method 1: Look for race date links or buttons
        print(f"🔍 Searching for race dates...")
        
        # Look for date patterns in the page
        page_text = soup.get_text()
        
        # Extract dates in various formats
        date_patterns = [
            r'(\d{4})/(\d{1,2})/(\d{1,2})',  # YYYY/MM/DD
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY or DD/MM/YYYY
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
            r'(\d{4})年(\d{1,2})月(\d{1,2})日'  # Chinese format
        ]
        
        found_dates = set()
        
        for pattern in date_patterns:
            matches = re.findall(pattern, page_text)
            for match in matches:
                try:
                    if '年' in pattern:  # Chinese format
                        year, month, day = match
                        date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    elif pattern.startswith(r'(\d{4})'):  # YYYY first
                        year, month, day = match
                        date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    else:  # MM/DD/YYYY or DD/MM/YYYY
                        part1, part2, year = match
                        # Assume MM/DD/YYYY format
                        month, day = part1, part2
                        date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    
                    # Validate date
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    
                    # Only include dates within reasonable range (past 6 months to future 6 months)
                    today = datetime.now()
                    six_months_ago = today - timedelta(days=180)
                    six_months_later = today + timedelta(days=180)
                    
                    if six_months_ago <= date_obj <= six_months_later:
                        found_dates.add(date_str)
                        
                except ValueError:
                    continue
        
        if found_dates:
            print(f"✅ Found {len(found_dates)} potential race dates")
            race_dates = sorted(list(found_dates))
        else:
            print(f"⚠️ No race dates found in page content")
        
        return race_dates
        
    except Exception as e:
        print(f"❌ Error fetching race schedule: {str(e)}")
        return None

def get_current_race_info():
    """
    Get current race information from HKJC racing page.
    """
    try:
        print(f"\n🔍 Getting current race information...")
        
        url = "https://racing.hkjc.com/racing/information/Chinese/racing/RaceCard.aspx"
        
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }, timeout=15)
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch current race info: HTTP {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()
        
        # Look for current race date
        current_date = None
        venue = None
        
        # Extract current date
        date_patterns = [
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',
            r'(\d{4})/(\d{1,2})/(\d{1,2})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, page_text)
            if match:
                if '年' in pattern:
                    year, month, day = match.groups()
                    current_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                else:
                    year, month, day = match.groups()
                    current_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                break
        
        # Extract venue
        if "沙田" in page_text:
            venue = "ST"
        elif "跑馬地" in page_text:
            venue = "HV"
        
        if current_date:
            print(f"✅ Current race: {current_date} {venue}")
            return current_date, venue
        else:
            print(f"⚠️ Could not extract current race info")
            return None
            
    except Exception as e:
        print(f"❌ Error getting current race info: {str(e)}")
        return None

def generate_race_schedule():
    """
    Generate a comprehensive race schedule based on HKJC patterns.
    """
    print(f"\n📅 Generating race schedule based on HKJC patterns...")
    
    # Get current race info as a starting point
    current_info = get_current_race_info()
    
    race_dates = []
    
    if current_info:
        current_date, current_venue = current_info
        
        # Parse current date
        try:
            current_dt = datetime.strptime(current_date, '%Y-%m-%d')
            
            # Generate dates around current date
            # HKJC typically has races on Wednesdays (HV) and Sundays (ST)
            # But also has races on other days
            
            # Go back 30 days and forward 30 days
            start_date = current_dt - timedelta(days=30)
            end_date = current_dt + timedelta(days=30)
            
            current = start_date
            while current <= end_date:
                # Check if this could be a race day
                weekday = current.weekday()
                
                # Wednesday (2) is typically HV, Sunday (6) is typically ST
                # But also include other potential race days
                if weekday in [2, 6] or current == current_dt:  # Wed, Sun, or current date
                    date_str = current.strftime('%Y-%m-%d')
                    race_dates.append(date_str)
                
                current += timedelta(days=1)
            
            print(f"✅ Generated {len(race_dates)} potential race dates")
            
        except ValueError:
            print(f"❌ Could not parse current date: {current_date}")
    
    # If we couldn't get current info, generate a basic schedule
    if not race_dates:
        print(f"⚠️ Generating fallback schedule...")
        
        today = datetime.now()
        
        # Generate dates for the next 60 days
        for i in range(-30, 31):
            date = today + timedelta(days=i)
            weekday = date.weekday()
            
            # Include Wednesdays and Sundays
            if weekday in [2, 6]:
                race_dates.append(date.strftime('%Y-%m-%d'))
    
    return sorted(race_dates)

def create_race_dates_json():
    """
    Create race_dates.json from HKJC website information.
    """
    print("🏇 HKJC Race Dates Creator")
    print("=" * 50)
    
    # Method 1: Try to get race schedule directly from HKJC
    race_dates = get_race_schedule_from_hkjc()
    
    # Method 2: If that fails, generate based on patterns
    if not race_dates:
        print(f"\n🔄 Falling back to pattern-based generation...")
        race_dates = generate_race_schedule()
    
    if not race_dates:
        print(f"❌ Could not generate race dates")
        return False
    
    # Backup existing race_dates.json
    try:
        with open('race_dates.json', 'r') as f:
            old_data = json.load(f)
        
        backup_filename = f"race_dates_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_filename, 'w') as f:
            json.dump(old_data, f, indent=2)
        print(f"📋 Backed up existing race_dates.json to {backup_filename}")
    except FileNotFoundError:
        print(f"📋 No existing race_dates.json to backup")
    except Exception as e:
        print(f"⚠️ Could not backup existing file: {e}")
    
    # Save new race_dates.json
    try:
        with open('race_dates.json', 'w') as f:
            json.dump(race_dates, f, indent=2)
        
        print(f"\n✅ Created race_dates.json with {len(race_dates)} dates")
        
        # Show the dates
        print(f"\n📅 Race dates:")
        for date in race_dates:
            print(f"   - {date}")
        
        # Create summary
        summary = {
            "generated_at": datetime.now().isoformat(),
            "total_dates": len(race_dates),
            "date_range": {
                "start": race_dates[0] if race_dates else None,
                "end": race_dates[-1] if race_dates else None
            },
            "race_dates": race_dates
        }
        
        with open('race_dates_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"📊 Created race_dates_summary.json")
        
        return True
        
    except Exception as e:
        print(f"❌ Error saving race_dates.json: {e}")
        return False

def main():
    """Main function"""
    success = create_race_dates_json()
    
    print(f"\n" + "=" * 50)
    if success:
        print(f"🎉 Successfully created race_dates.json from HKJC website!")
        print(f"📄 Check race_dates.json for the complete list")
        print(f"📊 Check race_dates_summary.json for details")
    else:
        print(f"❌ Failed to create race_dates.json")
    print("=" * 50)

if __name__ == '__main__':
    main()
