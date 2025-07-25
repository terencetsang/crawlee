# HKJC Win Odds Trends Extraction & Upload Guide

## Overview
This guide covers the complete process for extracting **獨贏賠率走勢 (Win Odds Trends)** data from HKJC website and uploading to PocketBase database.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Configuration](#configuration)
3. [Data Structure](#data-structure)
4. [Extraction Process](#extraction-process)
5. [Upload Process](#upload-process)
6. [Verification](#verification)
7. [File Organization](#file-organization)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software
- Python 3.8+
- Playwright browser automation
- PocketBase database server

### Required Python Packages
```bash
pip install playwright beautifulsoup4 requests python-dotenv pocketbase
playwright install chromium
```

### Environment Setup
Create `.env` file with:

**⚠️ SECURITY NOTE**: Never commit the `.env` file to version control. Add `.env` to your `.gitignore` file to prevent accidental exposure of credentials.
```env
# PocketBase Configuration
POCKETBASE_URL=your_pocketbase_server_url
POCKETBASE_EMAIL=your_pocketbase_email
POCKETBASE_PASSWORD=your_pocketbase_password

# Output Directory for JSON backups
OUTPUT_DIR=win_odds_data

# Race Information (for manual extraction)
RACE_DATE=2025/07/01
RACECOURSE=ST
TOTAL_RACES=12
```

## Configuration

### PocketBase Collection Schema
Collection name: `race_odds`

#### Current Schema (extract_latest_odds.py)
Required fields:
- `race_date` (text) - Format: YYYY/MM/DD
- `racecourse` (text) - ST (Sha Tin) or HV (Happy Valley)
- `race_number` (number) - Race number (1-12)
- `race_id` (text) - Format: YYYY-MM-DD_VENUE_RX
- `horse_data` (json) - Array of horse odds data
- `extracted_at` (text) - ISO timestamp
- `source_url` (text) - HKJC source URL

#### Legacy Schema (historical scripts)
- `race_date` (text) - Format: YYYY-MM-DD
- `venue` (text) - ST (Sha Tin) or HV (Happy Valley)
- `race_number` (number) - Race number (1-12)
- `data_type` (text) - Always "win_odds_trends"
- `complete_data` (json) - Full odds data structure
- `scraped_at` (text) - ISO timestamp
- `source_url` (text) - HKJC source URL
- `extraction_status` (text) - "success" or "partial"

### Date Reference Files
- `odds_dates.json` - Contains dates with available odds data
- `race_dates.json` - Contains all race dates (for race entries)

## Data Structure

### Win Odds Trends JSON Format

#### Current Format (extract_latest_odds.py)
```json
{
  "race_info": {
    "race_date": "2025-07-09",
    "venue": "HV",
    "race_number": 1,
    "source_url": "https://bet.hkjc.com/ch/racing/pwin/2025-07-09/HV/1",
    "scraped_at": "2025-07-07T21:25:35.827048"
  },
  "horses_data": [
    {
      "horse_number": 1,
      "horse_name": "Horse 1",
      "win_odds": "3.0",
      "extracted_at": "2025-07-07T21:25:35.827095"
    },
    {
      "horse_number": 2,
      "horse_name": "Horse 2",
      "win_odds": "3.5",
      "extracted_at": "2025-07-07T21:25:35.827106"
    }
  ]
}
```

#### Legacy Format (historical scripts)
```json
{
  "race_info": {
    "race_date": "2025-07-01",
    "venue": "ST",
    "race_number": 1,
    "source_url": "https://bet.hkjc.com/ch/racing/pwin/2025-07-01/ST/1",
    "scraped_at": "2025-07-03T13:44:14.123456"
  },
  "horses_data": [
    {
      "horse_number": "1",
      "horse_name": "馬名",
      "gate": "1",
      "weight": "133",
      "jockey": "騎師名",
      "trainer": "練馬師名",
      "win_odds_trend": [
        {"time": "07:30", "odds": "3.2"},
        {"time": "15:59", "odds": "3.5"},
        {"time": "16:02", "odds": "3.8"}
      ],
      "place_odds": "1.4"
    }
  ],
  "extraction_summary": {
    "total_horses": 14,
    "data_extraction_successful": true,
    "timestamps": ["07:30", "15:59", "16:02"]
  }
}
```

## Extraction Process

### 1. Latest Race Odds Extraction (Recommended)
```bash
# Extract latest/current race odds automatically
python extract_latest_odds.py
```
**Features:**
- ✅ Automatically detects latest available race date
- ✅ Uses base URL strategy for current race data
- ✅ Extracts all races for the detected date
- ✅ Saves to both local files and PocketBase
- ✅ No manual date configuration required

### 2. Historical Odds Extraction
```bash
# Extract all available historical odds data
python extract_all_odds_data.py
```

### 3. Manual Single Race Extraction
```bash
# Extract specific race (legacy method)
python hkjc_win_odds_trends.py
```

### 4. Extract Missing Races
```bash
# Check for missing races first
python cross_check_race_counts.py

# Extract specific missing races
python extract_missing_2_races.py
```

### Extraction Scripts Overview

#### `extract_latest_odds.py` ⭐ **RECOMMENDED**
- **Purpose**: Extract latest/current race odds automatically
- **Strategy**: Uses base URL to detect current race date and venue
- **Input**: No configuration required (auto-detects)
- **Output**: JSON files with `_latest` suffix + PocketBase upload
- **Features**:
  - Auto-detection of current race
  - Complete race day extraction
  - Real-time odds data
  - Automatic PocketBase upload
- **Use Case**: Daily odds monitoring, current race analysis

#### `extract_all_odds_data.py`
- **Purpose**: Extract all available historical odds data
- **Input**: Uses `odds_dates.json` for date list
- **Output**: JSON files in `win_odds_data/` + PocketBase upload
- **Features**: Retry logic, error handling, progress tracking
- **Use Case**: Historical data collection, bulk extraction

#### `hkjc_win_odds_trends.py`
- **Purpose**: Extract single race odds data (legacy)
- **Input**: Manual race date/venue/number configuration
- **Output**: Single JSON file + PocketBase upload
- **Features**: Detailed extraction logging
- **Use Case**: Specific race extraction, debugging

#### `extract_missing_2_races.py`
- **Purpose**: Extract specific missing races
- **Input**: Hardcoded race list in script
- **Output**: JSON files + PocketBase upload
- **Features**: Targeted extraction with retry
- **Use Case**: Gap filling, specific race recovery

## Latest Odds Extraction Workflow

### Quick Start (Recommended)
```bash
# Extract latest race odds (one command)
python extract_latest_odds.py
```

### What It Does
1. **🔍 Auto-Detection**: Automatically detects current race date and venue
2. **🏇 Complete Extraction**: Extracts all races for the detected race day
3. **💾 Dual Storage**: Saves to both local JSON files and PocketBase
4. **📊 Real-Time Data**: Gets current live odds for upcoming races

### Output Files
- **Local Files**: `win_odds_data/win_odds_trends_YYYY_MM_DD_VENUE_RX_latest.json`
- **PocketBase**: Records in `race_odds` collection
- **Console**: Progress tracking and summary statistics

### Example Output
```
🏇 HKJC Latest Race Odds Extractor
============================================================
✅ Latest race: 2025-07-09 HV (Happy Valley)
📊 Processing 12 races
✅ Total races extracted: 12/12
💾 Total saved to PocketBase: 12
📁 Backup files saved to: win_odds_data/
```

## Upload Process

### Automatic Upload
All extraction scripts automatically upload to PocketBase after successful extraction.

### Manual Upload/Verification
```bash
# Verify all data is uploaded correctly
python verify_pocketbase_data.py

# Upload missing files manually
python upload_missing_to_pocketbase.py
```

### Upload Data Flow
1. **Extract** odds data from HKJC website
2. **Process** raw HTML into structured JSON
3. **Save** backup JSON file to `win_odds_data/`
4. **Upload** to PocketBase `race_odds` collection
5. **Verify** upload success

## Verification

### Database Verification
```bash
# Complete verification of database vs local files
python verify_pocketbase_data.py
```

### Cross-Check Race Counts
```bash
# Verify race counts against reference data
python cross_check_race_counts.py
```

### Cleanup Invalid Data
```bash
# Remove duplicate records
python check_and_cleanup_duplicates.py

# Remove invalid venue assignments
python cleanup_invalid_venues.py

# Remove invalid dates (e.g., July 2nd)
python cleanup_july_2_records.py
```

## File Organization

### Directory Structure
```
project/
├── win_odds_data/                    # Win odds trends JSON files
│   ├── README.md                     # Documentation
│   ├── win_odds_trends_2025_06_26_ST_R1.json
│   ├── win_odds_trends_2025_06_26_ST_R2.json
│   └── ...
├── race_data/                        # Race entries data
├── odds_dates.json                   # Odds data dates reference
├── race_dates.json                   # All race dates reference
└── extraction_scripts/
    ├── extract_all_odds_data.py
    ├── hkjc_win_odds_trends.py
    └── verify_pocketbase_data.py
```

### File Naming Convention

#### Current Format (extract_latest_odds.py)
Format: `win_odds_trends_YYYY_MM_DD_VENUE_RX_latest.json`
- `YYYY_MM_DD`: Race date (underscores)
- `VENUE`: ST (Sha Tin) or HV (Happy Valley)
- `RX`: Race number (R1, R2, etc.)
- `_latest`: Suffix indicating current/live odds data

**Examples:**
- `win_odds_trends_2025_07_09_HV_R1_latest.json`
- `win_odds_trends_2025_07_09_HV_R12_latest.json`

#### Legacy Format (historical scripts)
Format: `win_odds_trends_YYYY_MM_DD_VENUE_RX.json`
- `YYYY_MM_DD`: Race date (underscores)
- `VENUE`: ST (Sha Tin) or HV (Happy Valley)
- `RX`: Race number (R1, R2, etc.)

**Examples:**
- `win_odds_trends_2025_07_05_ST_R1.json`
- `win_odds_trends_2025_07_05_ST_R11.json`

## Troubleshooting

### Common Issues

#### 1. No Odds Data Available
**Symptom**: Script reports "No odds data found"
**Cause**: HKJC removes old odds data after ~1-2 months
**Solution**: Check if date is too old, use available dates from `odds_dates.json`

#### 2. PocketBase Upload Fails
**Symptom**: "PocketBase error" messages
**Cause**: Authentication or network issues
**Solution**: 
- Verify PocketBase URL and credentials in `.env`
- Check PocketBase server is running
- Verify collection permissions

#### 3. Duplicate Records
**Symptom**: Multiple records for same race
**Cause**: Re-running extraction scripts
**Solution**: Run `python check_and_cleanup_duplicates.py`

#### 4. Invalid Venue Assignments
**Symptom**: Both ST and HV for same date
**Cause**: Incorrect venue detection
**Solution**: Run `python cleanup_invalid_venues.py`

#### 5. Browser Automation Fails
**Symptom**: Playwright timeout errors
**Cause**: HKJC website changes or network issues
**Solution**:
- Update Playwright: `playwright install chromium`
- Check internet connection
- Try with `headless=False` for debugging

### Debug Mode
Enable debug mode by setting `headless=False` in extraction scripts:
```python
browser = await p.chromium.launch(headless=False)  # Shows browser
```

### Log Analysis
Check extraction logs for:
- HTTP response codes
- Page content validation
- Data parsing errors
- Upload confirmation

## Best Practices

### Current Approach (extract_latest_odds.py)
1. **Daily Extraction**: Run `python extract_latest_odds.py` daily for current odds
2. **Automatic Detection**: No manual date configuration required
3. **Real-Time Data**: Gets live odds for upcoming races
4. **Consistent Format**: Standardized JSON structure and naming
5. **Dual Storage**: Local backup + PocketBase upload

### Legacy Approach (historical scripts)
1. **Regular Extraction**: Run extraction weekly to capture data before removal
2. **Backup Strategy**: Keep JSON files as backup before PocketBase upload
3. **Verification**: Always run verification after bulk operations
4. **Monitoring**: Check `odds_dates.json` for available date ranges
5. **Cleanup**: Regularly remove invalid/duplicate records

### Migration Strategy
- **New Projects**: Use `extract_latest_odds.py` for current odds
- **Historical Data**: Use legacy scripts for past data collection
- **Monitoring**: Combine both approaches for comprehensive coverage

## Data Retention

- **HKJC Website**: ~1-2 months for odds data
- **Local JSON Files**: Permanent backup in `win_odds_data/`
- **PocketBase**: Permanent storage with full history

## Contact & Support

For issues with:
- **Extraction Scripts**: Check script logs and error messages
- **PocketBase**: Verify server status and credentials
- **Data Quality**: Run verification and cleanup scripts
