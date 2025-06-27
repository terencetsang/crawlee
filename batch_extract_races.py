#!/usr/bin/env python3
"""
Batch extract HKJC race data based on race_dates.json
"""

import json
import subprocess
import time
import argparse
from datetime import datetime

def load_race_dates(filename='race_dates.json'):
    """Load race dates from JSON file."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('race_dates', [])
    except Exception as e:
        print(f"❌ Error loading {filename}: {e}")
        print(f"💡 Run 'python extract_race_dates_to_json.py' first to create {filename}")
        return []

def filter_dates_by_criteria(race_dates, status=None, month=None, limit=None):
    """Filter race dates by various criteria."""
    filtered = race_dates
    
    # Filter by status
    if status:
        filtered = [d for d in filtered if d.get('status') == status]
    
    # Filter by month (YYYY/MM format)
    if month:
        filtered = [d for d in filtered if d.get('race_date', '').startswith(month)]
    
    # Apply limit
    if limit:
        filtered = filtered[-limit:]  # Get most recent dates
    
    return filtered

def extract_race_data(race_date, date_metadata, racecourses=['ST', 'HV'], delay=2):
    """Extract race data for a specific date using metadata."""
    print(f"\n📅 Processing {race_date}...")

    # Get metadata for this date
    racecourse_from_metadata = date_metadata.get('racecourse')
    total_races = date_metadata.get('total_races', 0)

    print(f"  📊 Metadata: {racecourse_from_metadata}, {total_races} races")

    # Skip if no racing
    if racecourse_from_metadata == 'NO_RACING' or total_races == 0:
        print(f"  ⚪ No racing scheduled for {race_date}")
        return 0

    success_count = 0

    # Only extract for the racecourse that has racing
    if racecourse_from_metadata in racecourses:
        try:
            print(f"  🏇 Extracting {racecourse_from_metadata} races (1-{total_races})...")

            # Create race range based on metadata
            race_range = f"1-{total_races}"

            # Run the scraper with specific race range
            cmd = ['python', 'hkjc_race_results_scraper.py', race_date, racecourse_from_metadata, race_range]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                print(f"    ✅ {racecourse_from_metadata} extraction successful")
                success_count += 1
            else:
                print(f"    ⚠️  {racecourse_from_metadata} extraction failed")
                if result.stderr:
                    print(f"    Error: {result.stderr.strip()}")

        except subprocess.TimeoutExpired:
            print(f"    ⏰ {racecourse_from_metadata} extraction timed out")
        except Exception as e:
            print(f"    ❌ {racecourse_from_metadata} extraction error: {e}")
    else:
        print(f"  ⚠️  Racecourse {racecourse_from_metadata} not in extraction list {racecourses}")

    # Add delay between dates
    if delay > 0:
        time.sleep(delay)

    return success_count

def main():
    parser = argparse.ArgumentParser(
        description='Batch extract HKJC race data based on race_dates.json',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python batch_extract_races.py --status completed --limit 5
  python batch_extract_races.py --month 2025/06
  python batch_extract_races.py --status completed --month 2025/06 --delay 3
        """
    )
    
    parser.add_argument('--status', choices=['completed', 'today', 'upcoming'],
                       help='Filter by race status')
    parser.add_argument('--month', help='Filter by month (YYYY/MM format)')
    parser.add_argument('--limit', type=int, help='Limit number of dates to process')
    parser.add_argument('--delay', type=float, default=2.0,
                       help='Delay between dates in seconds (default: 2.0)')
    parser.add_argument('--racecourses', nargs='+', default=['ST', 'HV'],
                       help='Racecourses to extract (default: ST HV)')
    
    args = parser.parse_args()
    
    print("HKJC Batch Race Data Extractor")
    print("=" * 40)
    
    # Load race dates
    race_dates = load_race_dates()
    if not race_dates:
        print("❌ No race dates found")
        return
    
    print(f"📋 Loaded {len(race_dates)} total race dates")
    
    # Filter dates
    filtered_dates = filter_dates_by_criteria(
        race_dates, 
        status=args.status, 
        month=args.month, 
        limit=args.limit
    )
    
    if not filtered_dates:
        print("❌ No dates match the specified criteria")
        return
    
    print(f"🎯 Selected {len(filtered_dates)} dates for extraction")
    print(f"📅 Date range: {filtered_dates[0]['race_date']} to {filtered_dates[-1]['race_date']}")
    print(f"🏇 Racecourses: {', '.join(args.racecourses)}")
    print(f"⏱️  Delay between dates: {args.delay}s")
    
    # Confirm before proceeding
    response = input(f"\n🚀 Proceed with extraction? (y/N): ")
    if response.lower() != 'y':
        print("❌ Extraction cancelled")
        return
    
    # Extract race data
    total_success = 0
    start_time = datetime.now()

    try:
        for i, date_entry in enumerate(filtered_dates, 1):
            race_date = date_entry['race_date']
            print(f"\n[{i}/{len(filtered_dates)}] {race_date}")

            success_count = extract_race_data(race_date, date_entry, args.racecourses, args.delay)
            total_success += success_count
            
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Process interrupted by user")
    
    # Summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    print(f"\n📊 EXTRACTION SUMMARY:")
    print(f"   Dates processed: {i}/{len(filtered_dates)}")
    print(f"   Successful extractions: {total_success}")
    print(f"   Duration: {duration}")
    print(f"   Average time per date: {duration.total_seconds() / i:.1f}s")

if __name__ == "__main__":
    main()
