#!/usr/bin/env python3
"""
Check specifically for July 2025 records in race_payout_pools collection.
"""

import os
import requests
from urllib.parse import urljoin
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class PayoutPoolsChecker:
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
    
    def search_july_records(self):
        """Search for any July 2025 records in race_payout_pools collection."""
        try:
            records_url = urljoin(self.base_url, f'/api/collections/race_payout_pools/records')
            
            # Try different date filters
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
                params = {'filter': date_filter, 'perPage': 500}
                response = self.session.get(records_url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    records = data.get('items', [])
                    if records:
                        july_records.extend(records)
                        print(f"Found {len(records)} records with filter: {date_filter}")
            
            # Remove duplicates based on ID
            unique_records = {}
            for record in july_records:
                unique_records[record['id']] = record
            
            july_records = list(unique_records.values())
            
            if july_records:
                print(f"\n🎯 Found {len(july_records)} July 2025 records in race_payout_pools:")
                for record in july_records:
                    race_date = record.get('race_date', 'N/A')
                    venue = record.get('racecourse', record.get('venue', 'N/A'))
                    race_num = record.get('race_number', 'N/A')
                    pool_type = record.get('pool_type', 'N/A')
                    print(f"     - ID: {record['id']} | {race_date} {venue} R{race_num} {pool_type}")
            else:
                print(f"\n✅ No July 2025 records found in race_payout_pools")
            
            return july_records
            
        except Exception as e:
            print(f"❌ Error searching July records in race_payout_pools: {e}")
            return []
    
    def check_total_records(self):
        """Check total number of records in race_payout_pools."""
        try:
            records_url = urljoin(self.base_url, f'/api/collections/race_payout_pools/records')
            params = {'perPage': 1}  # Just get count
            
            response = self.session.get(records_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                total_count = data.get('totalItems', 0)
                print(f"📊 Total records in race_payout_pools: {total_count}")
                return total_count
            else:
                print(f"⚠️ Failed to check race_payout_pools: {response.status_code}")
                return 0
                
        except Exception as e:
            print(f"❌ Error checking race_payout_pools: {e}")
            return 0

def main():
    """Main function."""
    print("🔍 Checking race_payout_pools for July 2025 records")
    print("=" * 50)
    
    checker = PayoutPoolsChecker()
    
    if not checker.authenticate():
        print("❌ Failed to authenticate - cannot proceed")
        return
    
    # Check total records
    checker.check_total_records()
    
    # Search for July 2025 records
    july_records = checker.search_july_records()
    
    print(f"\n📋 Summary:")
    print(f"July 2025 records found: {len(july_records)}")

if __name__ == '__main__':
    main()
