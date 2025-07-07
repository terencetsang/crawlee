# Pipeline Changelog

## [2.0.0] - 2025-07-04

### 🛡️ Major Safety Features Added

#### Automatic Future Date Protection
- **Added safety filter** to `batch_extract_races.py` that excludes upcoming races by default
- **New flag `--allow-upcoming`** to override safety filter when needed
- **Prevents accidental processing** of future race dates

#### Enhanced Date Filtering
```python
# Before: Processed all dates regardless of status
filtered_dates = filter_dates_by_criteria(race_dates, status=args.status, month=args.month, limit=args.limit)

# After: Excludes upcoming races by default with safety override
filtered_dates = filter_dates_by_criteria(race_dates, status=args.status, month=args.month, limit=args.limit, allow_upcoming=args.allow_upcoming)
```

### 🧹 Comprehensive Cleanup Tools

#### New Script: `cleanup_july_2025_records.py`
- **Handles all 8 PocketBase collections** including the tricky `race_payout_pools`
- **Special handling for race_payout_pools** which uses `race_id` instead of `race_date`
- **Interactive confirmation** with detailed preview before deletion
- **Verification step** to ensure complete cleanup

#### Collection Coverage
- ✅ race_performance
- ✅ race_performance_analysis  
- ✅ race_horse_performance
- ✅ race_incidents
- ✅ race_incident_analysis
- ✅ race_payouts
- ✅ **race_payout_pools** (special race_id handling)
- ✅ race_payout_analysis

### 🔍 Verification & Monitoring Tools

#### New Script: `check_pocketbase_collections.py`
- **Comprehensive collection checking** across all 8 collections
- **July 2025 record detection** with detailed reporting
- **Multiple date format support** for thorough searching

#### New Script: `check_payout_pools.py`
- **Specialized checker** for race_payout_pools collection
- **race_id pattern matching** (e.g., "2025-07-01_ST_R1")
- **Pool type identification** (獨贏, 位置, 連贏, etc.)

### 🐛 Bug Fixes

#### Issue: Future Date Processing
- **Problem:** Pipeline was creating records for 2025/07/05 (future date) when processing July 2025
- **Root Cause:** No safety filter to prevent upcoming race processing
- **Solution:** Added automatic safety filter that excludes upcoming races by default

#### Issue: Incomplete Cleanup
- **Problem:** `race_payout_pools` collection was missed in cleanup operations
- **Root Cause:** Collection uses `race_id` field instead of `race_date`
- **Solution:** Added special handling for race_id pattern matching

#### Issue: Manual Cleanup Difficulty
- **Problem:** No easy way to clean up incorrect records across all collections
- **Root Cause:** No comprehensive cleanup tool
- **Solution:** Created interactive cleanup script with verification

### 📊 Data Integrity Improvements

#### Record Count Tracking
- **Before cleanup:** 757 July 2025 records across collections
  - 317 records in 7 collections (race_date field)
  - 440 records in race_payout_pools (race_id field)
- **After cleanup:** 0 July 2025 records (verified clean state)

#### Field Format Standardization
| Collection | Field | Format | Example |
|------------|-------|--------|---------|
| Most collections | race_date | YYYY/MM/DD | 2025/07/01 |
| race_payout_pools | race_id | YYYY-MM-DD_VENUE_RN | 2025-07-01_ST_R1 |

### 🔧 Technical Improvements

#### Enhanced Error Handling
- **Better error messages** with emoji indicators
- **Graceful failure handling** for missing collections
- **Detailed logging** of cleanup operations

#### Code Quality
- **Modular design** with reusable functions
- **Consistent error handling** across all scripts
- **Clear documentation** and inline comments

### 📚 Documentation

#### New Documentation Files
- **`PIPELINE_DOCUMENTATION.md`** - Comprehensive pipeline guide
- **`QUICK_REFERENCE.md`** - Common commands and troubleshooting
- **`CHANGELOG.md`** - This changelog

#### Updated Documentation
- **Enhanced README** with safety feature explanations
- **Inline code comments** for better maintainability

### ⚠️ Breaking Changes

#### Command Line Interface
- **New flag:** `--allow-upcoming` required to process future dates
- **Default behavior changed:** Now excludes upcoming races automatically

#### Migration Guide
```bash
# Old way (processed all dates)
python3 batch_extract_races.py --month 2025/07

# New way (safe by default)
python3 batch_extract_races.py --month 2025/07  # Excludes upcoming
python3 batch_extract_races.py --month 2025/07 --allow-upcoming  # Includes upcoming
```

### 🎯 Impact Summary

#### Safety Improvements
- **100% prevention** of accidental future date processing
- **Interactive confirmations** for destructive operations
- **Comprehensive verification** tools

#### Operational Efficiency  
- **One-command cleanup** for all collections
- **Automated verification** of cleanup operations
- **Clear status indicators** throughout process

#### Data Quality
- **Zero tolerance** for future date records
- **Complete collection coverage** in cleanup operations
- **Verified clean state** after operations

---

## [1.0.0] - Previous Version

### Initial Features
- Basic race data extraction from HKJC website
- Upload to PocketBase collections
- Manual pipeline execution
- Basic date filtering

### Known Issues (Fixed in 2.0.0)
- ❌ No protection against future date processing
- ❌ Incomplete cleanup tools
- ❌ Missing race_payout_pools handling
- ❌ Manual verification required

---

**Migration Notes:** 
- All existing functionality preserved
- New safety features active by default
- Use `--allow-upcoming` flag if you need to process future dates
- Run cleanup tools to remove any existing future date records
