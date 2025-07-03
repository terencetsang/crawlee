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

def cleanup_july_2_records():
    """Clean up invalid 2025-07-02 records from PocketBase"""
    try:
        print("🧹 Cleaning up invalid 2025-07-02 records from PocketBase...")
        
        # Initialize PocketBase client
        client = PocketBase(POCKETBASE_URL)
        
        # Authenticate
        try:
            client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
            print("✅ Authenticated with PocketBase")
        except Exception as auth_error:
            print(f"❌ Authentication failed: {str(auth_error)}")
            return False
        
        # Get all 2025-07-02 records
        print(f"\n🔍 Searching for 2025-07-02 records...")
        
        try:
            july_2_records = client.collection(COLLECTION_NAME).get_full_list(
                query_params={
                    "filter": 'race_date="2025-07-02"'
                }
            )
            
            if july_2_records:
                print(f"⚠️ Found {len(july_2_records)} invalid records for 2025-07-02")
                
                # Show details of what will be deleted
                print(f"\n📋 Records to be deleted:")
                for record in july_2_records:
                    print(f"   - ID: {record.id} | {record.race_date} {record.venue} Race {record.race_number}")
                
                # Confirm deletion
                print(f"\n⚠️ WARNING: This will permanently delete {len(july_2_records)} records!")
                confirm = input("Do you want to proceed? (yes/no): ").lower().strip()
                
                if confirm in ['yes', 'y']:
                    # Delete each record
                    deleted_count = 0
                    failed_count = 0
                    
                    for record in july_2_records:
                        try:
                            client.collection(COLLECTION_NAME).delete(record.id)
                            print(f"   🗑️ Deleted: {record.race_date} {record.venue} Race {record.race_number}")
                            deleted_count += 1
                        except Exception as delete_error:
                            print(f"   ❌ Failed to delete record {record.id}: {delete_error}")
                            failed_count += 1
                    
                    print(f"\n📊 Cleanup Summary:")
                    print(f"✅ Successfully deleted: {deleted_count}")
                    print(f"❌ Failed to delete: {failed_count}")
                    
                    if deleted_count > 0:
                        print(f"🎉 Cleanup completed! Removed {deleted_count} invalid 2025-07-02 records.")
                    
                    return failed_count == 0
                else:
                    print("❌ Cleanup cancelled by user")
                    return False
            else:
                print(f"✅ No 2025-07-02 records found - database is already clean!")
                return True
                
        except Exception as query_error:
            print(f"❌ Error querying 2025-07-02 records: {query_error}")
            return False
        
    except Exception as e:
        print(f"❌ Cleanup error: {str(e)}")
        return False

def cleanup_july_2_local_files():
    """Also clean up local JSON files for 2025-07-02"""
    try:
        print(f"\n🧹 Cleaning up local 2025-07-02 JSON files...")
        
        # Look for 2025-07-02 files
        import glob
        pattern = "odds_data/win_odds_trends_2025_07_02_*.json"
        july_2_files = glob.glob(pattern)
        
        if july_2_files:
            print(f"⚠️ Found {len(july_2_files)} local 2025-07-02 files:")
            for file_path in july_2_files:
                print(f"   - {file_path}")
            
            confirm = input(f"\nDelete these {len(july_2_files)} local files? (yes/no): ").lower().strip()
            
            if confirm in ['yes', 'y']:
                deleted_files = 0
                for file_path in july_2_files:
                    try:
                        os.remove(file_path)
                        print(f"   🗑️ Deleted: {file_path}")
                        deleted_files += 1
                    except Exception as e:
                        print(f"   ❌ Failed to delete {file_path}: {e}")
                
                print(f"✅ Deleted {deleted_files} local files")
                return True
            else:
                print("❌ Local file cleanup cancelled")
                return False
        else:
            print(f"✅ No local 2025-07-02 files found")
            return True
            
    except Exception as e:
        print(f"❌ Error cleaning local files: {e}")
        return False

def verify_final_database_state():
    """Verify the final state of the database after cleanup"""
    try:
        print(f"\n🔍 Verifying final database state...")
        
        client = PocketBase(POCKETBASE_URL)
        client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
        
        # Get all remaining records
        all_records = client.collection(COLLECTION_NAME).get_full_list()
        
        # Group by date
        date_summary = {}
        for record in all_records:
            date = record.race_date
            venue = record.venue
            
            if date not in date_summary:
                date_summary[date] = {"ST": 0, "HV": 0}
            date_summary[date][venue] += 1
        
        print(f"\n📊 Final Database Summary:")
        print(f"Total records: {len(all_records)}")
        print(f"\nRace sessions:")
        
        total_races = 0
        for date in sorted(date_summary.keys()):
            st_count = date_summary[date]["ST"]
            hv_count = date_summary[date]["HV"]
            date_total = st_count + hv_count
            total_races += date_total
            
            print(f"   {date}: ST({st_count}) + HV({hv_count}) = {date_total} races")
        
        print(f"\n🎯 Grand Total: {total_races} races")
        
        # Check for any remaining 2025-07-02 records
        july_2_check = client.collection(COLLECTION_NAME).get_full_list(
            query_params={"filter": 'race_date="2025-07-02"'}
        )
        
        if july_2_check:
            print(f"⚠️ WARNING: Still found {len(july_2_check)} records for 2025-07-02!")
            return False
        else:
            print(f"✅ Confirmed: No 2025-07-02 records remain")
            return True
        
    except Exception as e:
        print(f"❌ Error verifying database: {e}")
        return False

def main():
    """Main cleanup function"""
    print("🏇 HKJC July 2nd Records Cleanup")
    print("=" * 50)
    print("This script will remove invalid 2025-07-02 race records")
    print("(No races actually occurred on July 2nd, 2025)")
    print("=" * 50)
    
    # Step 1: Clean up PocketBase records
    pocketbase_success = cleanup_july_2_records()
    
    # Step 2: Clean up local files
    local_files_success = cleanup_july_2_local_files()
    
    # Step 3: Verify final state
    if pocketbase_success:
        verification_success = verify_final_database_state()
    else:
        verification_success = False
    
    # Final summary
    print(f"\n" + "=" * 50)
    print("🎯 CLEANUP SUMMARY:")
    print(f"🗄️ PocketBase cleanup: {'✅ Success' if pocketbase_success else '❌ Failed'}")
    print(f"📁 Local files cleanup: {'✅ Success' if local_files_success else '❌ Failed'}")
    print(f"🔍 Final verification: {'✅ Success' if verification_success else '❌ Failed'}")
    
    if pocketbase_success and verification_success:
        print(f"\n🎉 All invalid 2025-07-02 records have been successfully removed!")
        print(f"📊 Database now contains only valid race data")
    else:
        print(f"\n⚠️ Some cleanup operations failed - please check the logs")
    
    print("=" * 50)

if __name__ == '__main__':
    main()
