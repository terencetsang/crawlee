import json
from dotenv import load_dotenv
from pocketbase import PocketBase

# Load environment variables
load_dotenv()

# PocketBase configuration
POCKETBASE_URL = "http://terence.myds.me:8081"
POCKETBASE_EMAIL = "terencetsang@hotmail.com"
POCKETBASE_PASSWORD = "Qwertyu12345"
COLLECTION_NAME = "race_odds"

def debug_pocketbase_record():
    """Debug a single PocketBase record to see the data structure"""
    try:
        client = PocketBase(POCKETBASE_URL)
        client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
        
        # Get first record
        records = client.collection(COLLECTION_NAME).get_list(1, 1)
        
        if records.items:
            record = records.items[0]
            print(f"Record ID: {record.id}")
            print(f"Race Date: {record.race_date}")
            print(f"Venue: {record.venue}")
            print(f"Race Number: {record.race_number}")
            print(f"Data Type: {record.data_type}")
            print(f"Extraction Status: {record.extraction_status}")
            print(f"Source URL: {record.source_url}")
            print(f"Scraped At: {record.scraped_at}")
            
            # Check complete_data field
            print(f"\nComplete Data Type: {type(record.complete_data)}")
            print(f"Complete Data Length: {len(str(record.complete_data))}")
            print(f"First 200 chars: {str(record.complete_data)[:200]}")
            
            # Try to parse JSON
            try:
                if isinstance(record.complete_data, str):
                    data = json.loads(record.complete_data)
                    print(f"\n✅ JSON parsing successful")
                    print(f"Keys in data: {list(data.keys())}")
                    if 'horses_data' in data:
                        print(f"Number of horses: {len(data['horses_data'])}")
                        if data['horses_data']:
                            print(f"First horse: {data['horses_data'][0]}")
                else:
                    print(f"\n⚠️ complete_data is not a string: {type(record.complete_data)}")
                    print(f"Value: {record.complete_data}")
            except json.JSONDecodeError as e:
                print(f"\n❌ JSON parsing failed: {e}")
                print(f"Raw data: {record.complete_data}")
        else:
            print("No records found")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    debug_pocketbase_record()
