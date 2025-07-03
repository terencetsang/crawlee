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

# Correct venue assignments based on HKJC racing schedule
CORRECT_VENUES = {
    "2025-06-26": "ST",  # Sha Tin
    "2025-06-27": "HV",  # Happy Valley
    "2025-06-28": "ST",  # Sha Tin
    "2025-06-29": "HV",  # Happy Valley
    "2025-06-30": "ST",  # Sha Tin
    "2025-07-01": "ST",  # Sha Tin (confirmed by user)
}

def analyze_current_venue_assignments():
    """Analyze current venue assignments in the database"""
    try:
        print("🔍 Analyzing current venue assignments...")
        
        client = PocketBase(POCKETBASE_URL)
        client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
        
        # Get all records
        all_records = client.collection(COLLECTION_NAME).get_full_list()
        
        # Group by date and venue
        date_venue_summary = {}
        invalid_records = []
        
        for record in all_records:
            date = record.race_date
            venue = record.venue
            
            if date not in date_venue_summary:
                date_venue_summary[date] = {"ST": 0, "HV": 0, "records": {"ST": [], "HV": []}}
            
            date_venue_summary[date][venue] += 1
            date_venue_summary[date]["records"][venue].append({
                "id": record.id,
                "race_number": record.race_number,
                "scraped_at": record.scraped_at
            })
            
            # Check if this record has incorrect venue
            if date in CORRECT_VENUES:
                correct_venue = CORRECT_VENUES[date]
                if venue != correct_venue:
                    invalid_records.append({
                        "id": record.id,
                        "race_date": date,
                        "current_venue": venue,
                        "correct_venue": correct_venue,
                        "race_number": record.race_number
                    })
        
        print(f"\n📊 Current venue assignments:")
        for date in sorted(date_venue_summary.keys()):
            st_count = date_venue_summary[date]["ST"]
            hv_count = date_venue_summary[date]["HV"]
            correct_venue = CORRECT_VENUES.get(date, "Unknown")
            
            status = "✅" if (st_count > 0 and hv_count == 0 and correct_venue == "ST") or \
                           (hv_count > 0 and st_count == 0 and correct_venue == "HV") else "❌"
            
            print(f"   {status} {date}: ST({st_count}) + HV({hv_count}) | Should be: {correct_venue}")
        
        print(f"\n⚠️ Invalid venue assignments found: {len(invalid_records)}")
        
        if invalid_records:
            print(f"\n📋 Invalid records to fix:")
            for record in invalid_records:
                print(f"   - {record['race_date']} {record['current_venue']} Race {record['race_number']} → Should be {record['correct_venue']}")
        
        return invalid_records, date_venue_summary
        
    except Exception as e:
        print(f"❌ Error analyzing venues: {str(e)}")
        return [], {}

def cleanup_invalid_venue_records(invalid_records):
    """Remove records with invalid venue assignments"""
    if not invalid_records:
        print("✅ No invalid venue records to clean up!")
        return True
    
    try:
        print(f"\n🧹 Cleaning up {len(invalid_records)} invalid venue records...")
        
        client = PocketBase(POCKETBASE_URL)
        client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
        
        # Group invalid records by date for better display
        by_date = {}
        for record in invalid_records:
            date = record['race_date']
            if date not in by_date:
                by_date[date] = []
            by_date[date].append(record)
        
        print(f"\n📋 Records to be deleted:")
        total_to_delete = 0
        for date in sorted(by_date.keys()):
            records = by_date[date]
            correct_venue = CORRECT_VENUES[date]
            print(f"\n   📅 {date} (should be {correct_venue} only):")
            for record in records:
                print(f"      🗑️ {record['current_venue']} Race {record['race_number']} (ID: {record['id']})")
                total_to_delete += 1
        
        print(f"\n⚠️ WARNING: This will permanently delete {total_to_delete} records!")
        confirm = input("Do you want to proceed? (yes/no): ").lower().strip()
        
        if confirm in ['yes', 'y']:
            deleted_count = 0
            failed_count = 0
            
            for record in invalid_records:
                try:
                    client.collection(COLLECTION_NAME).delete(record['id'])
                    print(f"   🗑️ Deleted: {record['race_date']} {record['current_venue']} Race {record['race_number']}")
                    deleted_count += 1
                except Exception as e:
                    print(f"   ❌ Failed to delete {record['id']}: {e}")
                    failed_count += 1
            
            print(f"\n📊 Cleanup Summary:")
            print(f"✅ Successfully deleted: {deleted_count}")
            print(f"❌ Failed to delete: {failed_count}")
            
            return failed_count == 0
        else:
            print("❌ Cleanup cancelled by user")
            return False
            
    except Exception as e:
        print(f"❌ Error during cleanup: {str(e)}")
        return False

def verify_final_venue_assignments():
    """Verify final venue assignments after cleanup"""
    try:
        print(f"\n🔍 Verifying final venue assignments...")
        
        client = PocketBase(POCKETBASE_URL)
        client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
        
        # Get all remaining records
        all_records = client.collection(COLLECTION_NAME).get_full_list()
        
        # Group by date and venue
        date_venue_summary = {}
        
        for record in all_records:
            date = record.race_date
            venue = record.venue
            
            if date not in date_venue_summary:
                date_venue_summary[date] = {"ST": 0, "HV": 0}
            date_venue_summary[date][venue] += 1
        
        print(f"\n📊 Final Database Summary:")
        print(f"Total records: {len(all_records)}")
        print(f"\nVenue assignments:")
        
        total_races = 0
        all_correct = True
        
        for date in sorted(date_venue_summary.keys()):
            st_count = date_venue_summary[date]["ST"]
            hv_count = date_venue_summary[date]["HV"]
            correct_venue = CORRECT_VENUES.get(date, "Unknown")
            
            # Check if assignment is correct
            is_correct = (st_count > 0 and hv_count == 0 and correct_venue == "ST") or \
                        (hv_count > 0 and st_count == 0 and correct_venue == "HV")
            
            status = "✅" if is_correct else "❌"
            if not is_correct:
                all_correct = False
            
            date_total = st_count + hv_count
            total_races += date_total
            
            print(f"   {status} {date}: {correct_venue}({date_total}) | Expected: {correct_venue} only")
        
        print(f"\n🎯 Grand Total: {total_races} races")
        
        if all_correct:
            print(f"✅ All venue assignments are now correct!")
        else:
            print(f"❌ Some venue assignments are still incorrect!")
        
        return all_correct
        
    except Exception as e:
        print(f"❌ Error verifying venues: {e}")
        return False

def main():
    """Main function to clean up invalid venue assignments"""
    print("🏇 HKJC Invalid Venue Cleanup")
    print("=" * 60)
    print("Correcting venue assignments based on HKJC racing schedule:")
    for date, venue in CORRECT_VENUES.items():
        venue_name = "Sha Tin" if venue == "ST" else "Happy Valley"
        print(f"   {date}: {venue} ({venue_name})")
    print("=" * 60)
    
    # Step 1: Analyze current assignments
    invalid_records, current_summary = analyze_current_venue_assignments()
    
    # Step 2: Clean up invalid records
    if invalid_records:
        cleanup_success = cleanup_invalid_venue_records(invalid_records)
    else:
        print(f"\n✅ All venue assignments are already correct!")
        cleanup_success = True
    
    # Step 3: Verify final state
    if cleanup_success:
        verification_success = verify_final_venue_assignments()
    else:
        verification_success = False
    
    # Final summary
    print(f"\n" + "=" * 60)
    print("🎯 CLEANUP SUMMARY:")
    
    if invalid_records:
        print(f"⚠️ Invalid records found: {len(invalid_records)}")
        print(f"🧹 Cleanup: {'✅ Success' if cleanup_success else '❌ Failed'}")
    else:
        print(f"✅ No invalid venue assignments found")
    
    print(f"🔍 Verification: {'✅ Success' if verification_success else '❌ Failed'}")
    
    if cleanup_success and verification_success:
        print(f"\n🎉 All venue assignments are now correct!")
        print(f"📊 Database contains only valid single-venue race dates")
    else:
        print(f"\n⚠️ Some issues remain - please check the logs")
    
    print("=" * 60)

if __name__ == '__main__':
    main()
