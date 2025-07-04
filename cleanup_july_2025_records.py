#!/usr/bin/env python3
"""
Clean up ALL July 2025 records from PocketBase collections.
This script removes ALL records for July 2025 (both 2025/07/01 and 2025/07/05)
from all collections to allow for a fresh manual restart.
"""

import os
import json
import requests
from datetime import datetime
from urllib.parse import urljoin
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class July2025Cleaner:
    def __init__(self):
        self.base_url = os.getenv("POCKETBASE_URL", "http://terence.myds.me:8081").rstrip('/')
        self.email = os.getenv("POCKETBASE_EMAIL", "terencetsang@hotmail.com")
        self.password = os.getenv("POCKETBASE_PASSWORD", "Qwertyu12345")
        self.auth_token = None
        self.session = requests.Session()
        
        # All collections that might contain July 2025 data (all 8 collections)
        self.collections = [
            'race_performance',
            'race_performance_analysis',
            'race_horse_performance',
            'race_incidents',
            'race_incident_analysis',
            'race_payouts',
            'race_payout_pools',
            'race_payout_analysis'
        ]

        # Clean up ALL July 2025 dates for fresh manual restart
        self.july_dates = ["2025/07/01", "2025/07/05"]
    
    def authenticate(self):
        """Authenticate with PocketBase and get auth token."""
        try:
            auth_url = urljoin(self.base_url, '/api/collections/users/auth-with-password')
            auth_data = {
                'identity': self.email,
                'password': self.password
            }

            response = self.session.post(auth_url, json=auth_data)
            response.raise_for_status()

            auth_result = response.json()
            self.auth_token = auth_result.get('token')

            if self.auth_token:
                self.session.headers.update({
                    'Authorization': f'Bearer {self.auth_token}',
                    'Content-Type': 'application/json'
                })
                print("✅ Successfully authenticated with PocketBase")
                return True
            else:
                print("❌ Failed to get auth token")
                return False

        except Exception as e:
            print(f"❌ Authentication failed: {str(e)}")
            return False
    
    def find_july_records(self, collection_name, race_date):
        """Find all records for a specific July 2025 date in a collection."""
        try:
            search_url = urljoin(self.base_url, f'/api/collections/{collection_name}/records')

            # race_payout_pools uses race_id instead of race_date
            if collection_name == 'race_payout_pools':
                # Convert 2025/07/01 to race_id pattern like "2025-07-01_ST_R1"
                date_for_race_id = race_date.replace('/', '-')  # 2025/07/01 -> 2025-07-01
                search_params = {
                    'filter': f'race_id~"{date_for_race_id}"',
                    'perPage': 500  # Get all records
                }
            else:
                # Other collections use race_date
                search_params = {
                    'filter': f'race_date="{race_date}"',
                    'perPage': 500  # Get all records
                }

            response = self.session.get(search_url, params=search_params)

            if response.status_code == 200:
                records = response.json().get('items', [])
                return records
            else:
                print(f"⚠️ Failed to search {collection_name} for {race_date}: {response.status_code}")
                return []

        except Exception as e:
            print(f"❌ Error searching {collection_name} for {race_date}: {e}")
            return []
    
    def delete_record(self, collection_name, record_id):
        """Delete a specific record from a collection."""
        try:
            delete_url = urljoin(self.base_url, f'/api/collections/{collection_name}/records/{record_id}')
            response = self.session.delete(delete_url)
            
            if response.status_code == 204:
                return True
            else:
                print(f"⚠️ Failed to delete record {record_id} from {collection_name}: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error deleting record {record_id} from {collection_name}: {e}")
            return False
    
    def cleanup_collection_for_date(self, collection_name, race_date):
        """Clean up all records for a specific date in a collection."""
        print(f"  🔍 Searching {collection_name} for {race_date}...")

        records = self.find_july_records(collection_name, race_date)

        if not records:
            print(f"    ✅ No records found in {collection_name} for {race_date}")
            return []

        print(f"    ⚠️ Found {len(records)} records in {collection_name} for {race_date}")

        # Show details of what will be deleted
        for record in records[:5]:  # Show first 5 records
            if collection_name == 'race_payout_pools':
                race_id = record.get('race_id', 'Unknown')
                pool_type = record.get('pool_type', 'Unknown')
                print(f"      - ID: {record['id']} | {race_id} {pool_type}")
            else:
                venue = record.get('racecourse', record.get('venue', 'Unknown'))
                race_num = record.get('race_number', 'Unknown')
                print(f"      - ID: {record['id']} | {venue} Race {race_num}")

        if len(records) > 5:
            print(f"      ... and {len(records) - 5} more records")

        return records
    
    def cleanup_all_july_records(self):
        """Clean up all July 2025 records from all collections."""
        print("🧹 Starting cleanup of July 2025 records from all collections...")
        print(f"📅 Target dates: {', '.join(self.july_dates)}")
        print(f"🗄️ Target collections: {', '.join(self.collections)}")
        print()
        
        # First, scan all collections to see what we have
        all_records_to_delete = {}
        total_records = 0
        
        for race_date in self.july_dates:
            print(f"📅 Scanning {race_date}...")
            all_records_to_delete[race_date] = {}
            
            for collection_name in self.collections:
                records = self.cleanup_collection_for_date(collection_name, race_date)
                all_records_to_delete[race_date][collection_name] = records
                total_records += len(records)
            
            print()
        
        if total_records == 0:
            print("✅ No July 2025 records found to delete!")
            return 0
        
        # Show summary and confirm
        print(f"📊 DELETION SUMMARY:")
        print(f"Total records to delete: {total_records}")
        print()
        
        for race_date in self.july_dates:
            date_total = sum(len(records) for records in all_records_to_delete[race_date].values())
            if date_total > 0:
                print(f"  📅 {race_date}: {date_total} records")
                for collection_name, records in all_records_to_delete[race_date].items():
                    if records:
                        print(f"    - {collection_name}: {len(records)} records")
        
        print()
        confirm = input(f"⚠️ Delete all {total_records} records? (yes/no): ").lower().strip()
        
        if confirm != 'yes':
            print("❌ Deletion cancelled by user")
            return 0
        
        # Perform deletions
        print("\n🗑️ Starting deletion process...")
        total_deleted = 0
        total_failed = 0
        
        for race_date in self.july_dates:
            for collection_name, records in all_records_to_delete[race_date].items():
                if records:
                    print(f"  Deleting {len(records)} records from {collection_name} for {race_date}...")
                    
                    for record in records:
                        if self.delete_record(collection_name, record['id']):
                            total_deleted += 1
                        else:
                            total_failed += 1
        
        print(f"\n📊 Deletion completed: ✅ {total_deleted} deleted, ❌ {total_failed} failed")
        return total_deleted
    
    def verify_cleanup(self):
        """Verify that all July 2025 records have been removed."""
        print("🔍 Verifying cleanup...")
        
        remaining_records = 0
        
        for race_date in self.july_dates:
            print(f"  📅 Checking {race_date}...")
            
            for collection_name in self.collections:
                records = self.find_july_records(collection_name, race_date)
                if records:
                    print(f"    ⚠️ {collection_name}: {len(records)} records still remain")
                    remaining_records += len(records)
                else:
                    print(f"    ✅ {collection_name}: Clean")
        
        if remaining_records == 0:
            print("✅ All July 2025 records have been successfully removed!")
            return True
        else:
            print(f"⚠️ {remaining_records} records still remain - cleanup incomplete")
            return False

def main():
    """Main cleanup function."""
    print("🏇 HKJC July 2025 Complete Cleanup")
    print("=" * 60)
    print("This script will remove ALL July 2025 records from PocketBase")
    print("Target dates: 2025/07/01 and 2025/07/05 (complete cleanup)")
    print("Purpose: Fresh start for manual pipeline execution")
    print("Target collections: All 8 collections (including race_payout_pools)")
    print("=" * 60)
    print()
    
    # Initialize cleaner
    cleaner = July2025Cleaner()
    
    # Authenticate
    if not cleaner.authenticate():
        print("❌ Failed to authenticate - cannot proceed")
        return
    
    # Perform cleanup
    total_deleted = cleaner.cleanup_all_july_records()
    
    # Verify cleanup
    cleanup_success = cleaner.verify_cleanup()
    
    # Final summary
    print()
    print("=" * 60)
    print("🎯 CLEANUP SUMMARY:")
    print(f"🗑️ Total records deleted: {total_deleted}")
    print(f"✅ Cleanup successful: {'Yes' if cleanup_success else 'No'}")
    
    if cleanup_success and total_deleted > 0:
        print("🎉 All July 2025 records have been successfully removed!")
    elif total_deleted == 0:
        print("ℹ️ No July 2025 records were found to delete")
    else:
        print("⚠️ Some records may still remain - please check manually")
    
    print("=" * 60)

if __name__ == '__main__':
    main()
