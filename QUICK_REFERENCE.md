# HKJC Pipeline Quick Reference

## 🚀 Common Commands

### Run Complete Pipeline
```bash
# Safe execution (excludes upcoming races)
./run_complete_pipeline.sh --month 2025/07

# Interactive mode with predefined options
./run_complete_pipeline.sh
```

### Manual Steps
```bash
# 1. Extract race dates
python3 extract_race_dates_to_json.py

# 2. Extract race data (safe mode)
python3 batch_extract_races.py --month 2025/07 --status completed

# 3. Upload to PocketBase
python3 upload_all_simple.py
```

## 🧹 Cleanup Commands

### Remove All Records for Specific Month
```bash
# Clean all July 2025 records from all 8 collections
python3 cleanup_july_2025_records.py
```

### Verify Collections
```bash
# Check all collections for July 2025 records
python3 check_pocketbase_collections.py

# Check specific race_payout_pools collection
python3 check_payout_pools.py
```

## 🛡️ Safety Features

### Default Behavior (SAFE)
- Automatically excludes upcoming races
- Only processes completed and today's races
- Shows safety filter messages

### Override Safety (USE WITH CAUTION)
```bash
# Include upcoming races
python3 batch_extract_races.py --month 2025/07 --allow-upcoming
```

## 📊 Collection Overview

| Collection | Records per Race | Field Type | Notes |
|------------|------------------|------------|-------|
| race_performance | 1 | race_date | Overall race results |
| race_performance_analysis | 1 | race_date | Analyzed performance |
| race_horse_performance | ~10-14 | race_date | Individual horses |
| race_incidents | ~10-14 | race_date | Race incidents |
| race_incident_analysis | 1 | race_date | Analyzed incidents |
| race_payouts | 1 | race_date | Payout summary |
| race_payout_pools | ~30-50 | **race_id** | Pool details |
| race_payout_analysis | 1 | race_date | Analyzed payouts |

## ⚠️ Important Notes

### race_payout_pools Collection
- Uses `race_id` field: `2025-07-01_ST_R1`
- Contains pool types: 獨贏, 位置, 連贏, etc.
- Different search pattern in cleanup scripts

### Date Formats
- **race_dates.json**: `2025/07/01`
- **PocketBase race_date**: `2025/07/01`
- **PocketBase race_id**: `2025-07-01_ST_R1`
- **Performance files**: `performance_2025-07-01_ST_R1.json`

## 🎯 Status Indicators

| Status | Symbol | Meaning | Action |
|--------|--------|---------|--------|
| completed | ✅ | Past race with results | Safe to process |
| today | ⚠️ | Current day race | Process with caution |
| upcoming | ❌ | Future race | Excluded by default |

## 🔧 Troubleshooting

### Problem: Future date records created
```bash
# 1. Clean up
python3 cleanup_july_2025_records.py

# 2. Verify
python3 check_pocketbase_collections.py

# 3. Re-run safely
python3 batch_extract_races.py --month 2025/07 --status completed
```

### Problem: No dates selected
```bash
# Check available dates
python3 batch_extract_races.py --month 2025/07 --limit 5

# If needed, override safety (careful!)
python3 batch_extract_races.py --month 2025/07 --allow-upcoming
```

### Problem: Missing race_payout_pools data
```bash
# Check specifically
python3 check_payout_pools.py

# Look for race_id pattern: 2025-07-01_ST_R1
```

## 📁 File Structure

```
crawlee/
├── batch_extract_races.py          # Main extraction script
├── cleanup_july_2025_records.py    # Cleanup tool
├── check_pocketbase_collections.py # Verification tool
├── check_payout_pools.py           # Specific checker
├── run_complete_pipeline.sh        # Pipeline orchestrator
├── race_dates.json                 # Available race dates
├── performance_data/               # Extracted race data
│   └── performance_YYYY-MM-DD_VENUE_RN.json
└── PIPELINE_DOCUMENTATION.md       # Full documentation
```

## 🚨 Emergency Commands

### Complete Reset for July 2025
```bash
# 1. Remove all July 2025 records
python3 cleanup_july_2025_records.py

# 2. Remove local files
rm -f performance_data/performance_2025-07-*

# 3. Verify clean state
python3 check_pocketbase_collections.py

# 4. Fresh start
./run_complete_pipeline.sh --month 2025/07
```

### Quick Health Check
```bash
# Check what July 2025 data exists
python3 check_pocketbase_collections.py | grep "July 2025"

# Check recent pipeline runs
ls -la performance_data/performance_2025-07-*
```

---

**💡 Remember:** The pipeline now has safety features that prevent future date processing by default. Always verify your target dates before running cleanup operations!
