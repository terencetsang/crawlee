# HKJC Race Data Pipeline Documentation

## Overview

This pipeline extracts, processes, and uploads Hong Kong Jockey Club (HKJC) race data to PocketBase. The system includes safety features to prevent processing of future race dates and comprehensive cleanup tools.

## Pipeline Components

### Core Scripts

1. **`extract_race_dates_to_json.py`** - Extracts available race dates from HKJC website
2. **`batch_extract_races.py`** - Batch extraction of race data with safety filters
3. **`upload_all_simple.py`** - Uploads processed data to PocketBase collections
4. **`run_complete_pipeline.sh`** - Orchestrates the complete pipeline execution

### Safety & Cleanup Tools

5. **`cleanup_july_2025_records.py`** - Removes records from all PocketBase collections
6. **`check_pocketbase_collections.py`** - Verifies collection states and searches for records
7. **`check_payout_pools.py`** - Specific checker for race_payout_pools collection

## Safety Features

### Automatic Future Date Protection

The pipeline now includes a **safety filter** that prevents processing of upcoming races by default:

```bash
# Safe execution - excludes upcoming races automatically
python3 batch_extract_races.py --month 2025/07

# Override safety filter to include upcoming races
python3 batch_extract_races.py --month 2025/07 --allow-upcoming
```

**Safety Messages:**
- `🛡️ Safety filter: Excluding 'upcoming' races (use --allow-upcoming to override)`

### Date Status Types

- **`completed`** - Past races with final results ✅ (Safe to process)
- **`today`** - Current day races ⚠️ (Process with caution)
- **`upcoming`** - Future races ❌ (Excluded by default)

## PocketBase Collections

The pipeline uploads data to **8 collections**:

1. **`race_performance`** - Overall race results and statistics
2. **`race_performance_analysis`** - Analyzed race performance data
3. **`race_horse_performance`** - Individual horse performance records
4. **`race_incidents`** - Race incidents and events
5. **`race_incident_analysis`** - Analyzed incident data
6. **`race_payouts`** - Payout information for different bet types
7. **`race_payout_pools`** - Pool-specific payout data (uses `race_id` field)
8. **`race_payout_analysis`** - Analyzed payout data

### Special Collection: race_payout_pools

**Important:** The `race_payout_pools` collection uses `race_id` instead of `race_date`:
- **Format:** `2025-07-01_ST_R1` (not `2025/07/01`)
- **Contains:** Pool types like 獨贏, 位置, 連贏, etc.

## Pipeline Execution

### Manual Execution

```bash
# 1. Extract race dates
python3 extract_race_dates_to_json.py

# 2. Extract race data (with safety filter)
python3 batch_extract_races.py --month 2025/07 --status completed

# 3. Upload to PocketBase
python3 upload_all_simple.py
```

### Automated Pipeline

```bash
# Complete pipeline for specific month
./run_complete_pipeline.sh --month 2025/07

# Predefined options
./run_complete_pipeline.sh
# Choose from: recent_10, recent_20, june_2025, etc.
```

## Cleanup & Verification

### Complete Cleanup

Remove all records for specific dates:

```bash
# Clean all July 2025 records from all collections
python3 cleanup_july_2025_records.py
```

**Features:**
- Handles all 8 collections including `race_payout_pools`
- Shows detailed preview before deletion
- Confirms each collection cleanup
- Verifies complete removal

### Verification Tools

```bash
# Check all collections for July 2025 records
python3 check_pocketbase_collections.py

# Specific check for race_payout_pools
python3 check_payout_pools.py
```

## Common Use Cases

### 1. Process New Month Data

```bash
# Safe processing (excludes upcoming races)
./run_complete_pipeline.sh --month 2025/08
```

### 2. Clean Up Incorrect Data

```bash
# Remove all July 2025 records
python3 cleanup_july_2025_records.py

# Verify cleanup
python3 check_pocketbase_collections.py
```

### 3. Process Specific Date Range

```bash
# Extract only completed races from July 2025
python3 batch_extract_races.py --month 2025/07 --status completed

# Extract recent 10 races
python3 batch_extract_races.py --limit 10 --status completed
```

### 4. Emergency: Include Future Dates

```bash
# Override safety filter (use with caution!)
python3 batch_extract_races.py --month 2025/07 --allow-upcoming
```

## Error Prevention

### Before Running Pipeline

1. **Check race_dates.json** - Verify date statuses
2. **Review target dates** - Ensure no upcoming races unless intended
3. **Backup consideration** - Consider data backup for large operations

### After Running Pipeline

1. **Verify uploads** - Check all 8 collections have data
2. **Validate dates** - Ensure no future dates were processed
3. **Check counts** - Verify expected number of records

## Troubleshooting

### Issue: Future Date Records Created

**Symptoms:** Records exist for upcoming race dates

**Solution:**
```bash
# 1. Clean up the incorrect records
python3 cleanup_july_2025_records.py

# 2. Verify cleanup
python3 check_pocketbase_collections.py

# 3. Re-run with safety filter
python3 batch_extract_races.py --month 2025/07 --status completed
```

### Issue: Missing race_payout_pools Data

**Symptoms:** Other collections have data but race_payout_pools is empty

**Solution:**
```bash
# Check specifically for race_payout_pools
python3 check_payout_pools.py

# The collection uses race_id format: 2025-07-01_ST_R1
```

### Issue: Safety Filter Too Restrictive

**Symptoms:** No dates selected for processing

**Solution:**
```bash
# Check what dates are available
python3 batch_extract_races.py --month 2025/07 --status completed

# If you need to process upcoming races (use carefully!)
python3 batch_extract_races.py --month 2025/07 --allow-upcoming
```

## Configuration

### Environment Variables

```bash
POCKETBASE_URL=http://terence.myds.me:8081
POCKETBASE_EMAIL=terencetsang@hotmail.com
POCKETBASE_PASSWORD=Qwertyu12345
```

### File Locations

- **Race dates:** `race_dates.json`
- **Performance data:** `performance_data/performance_YYYY-MM-DD_VENUE_RN.json`
- **Logs:** Console output with emoji indicators

## Best Practices

1. **Always use safety filter** - Let the system exclude upcoming races automatically
2. **Verify before cleanup** - Check what will be deleted before confirming
3. **Process completed races** - Use `--status completed` for reliable data
4. **Check all collections** - Verify data in all 8 collections after upload
5. **Monitor race_payout_pools** - This collection has different field structure

## Safety Indicators

- 🛡️ Safety filter active
- ✅ Safe operation completed
- ⚠️ Caution required
- ❌ Unsafe operation blocked
- 🎯 Target achieved
- 🧹 Cleanup operation
- 📊 Data verification

---

**Last Updated:** 2025-07-04  
**Pipeline Version:** 2.0 (with safety features)
