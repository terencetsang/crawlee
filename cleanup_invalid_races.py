import json
import os
from datetime import datetime
from dotenv import load_dotenv
from pocketbase import PocketBase

# Load environment variables from .env file
load_dotenv()

# PocketBase configuration
POCKETBASE_URL = os.getenv("POCKETBASE_URL")
POCKETBASE_EMAIL = os.getenv("POCKETBASE_EMAIL")
POCKETBASE_PASSWORD = os.getenv("POCKETBASE_PASSWORD")
COLLECTION_NAME = "race_odds"

def cleanup_invalid_race_data():
    """Clean up invalid race data from PocketBase"""
    try:
        print("🧹 Cleaning up invalid race data from PocketBase...")
        
        # Initialize PocketBase client
        client = PocketBase(POCKETBASE_URL)
        
        # Authenticate
        try:
            client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
            print("✅ Authenticated with PocketBase")
        except Exception as auth_error:
            print(f"❌ Authentication failed: {str(auth_error)}")
            return False
        
        # Define invalid dates (dates that shouldn't have races)
        invalid_dates = [
            "2025-07-02"  # No races on this date
        ]
        
        total_deleted = 0
        
        for invalid_date in invalid_dates:
            print(f"\n🔍 Checking for invalid records on {invalid_date}...")
            
            try:
                # Get all records for this date
                records = client.collection(COLLECTION_NAME).get_full_list(
                    query_params={
                        "filter": f'race_date="{invalid_date}"'
                    }
                )
                
                if records:
                    print(f"⚠️ Found {len(records)} invalid records for {invalid_date}")
                    
                    # Delete each record
                    for record in records:
                        try:
                            client.collection(COLLECTION_NAME).delete(record.id)
                            print(f"   🗑️ Deleted record {record.id} - {invalid_date} {record.venue} Race {record.race_number}")
                            total_deleted += 1
                        except Exception as delete_error:
                            print(f"   ❌ Failed to delete record {record.id}: {delete_error}")
                else:
                    print(f"✅ No invalid records found for {invalid_date}")
                    
            except Exception as query_error:
                print(f"❌ Error querying records for {invalid_date}: {query_error}")
        
        print(f"\n🎉 Cleanup completed! Deleted {total_deleted} invalid records.")
        return True
        
    except Exception as e:
        print(f"❌ Cleanup error: {str(e)}")
        return False

def validate_existing_data():
    """Validate existing data in PocketBase and report any issues"""
    try:
        print("\n🔍 Validating existing race data...")
        
        # Initialize PocketBase client
        client = PocketBase(POCKETBASE_URL)
        
        # Authenticate
        client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
        
        # Get all records
        all_records = client.collection(COLLECTION_NAME).get_full_list()
        
        print(f"📊 Total records in database: {len(all_records)}")
        
        # Group by date and venue
        date_venue_counts = {}
        duplicate_races = []
        
        for record in all_records:
            date_venue_key = f"{record.race_date}_{record.venue}"
            
            if date_venue_key not in date_venue_counts:
                date_venue_counts[date_venue_key] = []
            
            date_venue_counts[date_venue_key].append({
                'id': record.id,
                'race_number': record.race_number,
                'extraction_status': record.extraction_status
            })
        
        # Check for issues
        print("\n📋 Race sessions found:")
        for date_venue, races in sorted(date_venue_counts.items()):
            date, venue = date_venue.split('_')
            race_numbers = [r['race_number'] for r in races]
            race_numbers.sort()
            
            # Check for duplicates
            if len(race_numbers) != len(set(race_numbers)):
                duplicate_races.append(date_venue)
                print(f"⚠️ {date} {venue}: {len(races)} races (DUPLICATES FOUND) - {race_numbers}")
            else:
                print(f"✅ {date} {venue}: {len(races)} races - {race_numbers}")
        
        # Report duplicates
        if duplicate_races:
            print(f"\n⚠️ Found duplicate races in {len(duplicate_races)} sessions:")
            for date_venue in duplicate_races:
                date, venue = date_venue.split('_')
                races = date_venue_counts[date_venue]
                race_numbers = [r['race_number'] for r in races]
                duplicates = [x for x in set(race_numbers) if race_numbers.count(x) > 1]
                print(f"   {date} {venue}: Duplicate race numbers {duplicates}")
        
        # Check for suspicious dates (future dates, weekdays that typically don't have races)
        suspicious_dates = []
        today = datetime.now().date()
        
        for date_venue in date_venue_counts.keys():
            date_str, venue = date_venue.split('_')
            try:
                race_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                
                # Check if date is in the future
                if race_date > today:
                    suspicious_dates.append(f"{date_str} (future date)")
                
                # Check if it's a Tuesday (day 1) - typically no races
                if race_date.weekday() == 1:  # Tuesday
                    suspicious_dates.append(f"{date_str} (Tuesday - unusual)")
                    
            except ValueError:
                suspicious_dates.append(f"{date_str} (invalid date format)")
        
        if suspicious_dates:
            print(f"\n⚠️ Suspicious dates found:")
            for suspicious_date in suspicious_dates:
                print(f"   {suspicious_date}")
        
        return True
        
    except Exception as e:
        print(f"❌ Validation error: {str(e)}")
        return False

def main():
    """Main function to clean up and validate race data"""
    print("🏇 HKJC Race Data Cleanup & Validation")
    print("=" * 50)
    
    # Step 1: Clean up invalid data
    cleanup_success = cleanup_invalid_race_data()
    
    # Step 2: Validate remaining data
    if cleanup_success:
        validate_existing_data()
    
    print("\n" + "=" * 50)
    print("🎉 Cleanup and validation completed!")
    print("=" * 50)

if __name__ == '__main__':
    main()
