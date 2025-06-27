#!/usr/bin/env python3
"""
Extract all race dates from HKJC racing results dropdown and save to JSON file.
No PocketBase interaction - just save to JSON.
"""

import json
import requests
import argparse
import time
import re
import shutil
import os
from datetime import datetime
from bs4 import BeautifulSoup

class HKJCRaceDateExtractor:
    def __init__(self):
        # HKJC URL for race results page
        self.hkjc_url = "https://racing.hkjc.com/racing/information/chinese/Racing/LocalResults.aspx?RaceDate=2024/12/15&Racecourse=ST&RaceNo=2"
    
    def extract_race_dates_from_hkjc(self):
        """Extract all race dates from HKJC dropdown."""
        try:
            print("🔍 Extracting race dates from HKJC website...")
            
            # Set headers to mimic a real browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            try:
                response = requests.get(self.hkjc_url, headers=headers, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Method 1: Look for date options in the HTML content
                import re
                date_pattern = r'\b(\d{2}/\d{2}/\d{4})\b'
                page_text = soup.get_text()
                
                found_dates = re.findall(date_pattern, page_text)
                unique_dates = list(set(found_dates))
                
                print(f"  ✅ Found {len(unique_dates)} unique race dates from website")
                
            except Exception as e:
                print(f"  ⚠️  Website extraction failed: {str(e)}")
                print(f"  📋 Using known race dates from previous extraction...")
                
                # Fallback to known dates
                unique_dates = [
                    "17/06/2025", "14/06/2025", "11/06/2025", "08/06/2025", "07/06/2025", "04/06/2025", 
                    "01/06/2025", "31/05/2025", "28/05/2025", "25/05/2025", "24/05/2025", "21/05/2025", 
                    "18/05/2025", "17/05/2025", "14/05/2025", "11/05/2025", "10/05/2025", "07/05/2025", 
                    "04/05/2025", "03/05/2025", "30/04/2025", "27/04/2025", "23/04/2025", "20/04/2025", 
                    "16/04/2025", "13/04/2025", "12/04/2025", "09/04/2025", "06/04/2025", "05/04/2025", 
                    "02/04/2025", "30/03/2025", "29/03/2025", "26/03/2025", "23/03/2025", "19/03/2025", 
                    "15/03/2025", "12/03/2025", "09/03/2025", "08/03/2025", "05/03/2025", "02/03/2025", 
                    "26/02/2025", "23/02/2025", "22/02/2025", "19/02/2025", "16/02/2025", "12/02/2025", 
                    "09/02/2025", "05/02/2025", "31/01/2025", "26/01/2025", "25/01/2025", "22/01/2025", 
                    "19/01/2025", "15/01/2025", "12/01/2025", "08/01/2025", "05/01/2025", "01/01/2025", 
                    "29/12/2024", "26/12/2024", "22/12/2024", "18/12/2024", "15/12/2024", "11/12/2024", 
                    "08/12/2024", "04/12/2024", "01/12/2024", "27/11/2024", "24/11/2024", "20/11/2024", 
                    "17/11/2024", "13/11/2024", "10/11/2024", "09/11/2024", "06/11/2024", "05/11/2024", 
                    "03/11/2024", "02/11/2024", "30/10/2024", "27/10/2024", "23/10/2024", "20/10/2024", 
                    "19/10/2024", "16/10/2024", "13/10/2024", "09/10/2024", "06/10/2024", "01/10/2024", 
                    "29/09/2024", "28/09/2024", "25/09/2024", "22/09/2024", "18/09/2024", "15/09/2024", 
                    "14/09/2024", "11/09/2024", "08/09/2024", "01/09/2024", "23/08/2024", "22/08/2024", 
                    "21/08/2024", "11/08/2024", "04/08/2024", "01/08/2024", "31/07/2024", "30/07/2024", 
                    "28/07/2024", "27/07/2024", "14/07/2024", "10/07/2024", "07/07/2024", "06/07/2024", 
                    "04/07/2024", "01/07/2024", "30/06/2024", "26/06/2024", "23/06/2024", "22/06/2024", 
                    "21/06/2024", "20/06/2024", "19/06/2024", "18/06/2024", "15/06/2024", "12/06/2024", 
                    "08/06/2024", "05/06/2024", "02/06/2024", "01/06/2024", "29/05/2024", "26/05/2024", 
                    "22/05/2024", "19/05/2024", "18/05/2024", "15/05/2024", "12/05/2024", "11/05/2024", 
                    "08/05/2024", "05/05/2024", "04/05/2024", "01/05/2024", "28/04/2024", "24/04/2024", 
                    "20/04/2024", "17/04/2024", "14/04/2024", "13/04/2024", "10/04/2024", "07/04/2024", 
                    "06/04/2024", "03/04/2024", "31/03/2024", "30/03/2024", "27/03/2024", "24/03/2024", 
                    "20/03/2024", "16/03/2024", "13/03/2024", "10/03/2024", "06/03/2024", "03/03/2024", 
                    "28/02/2024", "25/02/2024", "24/02/2024", "21/02/2024", "18/02/2024", "15/02/2024", 
                    "12/02/2024", "07/02/2024", "04/02/2024", "31/01/2024", "28/01/2024", "27/01/2024", 
                    "24/01/2024", "21/01/2024", "17/01/2024", "13/01/2024", "10/01/2024", "07/01/2024", 
                    "04/01/2024", "01/01/2024", "29/12/2023", "26/12/2023", "24/12/2023", "23/12/2023", 
                    "20/12/2023", "17/12/2023", "13/12/2023", "10/12/2023", "06/12/2023", "03/12/2023", 
                    "29/11/2023", "26/11/2023", "22/11/2023", "19/11/2023", "15/11/2023", "12/11/2023", 
                    "11/11/2023", "08/11/2023", "07/11/2023", "05/11/2023", "04/11/2023", "01/11/2023", 
                    "29/10/2023", "28/10/2023", "25/10/2023", "22/10/2023", "21/10/2023", "18/10/2023", 
                    "15/10/2023", "14/10/2023", "11/10/2023", "08/10/2023", "07/10/2023", "04/10/2023", 
                    "01/10/2023", "27/09/2023", "24/09/2023", "20/09/2023", "17/09/2023", "13/09/2023", 
                    "10/09/2023", "09/09/2023", "03/09/2023", "25/08/2023", "24/08/2023", "23/08/2023", 
                    "20/08/2023", "13/08/2023", "06/08/2023", "03/08/2023", "02/08/2023", "01/08/2023", 
                    "30/07/2023", "29/07/2023", "23/07/2023"
                ]
                print(f"  📋 Using {len(unique_dates)} known race dates")
            
            # Convert dates and determine status
            race_dates = []
            current_date = datetime.now()
            
            for date_str in unique_dates:
                try:
                    # Parse DD/MM/YYYY format
                    date_obj = datetime.strptime(date_str, '%d/%m/%Y')
                    
                    # Convert to YYYY/MM/DD format for storage
                    race_date_storage = date_obj.strftime('%Y/%m/%d')
                    
                    # Determine status based on current date
                    if date_obj.date() < current_date.date():
                        status = "completed"
                    elif date_obj.date() == current_date.date():
                        status = "today"
                    else:
                        status = "upcoming"
                    
                    race_dates.append({
                        'race_date': race_date_storage,
                        'race_date_formatted': date_str,
                        'status': status,
                        'racecourse': None,  # Will be determined later if possible
                        'total_races': None,
                        'extracted_at': datetime.now().isoformat(),
                        'last_updated': datetime.now().isoformat()
                    })
                    
                except ValueError:
                    print(f"  ⚠️  Could not parse date: {date_str}")
                    continue
            
            # Sort by date
            race_dates.sort(key=lambda x: x['race_date'])
            
            print(f"  ✅ Successfully processed {len(race_dates)} race dates")
            return race_dates
            
        except Exception as e:
            print(f"❌ Error extracting race dates: {str(e)}")
            return []

    def save_to_json(self, race_dates, output_file):
        """Save race dates to JSON file."""
        try:
            print(f"💾 Saving race dates to {output_file}...")
            
            # Create metadata
            metadata = {
                'extracted_at': datetime.now().isoformat(),
                'total_dates': len(race_dates),
                'date_range': {
                    'earliest': race_dates[0]['race_date_formatted'] if race_dates else None,
                    'latest': race_dates[-1]['race_date_formatted'] if race_dates else None
                },
                'status_summary': {}
            }
            
            # Count statuses
            for race_date in race_dates:
                status = race_date['status']
                metadata['status_summary'][status] = metadata['status_summary'].get(status, 0) + 1
            
            # Create final data structure
            output_data = {
                'metadata': metadata,
                'race_dates': race_dates
            }
            
            # Save to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            print(f"  ✅ Successfully saved {len(race_dates)} race dates")
            print(f"  📊 Status breakdown:")
            for status, count in metadata['status_summary'].items():
                print(f"     • {status}: {count}")
            
            if race_dates:
                print(f"  📅 Date range: {metadata['date_range']['earliest']} to {metadata['date_range']['latest']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving to JSON: {str(e)}")
            return False

    def run(self, output_file, update_metadata=True, delay=1.5):
        """Main execution method."""
        print("HKJC Race Dates Extractor with Metadata Update")
        print("=" * 60)
        print(f"Output file: {output_file}")
        print(f"Update metadata: {update_metadata}")
        if update_metadata:
            print(f"Delay between requests: {delay}s")
        print()

        # Load existing data if file exists
        existing_data = self.load_existing_data(output_file)

        # Extract race dates from HKJC
        race_dates = self.extract_race_dates_from_hkjc()
        if not race_dates:
            print("❌ No race dates extracted")
            return False

        # Merge with existing metadata
        if existing_data:
            race_dates = self.merge_with_existing_metadata(race_dates, existing_data)

        # Update metadata if requested
        if update_metadata:
            print(f"\n🔍 Updating metadata for {len(race_dates)} race dates...")
            race_dates = self.update_race_metadata(race_dates, delay)

        # Save to JSON
        success = self.save_to_json(race_dates, output_file)

        if success:
            print(f"\n✅ Successfully extracted and saved race dates!")
            print(f"📄 Output file: {output_file}")
            print(f"📊 Total dates: {len(race_dates)}")
            if update_metadata:
                self.print_metadata_statistics(race_dates)
        else:
            print(f"\n❌ Failed to save race dates")

        return success

    def load_existing_data(self, output_file):
        """Load existing race dates data if file exists."""
        try:
            if os.path.exists(output_file):
                print(f"📂 Loading existing data from {output_file}...")
                with open(output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    existing_dates = data.get('race_dates', [])
                    print(f"  ✅ Found {len(existing_dates)} existing race dates")
                    return existing_dates
        except Exception as e:
            print(f"  ⚠️  Could not load existing data: {e}")
        return None

    def merge_with_existing_metadata(self, new_dates, existing_dates):
        """Merge new dates with existing metadata."""
        print("🔄 Merging with existing metadata...")

        # Create lookup dictionary for existing dates
        existing_lookup = {entry['race_date']: entry for entry in existing_dates}

        merged_dates = []
        preserved_count = 0

        for new_entry in new_dates:
            race_date = new_entry['race_date']

            if race_date in existing_lookup:
                existing_entry = existing_lookup[race_date]

                # Check if existing entry has valid metadata
                if (existing_entry.get('racecourse') and
                    existing_entry.get('total_races') is not None and
                    existing_entry.get('last_updated')):

                    # Preserve existing metadata but update basic fields
                    merged_entry = existing_entry.copy()
                    merged_entry['status'] = new_entry['status']  # Update status
                    merged_entry['race_date_formatted'] = new_entry['race_date_formatted']
                    merged_dates.append(merged_entry)
                    preserved_count += 1
                else:
                    # Existing entry has incomplete metadata, use new entry
                    merged_dates.append(new_entry)
            else:
                # New date, use new entry
                merged_dates.append(new_entry)

        print(f"  ✅ Preserved metadata for {preserved_count} existing dates")
        return merged_dates

    def update_race_metadata(self, race_dates, delay=1.5):
        """Update race metadata (racecourse and total_races) for dates that need verification."""
        updated_dates = []
        stats = {"st": 0, "hv": 0, "no_racing": 0, "errors": 0, "skipped": 0}

        # Determine which dates need verification
        dates_to_verify = []
        current_date = datetime.now()

        for race_date_entry in race_dates:
            race_date = race_date_entry['race_date']

            # Check if metadata is missing or incomplete
            has_metadata = (race_date_entry.get('racecourse') and
                          race_date_entry.get('total_races') is not None and
                          race_date_entry.get('last_updated'))

            if not has_metadata:
                dates_to_verify.append(race_date_entry)
                continue

            # Check if date is recent (within last 30 days) and might need re-verification
            try:
                date_obj = datetime.strptime(race_date, '%Y/%m/%d')
                days_ago = (current_date - date_obj).days

                # Only re-verify recent dates (within 30 days) or future dates
                if days_ago <= 30:
                    dates_to_verify.append(race_date_entry)
                else:
                    # Skip old dates with existing metadata
                    stats['skipped'] += 1
            except:
                # If date parsing fails, verify it
                dates_to_verify.append(race_date_entry)

        print(f"📊 Verification plan:")
        print(f"  • Total dates: {len(race_dates)}")
        print(f"  • Need verification: {len(dates_to_verify)}")
        print(f"  • Skipping (old with metadata): {len(race_dates) - len(dates_to_verify)}")

        if not dates_to_verify:
            print("✅ All dates already have valid metadata!")
            return race_dates

        verify_count = 0
        for i, race_date_entry in enumerate(race_dates, 1):
            race_date = race_date_entry['race_date']

            if race_date_entry in dates_to_verify:
                verify_count += 1
                print(f"[{verify_count}/{len(dates_to_verify)}] 🔍 Verifying {race_date}...")

                try:
                    metadata = self.verify_racecourse_for_date(race_date)

                    # Update the entry with metadata
                    race_date_entry['racecourse'] = metadata['racecourse']
                    race_date_entry['total_races'] = metadata['total_races']
                    race_date_entry['metadata_source'] = 'hkjc_url_verification'
                    race_date_entry['verification_confidence'] = metadata['confidence']
                    race_date_entry['verification_method'] = metadata['method']
                    race_date_entry['last_updated'] = datetime.now().isoformat()

                    # Update statistics
                    if metadata['racecourse'] == "ST":
                        stats["st"] += 1
                        print(f"    ✅ ST - {metadata['total_races']} races")
                    elif metadata['racecourse'] == "HV":
                        stats["hv"] += 1
                        print(f"    ✅ HV - {metadata['total_races']} races")
                    elif metadata['racecourse'] == "NO_RACING":
                        stats["no_racing"] += 1
                        print(f"    ⚪ No racing")
                    else:
                        stats["errors"] += 1
                        print(f"    ❌ Could not verify")

                    # Add delay between verification requests
                    if verify_count < len(dates_to_verify):
                        time.sleep(delay)

                except Exception as e:
                    print(f"    ❌ Error: {e}")
                    stats["errors"] += 1
            else:
                # Skip verification for this date
                racecourse = race_date_entry.get('racecourse', 'UNKNOWN')
                total_races = race_date_entry.get('total_races', 0)
                print(f"[SKIP] ✅ {race_date} - {racecourse} ({total_races} races) - using cached metadata")
                stats["skipped"] += 1

            updated_dates.append(race_date_entry)

        return updated_dates

    def verify_racecourse_for_date(self, race_date):
        """Verify racecourse for a specific date using HKJC URLs."""
        result = {
            "racecourse": None,
            "total_races": None,
            "confidence": "low",
            "method": "unknown"
        }

        try:
            # Convert date format
            date_obj = datetime.strptime(race_date, '%Y/%m/%d')
            formatted_date = date_obj.strftime('%Y/%m/%d')  # YYYY/MM/DD
            weekday = date_obj.weekday()  # 0=Monday, 6=Sunday

            # Method 1: Try Sha Tin (ST) directly
            st_url = f"https://racing.hkjc.com/racing/information/chinese/Racing/LocalResults.aspx?RaceDate={formatted_date}&Racecourse=ST"

            try:
                response = requests.get(st_url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                if response.status_code == 200:
                    content = response.text

                    if "沒有相關資料" not in content and "賽果" in content and len(content) > 5000:
                        # Found substantial content for ST
                        result["racecourse"] = "ST"
                        result["method"] = "direct_st_verification"
                        result["confidence"] = "high"

                        # Try to extract race count
                        race_count = self.extract_race_count_from_content(content)
                        if race_count:
                            result["total_races"] = race_count
                        else:
                            # Default ST race count based on weekday
                            result["total_races"] = 11 if weekday >= 5 else 10

                        return result
            except Exception:
                pass

            # Method 2: Try Happy Valley (HV) directly
            hv_url = f"https://racing.hkjc.com/racing/information/chinese/Racing/LocalResults.aspx?RaceDate={formatted_date}&Racecourse=HV"

            try:
                response = requests.get(hv_url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                if response.status_code == 200:
                    content = response.text

                    if "沒有相關資料" not in content and "賽果" in content and len(content) > 5000:
                        # Found substantial content for HV
                        result["racecourse"] = "HV"
                        result["method"] = "direct_hv_verification"
                        result["confidence"] = "high"

                        # Try to extract race count
                        race_count = self.extract_race_count_from_content(content)
                        if race_count:
                            result["total_races"] = race_count
                        else:
                            # Default HV race count
                            result["total_races"] = 8

                        return result
            except Exception:
                pass

            # Method 3: If no data found for either, mark as NO_RACING
            result["racecourse"] = "NO_RACING"
            result["total_races"] = 0
            result["method"] = "no_data_found"
            result["confidence"] = "high"

            return result

        except Exception as e:
            result["method"] = "error"
            return result

    def extract_race_count_from_content(self, content):
        """Extract race count from page content."""
        try:
            # Look for race patterns in content
            race_patterns = [
                r'第(\d+)場',  # Chinese race number pattern
                r'Race\s+(\d+)',  # English race number pattern
                r'R(\d+)',  # R1, R2, etc.
                r'RaceNo=(\d+)',  # URL parameter pattern
            ]

            all_races = []
            for pattern in race_patterns:
                matches = re.findall(pattern, content)
                all_races.extend([int(m) for m in matches])

            if all_races:
                return max(all_races)

        except Exception:
            pass

        return None

    def print_metadata_statistics(self, race_dates):
        """Print metadata update statistics."""
        stats = {"st": 0, "hv": 0, "no_racing": 0, "errors": 0}

        for entry in race_dates:
            racecourse = entry.get('racecourse')
            if racecourse == "ST":
                stats["st"] += 1
            elif racecourse == "HV":
                stats["hv"] += 1
            elif racecourse == "NO_RACING":
                stats["no_racing"] += 1
            else:
                stats["errors"] += 1

        print(f"\n📊 METADATA STATISTICS:")
        print(f"   ST (Sha Tin): {stats['st']}")
        print(f"   HV (Happy Valley): {stats['hv']}")
        print(f"   No Racing: {stats['no_racing']}")
        print(f"   Errors: {stats['errors']}")

def main():
    parser = argparse.ArgumentParser(
        description='Extract race dates from HKJC and save to JSON file with metadata',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extract_race_dates_to_json.py                    # Extract dates with metadata
  python extract_race_dates_to_json.py --no-metadata     # Extract dates only (fast)
  python extract_race_dates_to_json.py --delay 2.0       # Custom delay for metadata
  python extract_race_dates_to_json.py --output my_dates.json
        """
    )
    
    parser.add_argument('--output', '-o', default='race_dates.json',
                       help='Output JSON file (default: race_dates.json)')
    parser.add_argument('--no-metadata', action='store_true',
                       help='Skip metadata update (racecourse and total_races verification)')
    parser.add_argument('--delay', type=float, default=1.5,
                       help='Delay between metadata requests in seconds (default: 1.5)')

    args = parser.parse_args()

    # Initialize extractor
    extractor = HKJCRaceDateExtractor()

    # Run the extraction with metadata update
    update_metadata = not args.no_metadata
    success = extractor.run(args.output, update_metadata, args.delay)
    
    if not success:
        exit(1)

if __name__ == "__main__":
    main()
