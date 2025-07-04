#!/usr/bin/env python3
"""
Check what collections exist in PocketBase and what data they contain.
This will help us understand where the July 2025 records might be.
"""

import os
import requests
from urllib.parse import urljoin
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class PocketBaseChecker:
    def __init__(self):
        self.base_url = os.getenv("POCKETBASE_URL", "http://terence.myds.me:8081").rstrip('/')
        self.email = os.getenv("POCKETBASE_EMAIL", "terencetsang@hotmail.com")
        self.password = os.getenv("POCKETBASE_PASSWORD", "Qwertyu12345")
        self.auth_token = None
        self.session = requests.Session()
    
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
    
    def list_collections(self):
        """List all collections in PocketBase."""
        try:
            collections_url = urljoin(self.base_url, '/api/collections')
            response = self.session.get(collections_url)
            
            if response.status_code == 200:
                collections_data = response.json()
                collections = collections_data.get('items', [])
                
                print(f"📋 Found {len(collections)} collections:")
                for collection in collections:
                    print(f"  - {collection['name']} ({collection['type']})")
                
                return [col['name'] for col in collections if col['type'] == 'base']
            else:
                print(f"❌ Failed to list collections: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error listing collections: {e}")
            return []
    
    def check_collection_data(self, collection_name, limit=5):
        """Check what data exists in a collection."""
        try:
            records_url = urljoin(self.base_url, f'/api/collections/{collection_name}/records')
            params = {'perPage': limit, 'sort': '-created'}
            
            response = self.session.get(records_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                records = data.get('items', [])
                total_count = data.get('totalItems', 0)
                
                print(f"\n📊 Collection: {collection_name}")
                print(f"   Total records: {total_count}")
                
                if records:
                    print(f"   Recent records:")
                    for record in records:
                        # Try to extract key fields
                        race_date = record.get('race_date', 'N/A')
                        venue = record.get('racecourse', record.get('venue', 'N/A'))
                        race_num = record.get('race_number', 'N/A')
                        created = record.get('created', 'N/A')[:10]  # Just date part
                        
                        print(f"     - {race_date} {venue} R{race_num} (created: {created})")
                else:
                    print(f"   No records found")
                
                return total_count
            else:
                print(f"⚠️ Failed to check {collection_name}: {response.status_code}")
                return 0
                
        except Exception as e:
            print(f"❌ Error checking {collection_name}: {e}")
            return 0
    
    def search_july_records(self, collection_name):
        """Search for any July 2025 records in a collection."""
        try:
            records_url = urljoin(self.base_url, f'/api/collections/{collection_name}/records')
            
            # Try different date formats
            date_filters = [
                'race_date~"2025-07"',
                'race_date~"2025/07"', 
                'race_date~"07/2025"',
                'race_date="2025-07-01"',
                'race_date="2025-07-05"',
                'race_date="2025/07/01"',
                'race_date="2025/07/05"'
            ]
            
            july_records = []
            
            for date_filter in date_filters:
                params = {'filter': date_filter, 'perPage': 100}
                response = self.session.get(records_url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    records = data.get('items', [])
                    if records:
                        july_records.extend(records)
            
            # Remove duplicates based on ID
            unique_records = {}
            for record in july_records:
                unique_records[record['id']] = record
            
            july_records = list(unique_records.values())
            
            if july_records:
                print(f"\n🎯 Found {len(july_records)} July 2025 records in {collection_name}:")
                for record in july_records:
                    race_date = record.get('race_date', 'N/A')
                    venue = record.get('racecourse', record.get('venue', 'N/A'))
                    race_num = record.get('race_number', 'N/A')
                    print(f"     - ID: {record['id']} | {race_date} {venue} R{race_num}")
            
            return july_records
            
        except Exception as e:
            print(f"❌ Error searching July records in {collection_name}: {e}")
            return []
    
    def comprehensive_check(self):
        """Perform a comprehensive check of all collections."""
        print("🔍 Comprehensive PocketBase Check")
        print("=" * 50)

        # Use known collections since we can't list them
        known_collections = [
            'race_performance',
            'race_performance_analysis',
            'race_horse_performance',
            'race_incidents',
            'race_incident_analysis',
            'race_payouts',
            'race_payout_pools',
            'race_payout_analysis'
        ]

        print(f"📋 Checking known collections: {', '.join(known_collections)}")

        # Check each collection for data
        print(f"\n📊 Checking data in each collection...")
        total_records = 0
        existing_collections = []

        for collection_name in known_collections:
            count = self.check_collection_data(collection_name)
            if count >= 0:  # Include collections even if they have 0 records
                existing_collections.append(collection_name)
            total_records += count

        print(f"\n📈 Total records across all collections: {total_records}")
        print(f"📋 Collections with data: {', '.join(existing_collections)}")

        # Search specifically for July 2025 records
        print(f"\n🎯 Searching for July 2025 records...")
        all_july_records = {}

        for collection_name in known_collections:  # Search all collections, not just existing ones
            july_records = self.search_july_records(collection_name)
            if july_records:
                all_july_records[collection_name] = july_records

        if all_july_records:
            print(f"\n⚠️ FOUND JULY 2025 RECORDS:")
            total_july = 0
            for collection_name, records in all_july_records.items():
                print(f"   {collection_name}: {len(records)} records")
                total_july += len(records)
            print(f"   Total July 2025 records: {total_july}")
        else:
            print(f"\n✅ No July 2025 records found in any collection")

def main():
    """Main function."""
    checker = PocketBaseChecker()
    
    if not checker.authenticate():
        print("❌ Failed to authenticate - cannot proceed")
        return
    
    checker.comprehensive_check()

if __name__ == '__main__':
    main()
