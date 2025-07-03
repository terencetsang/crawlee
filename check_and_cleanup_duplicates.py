import json
import os
from datetime import datetime
from dotenv import load_dotenv
from pocketbase import PocketBase
from collections import defaultdict

# Load environment variables from .env file
load_dotenv()

# PocketBase configuration
POCKETBASE_URL = os.getenv("POCKETBASE_URL")
POCKETBASE_EMAIL = os.getenv("POCKETBASE_EMAIL")
POCKETBASE_PASSWORD = os.getenv("POCKETBASE_PASSWORD")
COLLECTION_NAME = "race_odds"

def find_duplicate_records():
    """Find duplicate records in PocketBase"""
    try:
        print("🔍 Checking for duplicate records in PocketBase...")
        
        client = PocketBase(POCKETBASE_URL)
        client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
        
        # Get all records
        all_records = client.collection(COLLECTION_NAME).get_full_list()
        print(f"📊 Total records found: {len(all_records)}")
        
        # Group records by race key (date_venue_race_number)
        race_groups = defaultdict(list)
        
        for record in all_records:
            race_key = f"{record.race_date}_{record.venue}_{record.race_number}"
            race_groups[race_key].append({
                'id': record.id,
                'race_date': record.race_date,
                'venue': record.venue,
                'race_number': record.race_number,
                'scraped_at': record.scraped_at,
                'extraction_status': record.extraction_status
            })
        
        # Find duplicates
        duplicates = {}
        unique_races = {}
        
        for race_key, records in race_groups.items():
            if len(records) > 1:
                duplicates[race_key] = records
            else:
                unique_races[race_key] = records[0]
        
        print(f"✅ Unique races: {len(unique_races)}")
        print(f"⚠️ Duplicate race keys: {len(duplicates)}")
        
        if duplicates:
            print(f"\n📋 Duplicate records found:")
            total_duplicate_records = 0
            
            for race_key, records in duplicates.items():
                print(f"\n   🔄 {race_key}: {len(records)} records")
                total_duplicate_records += len(records)
                
                for i, record in enumerate(records):
                    print(f"      {i+1}. ID: {record['id']} | Scraped: {record['scraped_at']} | Status: {record['extraction_status']}")
            
            print(f"\n📊 Summary:")
            print(f"   - Total duplicate records: {total_duplicate_records}")
            print(f"   - Records to keep: {len(duplicates)} (1 per race)")
            print(f"   - Records to delete: {total_duplicate_records - len(duplicates)}")
        
        return duplicates, unique_races
        
    except Exception as e:
        print(f"❌ Error finding duplicates: {str(e)}")
        return {}, {}

def cleanup_duplicates(duplicates):
    """Clean up duplicate records, keeping the most recent one"""
    if not duplicates:
        print("✅ No duplicates to clean up!")
        return True
    
    try:
        print(f"\n🧹 Cleaning up {len(duplicates)} duplicate race keys...")
        
        client = PocketBase(POCKETBASE_URL)
        client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
        
        total_deleted = 0
        failed_deletions = 0
        
        for race_key, records in duplicates.items():
            print(f"\n🔄 Processing {race_key} ({len(records)} records)...")
            
            # Sort by scraped_at timestamp to keep the most recent
            records.sort(key=lambda x: x['scraped_at'], reverse=True)
            
            # Keep the first (most recent) record, delete the rest
            keep_record = records[0]
            delete_records = records[1:]
            
            print(f"   ✅ Keeping: {keep_record['id']} (scraped: {keep_record['scraped_at']})")
            
            for record in delete_records:
                try:
                    client.collection(COLLECTION_NAME).delete(record['id'])
                    print(f"   🗑️ Deleted: {record['id']} (scraped: {record['scraped_at']})")
                    total_deleted += 1
                except Exception as e:
                    print(f"   ❌ Failed to delete {record['id']}: {e}")
                    failed_deletions += 1
        
        print(f"\n📊 Cleanup Summary:")
        print(f"✅ Successfully deleted: {total_deleted}")
        print(f"❌ Failed deletions: {failed_deletions}")
        
        return failed_deletions == 0
        
    except Exception as e:
        print(f"❌ Error during cleanup: {str(e)}")
        return False

def verify_final_state():
    """Verify the final state after cleanup"""
    try:
        print(f"\n🔍 Verifying final database state...")
        
        client = PocketBase(POCKETBASE_URL)
        client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
        
        # Get all remaining records
        all_records = client.collection(COLLECTION_NAME).get_full_list()
        
        # Group by date and venue
        date_summary = defaultdict(lambda: {"ST": 0, "HV": 0})
        race_keys = set()
        
        for record in all_records:
            date = record.race_date
            venue = record.venue
            race_key = f"{record.race_date}_{record.venue}_{record.race_number}"
            
            date_summary[date][venue] += 1
            race_keys.add(race_key)
        
        print(f"\n📊 Final Database Summary:")
        print(f"Total records: {len(all_records)}")
        print(f"Unique races: {len(race_keys)}")
        print(f"\nRace sessions:")
        
        total_races = 0
        for date in sorted(date_summary.keys()):
            st_count = date_summary[date]["ST"]
            hv_count = date_summary[date]["HV"]
            date_total = st_count + hv_count
            total_races += date_total
            
            print(f"   {date}: ST({st_count}) + HV({hv_count}) = {date_total} races")
        
        print(f"\n🎯 Grand Total: {total_races} races")
        
        # Check for any remaining duplicates
        race_groups = defaultdict(int)
        for record in all_records:
            race_key = f"{record.race_date}_{record.venue}_{record.race_number}"
            race_groups[race_key] += 1
        
        remaining_duplicates = {k: v for k, v in race_groups.items() if v > 1}
        
        if remaining_duplicates:
            print(f"⚠️ WARNING: Still found {len(remaining_duplicates)} duplicate race keys!")
            for race_key, count in remaining_duplicates.items():
                print(f"   - {race_key}: {count} records")
            return False
        else:
            print(f"✅ Confirmed: No duplicate records remain")
            return True
        
    except Exception as e:
        print(f"❌ Error verifying final state: {e}")
        return False

def main():
    """Main function to check and cleanup duplicates"""
    print("🏇 HKJC Duplicate Records Checker & Cleanup")
    print("=" * 60)
    
    # Step 1: Find duplicates
    duplicates, unique_races = find_duplicate_records()
    
    # Step 2: Clean up duplicates if found
    if duplicates:
        print(f"\n⚠️ Found duplicates - proceeding with cleanup...")
        cleanup_success = cleanup_duplicates(duplicates)
    else:
        print(f"\n✅ No duplicates found - database is clean!")
        cleanup_success = True
    
    # Step 3: Verify final state
    if cleanup_success:
        verification_success = verify_final_state()
    else:
        verification_success = False
    
    # Final summary
    print(f"\n" + "=" * 60)
    print("🎯 FINAL SUMMARY:")
    
    if duplicates:
        print(f"🔄 Duplicates found: {len(duplicates)} race keys")
        print(f"🧹 Cleanup: {'✅ Success' if cleanup_success else '❌ Failed'}")
    else:
        print(f"✅ No duplicates found")
    
    print(f"🔍 Verification: {'✅ Success' if verification_success else '❌ Failed'}")
    
    if cleanup_success and verification_success:
        print(f"\n🎉 Database is now clean with no duplicate records!")
    elif not duplicates:
        print(f"\n✅ Database was already clean!")
    else:
        print(f"\n⚠️ Some issues remain - please check the logs")
    
    print("=" * 60)

if __name__ == '__main__':
    main()
