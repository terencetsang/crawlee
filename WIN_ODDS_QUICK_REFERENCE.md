# HKJC Win Odds Trends - Quick Reference

## 🚀 Quick Start Commands

### Extract All Available Odds Data
```bash
python extract_all_odds_data.py
```

### Verify Database Integrity
```bash
python verify_pocketbase_data.py
```

### Check for Missing Races
```bash
python cross_check_race_counts.py
```

## 📁 Key Files & Directories

| File/Directory | Purpose |
|----------------|---------|
| `win_odds_data/` | 📊 Win odds trends JSON files |
| `odds_dates.json` | 📅 Available odds dates |
| `race_dates.json` | 📋 All race dates (entries) |
| `.env` | ⚙️ Configuration file |

## 🗄️ PocketBase Collection

**Collection**: `race_odds`
**Purpose**: Store 獨贏賠率走勢 (Win Odds Trends) data

### Key Fields
- `race_date` - YYYY-MM-DD format
- `venue` - ST (Sha Tin) or HV (Happy Valley)  
- `race_number` - 1-12
- `complete_data` - Full JSON odds data

## 🔧 Common Operations

### 1. Extract New Odds Data
```bash
# Check available dates first
cat odds_dates.json

# Extract all available
python extract_all_odds_data.py
```

### 2. Fix Data Issues
```bash
# Remove duplicates
python check_and_cleanup_duplicates.py

# Fix venue assignments
python cleanup_invalid_venues.py

# Remove invalid dates
python cleanup_july_2_records.py
```

### 3. Verify Data Quality
```bash
# Complete verification
python verify_pocketbase_data.py

# Cross-check counts
python cross_check_race_counts.py
```

## 📊 Current Data Status

### Available Odds Data (as of July 2025)
- **Dates**: 2025-06-26 to 2025-07-01 (6 dates)
- **Total Races**: 72 races
- **Venues**: ST (Sha Tin), HV (Happy Valley)
- **Format**: 獨贏賠率走勢 with merged timestamps

### Data Coverage
```
✅ 2025-06-26: ST (12 races)
✅ 2025-06-27: HV (12 races)  
✅ 2025-06-28: ST (12 races)
✅ 2025-06-29: HV (12 races)
✅ 2025-06-30: ST (12 races)
✅ 2025-07-01: ST (12 races)
```

## ⚠️ Important Notes

### HKJC Data Retention
- **Odds data**: Available for ~1-2 months only
- **Older data**: No longer accessible on HKJC website
- **Our database**: Contains complete historical record

### Venue Rules
- **One venue per date**: Never both ST and HV on same date
- **ST**: Sha Tin (typically Sundays)
- **HV**: Happy Valley (typically Wednesdays)

### File Organization
- **win_odds_data/**: Win odds trends only
- **race_data/**: Race entries data only
- **Automatic backup**: JSON files saved before PocketBase upload

## 🚨 Emergency Commands

### If Database is Corrupted
```bash
# 1. Backup current database
python backup_pocketbase_data.py

# 2. Clean duplicates
python check_and_cleanup_duplicates.py

# 3. Re-upload from JSON files
python upload_all_json_to_pocketbase.py

# 4. Verify integrity
python verify_pocketbase_data.py
```

### If Extraction Fails
```bash
# 1. Check available dates
python check_june_july_odds.py

# 2. Try manual extraction
python hkjc_win_odds_trends.py

# 3. Check browser automation
# Set headless=False in script for debugging
```

## 📈 Success Metrics

### Complete Extraction
- ✅ 72/72 races extracted
- ✅ 0 duplicates
- ✅ 0 invalid venues
- ✅ 100% upload success

### Data Quality
- ✅ All races have R1-R12 sequence
- ✅ Single venue per date
- ✅ Valid timestamps in odds trends
- ✅ Complete horse data (name, jockey, trainer)

## 🔗 Related Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `extract_all_odds_data.py` | Extract all odds | Weekly/monthly |
| `verify_pocketbase_data.py` | Verify database | After extractions |
| `organize_win_odds_files.py` | Organize files | Setup/maintenance |
| `create_odds_dates_json.py` | Update date refs | When data changes |

## 📞 Quick Help

### Check Current Status
```bash
# Database record count
python -c "from pocketbase import PocketBase; pb=PocketBase('http://terence.myds.me:8081'); pb.collection('users').auth_with_password('terencetsang@hotmail.com','Qwertyu12345'); print(f'Records: {len(pb.collection(\"race_odds\").get_full_list())}')"

# Local file count  
ls win_odds_data/*.json | wc -l

# Available dates
cat odds_dates.json
```

### Environment Check
```bash
# Check .env configuration
grep -E "(POCKETBASE|OUTPUT)" .env

# Test PocketBase connection
python -c "from pocketbase import PocketBase; pb=PocketBase('http://terence.myds.me:8081'); pb.collection('users').auth_with_password('terencetsang@hotmail.com','Qwertyu12345'); print('✅ Connected')"
```
