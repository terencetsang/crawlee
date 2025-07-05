#!/usr/bin/env python3
"""
Update odds_dates.json with authoritative race dates from HKJC Local Results
"""
import json
from datetime import datetime
from extract_all_odds_data import get_available_race_dates

def update_odds_dates_with_authoritative_data():
    """Update odds_dates.json with corrected authoritative data"""
    print("🔄 Updating odds_dates.json with authoritative HKJC data...")
    print("=" * 60)
    
    # Get the corrected race dates
    available_races = get_available_race_dates()
    
    if not available_races:
        print("❌ No race dates found")
        return False
    
    # Extract just the dates for the simple JSON format
    corrected_dates = [race[0] for race in available_races]  # race[0] is the date
    corrected_dates.sort()  # Sort chronologically
    
    # Backup existing odds_dates.json
    try:
        if os.path.exists('odds_dates.json'):
            with open('odds_dates.json', 'r') as f:
                old_data = json.load(f)
            
            with open('odds_dates_backup.json', 'w') as f:
                json.dump(old_data, f, indent=2)
            print("📋 Backed up existing odds_dates.json to odds_dates_backup.json")
    except Exception as e:
        print(f"⚠️ Could not backup existing file: {e}")
    
    # Create new odds_dates.json
    try:
        with open('odds_dates.json', 'w') as f:
            json.dump(corrected_dates, f, indent=2)
        
        print(f"✅ Updated odds_dates.json with {len(corrected_dates)} corrected dates")
        
        # Show the corrected dates
        print(f"\n📅 Corrected odds dates:")
        for date in corrected_dates:
            print(f"   - {date}")
        
        # Create detailed summary
        race_sessions_detail = []
        for race_date, venue, total_races in available_races:
            venue_name = "Sha Tin" if venue == "ST" else "Happy Valley"
            race_sessions_detail.append({
                "race_date": race_date,
                "venue": venue,
                "venue_name": venue_name,
                "total_races": total_races
            })
        
        summary = {
            "updated_at": datetime.now().isoformat(),
            "source": "hkjc_local_results_authoritative",
            "total_dates": len(corrected_dates),
            "date_range": {
                "start": corrected_dates[0] if corrected_dates else None,
                "end": corrected_dates[-1] if corrected_dates else None
            },
            "corrected_odds_dates": corrected_dates,
            "race_sessions": race_sessions_detail
        }
        
        with open('odds_dates_corrected_summary.json', 'w') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Created detailed summary: odds_dates_corrected_summary.json")
        
        # Show race sessions breakdown
        print(f"\n🏇 Race sessions breakdown:")
        for session in race_sessions_detail:
            print(f"   - {session['race_date']}: {session['venue']} ({session['venue_name']}) - {session['total_races']} races")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating odds_dates.json: {e}")
        return False

def main():
    """Main function"""
    print("🏇 Odds Dates Corrector")
    print("📋 Using authoritative HKJC Local Results data")
    print("=" * 60)
    
    success = update_odds_dates_with_authoritative_data()
    
    if success:
        print(f"\n✅ Successfully updated odds_dates.json with authoritative data")
        print("🎯 The extraction script will now use correct race dates and venues")
        print("📝 Key improvements:")
        print("   - Only completed races with actual results")
        print("   - Correct venue assignments (one per date)")
        print("   - No upcoming/future dates")
        print("   - Verified from HKJC Local Results pages")
    else:
        print(f"\n❌ Failed to update odds_dates.json")

if __name__ == "__main__":
    import os
    main()
