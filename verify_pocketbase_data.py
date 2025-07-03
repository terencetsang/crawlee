import json
import os
import glob
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

# Output directory for JSON files
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "odds_data")

def get_all_local_json_files():
    """Get all local JSON files with race data"""
    try:
        print("📁 Scanning local JSON files...")
        
        # Look for win odds trends files
        pattern = f"{OUTPUT_DIR}/win_odds_trends_*.json"
        json_files = glob.glob(pattern)
        
        local_races = {}
        
        for json_file in json_files:
            try:
                # Extract race info from filename
                # Format: win_odds_trends_2025_06_26_ST_R1.json
                filename = os.path.basename(json_file)
                parts = filename.replace('.json', '').split('_')
                
                if len(parts) >= 7:
                    # Extract date, venue, race number
                    year = parts[3]
                    month = parts[4]
                    day = parts[5]
                    venue = parts[6]
                    race_num = parts[7][1:]  # Remove 'R' prefix
                    
                    race_date = f"{year}-{month}-{day}"
                    race_key = f"{race_date}_{venue}_{race_num}"
                    
                    # Load and validate JSON content
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Extract key information
                    horses_count = len(data.get('horses_data', []))
                    extraction_status = data.get('extraction_summary', {}).get('data_extraction_successful', False)
                    
                    local_races[race_key] = {
                        'file_path': json_file,
                        'race_date': race_date,
                        'venue': venue,
                        'race_number': int(race_num),
                        'horses_count': horses_count,
                        'extraction_successful': extraction_status,
                        'file_size': os.path.getsize(json_file),
                        'data': data
                    }
                    
            except Exception as e:
                print(f"   ⚠️ Error processing {json_file}: {str(e)}")
                continue
        
        print(f"✅ Found {len(local_races)} local race files")
        return local_races
        
    except Exception as e:
        print(f"❌ Error scanning local files: {str(e)}")
        return {}

def get_all_pocketbase_records():
    """Get all records from PocketBase"""
    try:
        print("🗄️ Fetching all PocketBase records...")
        
        client = PocketBase(POCKETBASE_URL)
        client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
        
        # Get all records
        all_records = client.collection(COLLECTION_NAME).get_full_list()
        
        pocketbase_races = {}
        
        for record in all_records:
            race_key = f"{record.race_date}_{record.venue}_{record.race_number}"
            
            # Handle complete_data (could be dict or string)
            try:
                if isinstance(record.complete_data, dict):
                    complete_data = record.complete_data
                else:
                    complete_data = json.loads(record.complete_data)
                horses_count = len(complete_data.get('horses_data', []))
            except:
                complete_data = {}
                horses_count = 0
            
            pocketbase_races[race_key] = {
                'record_id': record.id,
                'race_date': record.race_date,
                'venue': record.venue,
                'race_number': record.race_number,
                'data_type': record.data_type,
                'extraction_status': record.extraction_status,
                'horses_count': horses_count,
                'scraped_at': record.scraped_at,
                'source_url': record.source_url,
                'complete_data': complete_data
            }
        
        print(f"✅ Found {len(pocketbase_races)} PocketBase records")
        return pocketbase_races
        
    except Exception as e:
        print(f"❌ Error fetching PocketBase records: {str(e)}")
        return {}

def compare_local_vs_pocketbase(local_races, pocketbase_races):
    """Compare local files vs PocketBase records"""
    print("\n🔍 Comparing local files vs PocketBase records...")
    
    # Find missing uploads
    missing_in_pocketbase = []
    for race_key in local_races:
        if race_key not in pocketbase_races:
            missing_in_pocketbase.append(race_key)
    
    # Find extra records in PocketBase
    extra_in_pocketbase = []
    for race_key in pocketbase_races:
        if race_key not in local_races:
            extra_in_pocketbase.append(race_key)
    
    # Find data mismatches
    data_mismatches = []
    for race_key in local_races:
        if race_key in pocketbase_races:
            local_data = local_races[race_key]
            pb_data = pocketbase_races[race_key]
            
            # Compare key fields
            mismatches = []
            
            if local_data['horses_count'] != pb_data['horses_count']:
                mismatches.append(f"horses_count: local={local_data['horses_count']}, pb={pb_data['horses_count']}")
            
            if local_data['race_date'] != pb_data['race_date']:
                mismatches.append(f"race_date: local={local_data['race_date']}, pb={pb_data['race_date']}")
            
            if local_data['venue'] != pb_data['venue']:
                mismatches.append(f"venue: local={local_data['venue']}, pb={pb_data['venue']}")
            
            if local_data['race_number'] != pb_data['race_number']:
                mismatches.append(f"race_number: local={local_data['race_number']}, pb={pb_data['race_number']}")
            
            if mismatches:
                data_mismatches.append({
                    'race_key': race_key,
                    'mismatches': mismatches
                })
    
    return missing_in_pocketbase, extra_in_pocketbase, data_mismatches

def upload_missing_races(missing_races, local_races):
    """Upload missing races to PocketBase"""
    if not missing_races:
        return True
    
    print(f"\n📤 Uploading {len(missing_races)} missing races to PocketBase...")
    
    try:
        client = PocketBase(POCKETBASE_URL)
        client.collection("users").auth_with_password(POCKETBASE_EMAIL, POCKETBASE_PASSWORD)
        
        successful_uploads = 0
        failed_uploads = 0
        
        for race_key in missing_races:
            try:
                local_data = local_races[race_key]
                
                print(f"   📤 Uploading {race_key}...")
                
                # Prepare record data
                record_data = {
                    "race_date": local_data['race_date'],
                    "venue": local_data['venue'],
                    "race_number": local_data['race_number'],
                    "data_type": "win_odds_trends",
                    "complete_data": json.dumps(local_data['data'], ensure_ascii=False),
                    "scraped_at": datetime.now().isoformat(),
                    "source_url": local_data['data']['race_info']['source_url'],
                    "extraction_status": "success" if local_data['extraction_successful'] else "partial"
                }
                
                # Create record
                result = client.collection(COLLECTION_NAME).create(record_data)
                print(f"      ✅ Created record: {result.id}")
                successful_uploads += 1
                
            except Exception as e:
                print(f"      ❌ Failed to upload {race_key}: {str(e)}")
                failed_uploads += 1
        
        print(f"\n📊 Upload summary: {successful_uploads} successful, {failed_uploads} failed")
        return failed_uploads == 0
        
    except Exception as e:
        print(f"❌ Error during upload: {str(e)}")
        return False

def generate_verification_report(local_races, pocketbase_races, missing_in_pb, extra_in_pb, data_mismatches):
    """Generate a comprehensive verification report"""
    try:
        report = {
            "verification_timestamp": datetime.now().isoformat(),
            "summary": {
                "total_local_files": len(local_races),
                "total_pocketbase_records": len(pocketbase_races),
                "missing_in_pocketbase": len(missing_in_pb),
                "extra_in_pocketbase": len(extra_in_pb),
                "data_mismatches": len(data_mismatches),
                "verification_status": "PASS" if len(missing_in_pb) == 0 and len(data_mismatches) == 0 else "FAIL"
            },
            "local_files_summary": {},
            "pocketbase_summary": {},
            "issues": {
                "missing_in_pocketbase": missing_in_pb,
                "extra_in_pocketbase": extra_in_pb,
                "data_mismatches": data_mismatches
            }
        }
        
        # Summarize local files by date
        for race_key, data in local_races.items():
            date = data['race_date']
            if date not in report["local_files_summary"]:
                report["local_files_summary"][date] = {"ST": 0, "HV": 0}
            report["local_files_summary"][date][data['venue']] += 1
        
        # Summarize PocketBase records by date
        for race_key, data in pocketbase_races.items():
            date = data['race_date']
            if date not in report["pocketbase_summary"]:
                report["pocketbase_summary"][date] = {"ST": 0, "HV": 0}
            report["pocketbase_summary"][date][data['venue']] += 1
        
        # Save report
        with open('pocketbase_verification_report.json', 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📋 Generated verification report: pocketbase_verification_report.json")
        return report
        
    except Exception as e:
        print(f"❌ Error generating report: {str(e)}")
        return None

def main():
    """Main verification function"""
    print("🏇 HKJC PocketBase Data Verification")
    print("=" * 60)
    
    # Step 1: Get local files
    local_races = get_all_local_json_files()
    
    # Step 2: Get PocketBase records
    pocketbase_races = get_all_pocketbase_records()
    
    # Step 3: Compare data
    missing_in_pb, extra_in_pb, data_mismatches = compare_local_vs_pocketbase(local_races, pocketbase_races)
    
    # Step 4: Display results
    print(f"\n" + "=" * 60)
    print("📊 VERIFICATION RESULTS:")
    print(f"📁 Local JSON files: {len(local_races)}")
    print(f"🗄️ PocketBase records: {len(pocketbase_races)}")
    print(f"❌ Missing in PocketBase: {len(missing_in_pb)}")
    print(f"➕ Extra in PocketBase: {len(extra_in_pb)}")
    print(f"⚠️ Data mismatches: {len(data_mismatches)}")
    
    if missing_in_pb:
        print(f"\n❌ Missing races in PocketBase:")
        for race_key in missing_in_pb:
            print(f"   - {race_key}")
    
    if extra_in_pb:
        print(f"\n➕ Extra races in PocketBase (not in local files):")
        for race_key in extra_in_pb:
            print(f"   - {race_key}")
    
    if data_mismatches:
        print(f"\n⚠️ Data mismatches:")
        for mismatch in data_mismatches:
            print(f"   - {mismatch['race_key']}: {', '.join(mismatch['mismatches'])}")
    
    # Step 5: Upload missing races if any
    if missing_in_pb:
        upload_success = upload_missing_races(missing_in_pb, local_races)
        if upload_success:
            print(f"✅ All missing races uploaded successfully!")
            # Re-fetch PocketBase data to verify
            pocketbase_races = get_all_pocketbase_records()
        else:
            print(f"❌ Some uploads failed")
    
    # Step 6: Generate report
    report = generate_verification_report(local_races, pocketbase_races, missing_in_pb, extra_in_pb, data_mismatches)
    
    # Step 7: Final status
    print(f"\n" + "=" * 60)
    if report and report["summary"]["verification_status"] == "PASS":
        print("🎉 VERIFICATION PASSED: All data is correctly uploaded!")
    else:
        print("⚠️ VERIFICATION ISSUES: Please check the report for details")
    
    print(f"📋 Detailed report saved to: pocketbase_verification_report.json")
    print("=" * 60)

if __name__ == '__main__':
    main()
