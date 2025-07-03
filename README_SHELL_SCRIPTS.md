# HKJC Data Processing - Ubuntu/Linux Shell Scripts

This directory contains Ubuntu/Linux shell scripts (.sh) for automated HKJC race data processing.

## 📋 Available Shell Scripts

### 🚀 **Main Pipeline Scripts**

| **File** | **Purpose** | **Time** | **Description** |
|----------|-------------|----------|-----------------|
| `run_complete_pipeline.sh` | **Complete automation** | 10-30 min | Runs entire pipeline: dates → data → upload |
| `quick_test.sh` | **System validation** | 2-3 min | Tests all components with single race |

### 🔧 **Individual Step Scripts**

| **File** | **Purpose** | **Time** | **Description** |
|----------|-------------|----------|-----------------|
| `1_extract_race_dates.sh` | Extract race dates | 5-10 min | Gets all dates with metadata from HKJC |
| `2_extract_race_data.sh` | Extract race results | 5-60 min | Batch extracts race data with fixes |
| `3_upload_to_pocketbase.sh` | Upload to database | 2-10 min | Uploads to 8 PocketBase collections |

### 🗑️ **Clearing & Reset Scripts**

| **File** | **Purpose** | **Time** | **Description** |
|----------|-------------|----------|-----------------|
| `clear_local_files.sh` | Clear local files | <1 min | Clears race_dates.json and performance_data |
| `clear_pocketbase_collections.sh` | Clear database | 1-5 min | Clears 8 PocketBase collections |
| `complete_reset.sh` | **Complete system reset** | 2-30 min | Full reset + optional fresh extraction |

---

## 🚀 **Quick Start Guide**

### **Option 1: Complete Automation (Recommended)**
```bash
./run_complete_pipeline.sh
```
- Runs entire pipeline automatically
- Choose from preset options (June 2025, latest 10 races, etc.)
- Handles all steps with error checking

### **Option 2: Test First (Recommended for first-time users)**
```bash
./quick_test.sh
```
- Validates system with single race
- Confirms all components working
- Takes only 2-3 minutes

### **Option 3: Step-by-Step Control**
```bash
./1_extract_race_dates.sh
./2_extract_race_data.sh  
./3_upload_to_pocketbase.sh
```
- Run each step individually
- More control over process
- Better for troubleshooting

### **Option 4: Reset & Re-process**
```bash
./complete_reset.sh
```
- Complete system reset (local files + database)
- Optional fresh data extraction
- Clean slate for re-processing

---

## 📊 **Pipeline Options**

### **Complete Pipeline Options:**
1. **June 2025 pipeline** - Current month data (recommended)
2. **Latest 10 race days** - Recent data for analysis
3. **Latest 5 race days** - Quick testing
4. **Custom pipeline** - Specify your own parameters

### **Race Data Extraction Options:**
1. **June 2025 races** - Extract current month
2. **Latest 10 completed race days** - Recent comprehensive data
3. **Latest 5 completed race days** - Quick test extraction
4. **All completed races** - Full historical data (very long!)
5. **Custom extraction** - Specify month, limit, racecourse, etc.

### **Upload Options:**
1. **June 2025 data** - Upload current month
2. **Latest extracted data** - Upload most recent extractions
3. **All performance data** - Upload everything (careful of duplicates!)
4. **Specific date range** - Upload custom date pattern
5. **Test upload** - Single file validation

---

## 🔧 **Prerequisites**

### **Required Software:**
- ✅ **Ubuntu/Linux** (tested on Ubuntu 20.04+)
- ✅ **Python 3.7+** installed
- ✅ **Required Python packages** (requests, beautifulsoup4, etc.)
- ✅ **PocketBase server** running at http://terence.myds.me:8081

### **Installation Commands:**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python3 and pip
sudo apt install python3 python3-pip -y

# Install required Python packages
pip3 install requests beautifulsoup4 python-dotenv

# Make scripts executable (run once)
chmod +x *.sh
```

### **Required Files:**
- ✅ `extract_race_dates_to_json.py`
- ✅ `batch_extract_races.py`
- ✅ `hkjc_race_results_scraper.py`
- ✅ `upload_all_simple.py`
- ✅ `clear_pocketbase_collections.py`
- ✅ `.env` file with PocketBase credentials

### **Network Requirements:**
- ✅ Internet connection for HKJC website access
- ✅ Access to PocketBase server

---

## 📁 **Generated Files**

### **After Step 1:**
- `race_dates.json` - All race dates with metadata

### **After Step 2:**
- `performance_data/performance_YYYY-MM-DD_RC_RX.json` - Individual race files

### **After Step 3:**
- Data uploaded to 8 PocketBase collections

---

## 🎯 **Usage Examples**

### **First Time Setup:**
```bash
# Make scripts executable
chmod +x *.sh

# Test the system first
./quick_test.sh

# If test passes, run full pipeline
./run_complete_pipeline.sh
```

### **Regular Data Updates:**
```bash
# Extract latest race data
./run_complete_pipeline.sh
# Choose option 2: "Latest 10 race days pipeline"
```

### **Specific Month Processing:**
```bash
# Run complete pipeline
./run_complete_pipeline.sh
# Choose option 4: "Custom pipeline"
# Enter: --month 2025/05
```

### **Troubleshooting:**
```bash
# Run steps individually to isolate issues
./1_extract_race_dates.sh
./2_extract_race_data.sh
./3_upload_to_pocketbase.sh
```

### **Data Issues & Re-processing:**
```bash
# Found data inconsistencies - need fresh extraction
./complete_reset.sh
# Choose option 1: "Complete reset (local files + PocketBase)"

# Then run fresh pipeline
./run_complete_pipeline.sh
```

### **Database Schema Changes:**
```bash
# Clear database collections only (keep local files)
./clear_pocketbase_collections.sh
# Choose option 2: "Clear all collections"

# Re-upload existing data
./3_upload_to_pocketbase.sh
```

### **Testing New Extraction Logic:**
```bash
# Clear local files only (keep database)
./clear_local_files.sh
# Choose option 2: "Clear performance_data folder only"

# Test extraction with latest code
./2_extract_race_data.sh
```

---

## ⚠️ **Important Notes**

### **Performance:**
- Race dates extraction: ~5-10 minutes (with metadata verification)
- Race data extraction: Varies by number of races (2-5 seconds per race)
- PocketBase upload: ~1-2 seconds per race

### **Error Handling:**
- All scripts include error checking and helpful messages
- Failed steps won't proceed to next step
- Clear troubleshooting guidance provided

### **Data Safety:**
- Scripts check for existing files before overwriting
- PocketBase uploads handle duplicates appropriately
- Backup recommendations provided in error messages

### **Permissions:**
- Scripts must be executable: `chmod +x *.sh`
- May need sudo for package installation
- Ensure write permissions in working directory

---

## 🗑️ **Clearing & Reset Procedures**

### **When to Clear/Reset:**
- **Data inconsistencies** - When extracted data has errors
- **Schema changes** - When PocketBase collection structure changes  
- **Fresh start** - When you want to re-process all data cleanly
- **Testing** - Before running tests with clean environment
- **Troubleshooting** - When debugging data processing issues

### **Clear Options:**

#### **🗂️ Clear Local Files Only**
```bash
./clear_local_files.sh
```
**Clears:**
- `race_dates.json` (race dates with metadata)
- `performance_data/` folder (all extracted race JSON files)

#### **🗄️ Clear PocketBase Collections Only**
```bash
./clear_pocketbase_collections.sh
```
**Clears 8 collections:**
- `race_performance`, `race_performance_analysis`, `race_horse_preference`
- `race_incident_analysis`, `race_payouts`, `race_payout_analysis`
- `race_safety_assessment`, `race_results`

#### **🔄 Complete System Reset**
```bash
./complete_reset.sh
```
**Clears:**
- All local files + All 8 PocketBase collections
- **Optional:** Fresh data extraction

---

## 🆘 **Troubleshooting**

### **Common Issues:**

**"Python3 is not installed or not in PATH"**
- Install Python3: `sudo apt install python3 python3-pip`
- Verify installation: `python3 --version`

**"Permission denied"**
- Make scripts executable: `chmod +x *.sh`
- Check directory permissions: `ls -la`

**"Required script files are missing"**
- Ensure you're in the correct directory
- Check all Python scripts are present: `ls *.py`

**"PocketBase upload failed"**
- Verify PocketBase server is running
- Check server URL: http://terence.myds.me:8081
- Verify credentials in .env file
- Test network connectivity: `curl http://terence.myds.me:8081`

**"Race dates extraction failed"**
- Check internet connection: `ping racing.hkjc.com`
- HKJC website may be temporarily unavailable
- Try again later

**"Data inconsistencies or duplicates"**
- Run `./complete_reset.sh` for clean re-processing
- Or use `./clear_pocketbase_collections.sh` to clear database only
- Check for schema changes in PocketBase collections

---

## 📞 **Support**

For issues or questions:
1. Check error messages in script output
2. Verify all prerequisites are met
3. Try `./quick_test.sh` to isolate issues
4. Run individual step scripts for detailed debugging
5. Check log files and network connectivity

---

## 🎉 **Benefits of Shell Script System**

✅ **Native Linux support** - Optimized for Ubuntu/Linux environments  
✅ **No additional dependencies** - Uses standard bash features  
✅ **Complete automation** - Handles entire pipeline  
✅ **Error prevention** - Validates prerequisites  
✅ **User guidance** - Clear instructions and next steps  
✅ **Flexible options** - Multiple use cases supported  
✅ **Safety features** - Confirmations for destructive operations  
✅ **Troubleshooting support** - Helpful error messages  

The shell scripts make the HKJC data processing system **fully compatible with Ubuntu/Linux** while maintaining all the powerful automation and data quality features! 🏆
