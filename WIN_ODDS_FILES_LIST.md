# HKJC Win Odds Trends - File List for Git

## 📋 Files for Win Odds Extraction & Upload Process

### 🔧 **Core Extraction Scripts**
```
✅ extract_all_odds_data.py                    # Main automated extraction script
✅ hkjc_win_odds_trends.py                     # Single race extraction script  
✅ extract_missing_2_races.py                  # Targeted missing race extraction
✅ extract_odds_to_pocketbase.py               # Direct extraction to PocketBase
```

### 🗄️ **Database & Verification Scripts**
```
✅ verify_pocketbase_data.py                   # Complete database verification
✅ check_and_cleanup_duplicates.py             # Remove duplicate records
✅ cleanup_invalid_venues.py                   # Fix venue assignments
✅ cleanup_july_2_records.py                   # Remove invalid dates
✅ cross_check_race_counts.py                  # Cross-check race counts
```

### 📅 **Date Management Scripts**
```
✅ create_odds_dates_json.py                   # Create odds-specific dates
✅ create_race_dates_from_actual_data.py       # Generate dates from actual data
✅ create_race_dates_from_hkjc.py              # Generate dates from HKJC website
✅ update_race_dates_json.py                   # Update race dates reference
```

### 🧹 **Organization & Maintenance Scripts**
```
✅ organize_win_odds_files.py                  # Organize files into win_odds_data/
✅ check_june_july_odds.py                     # Check June/July availability
✅ check_may_odds.py                           # Check May availability
✅ debug_pocketbase_record.py                  # Debug PocketBase records
```

### 📚 **Documentation Files**
```
✅ WIN_ODDS_EXTRACTION_GUIDE.md                # Complete technical guide
✅ WIN_ODDS_QUICK_REFERENCE.md                 # Quick reference commands
✅ WIN_ODDS_PROCESS_FLOW.md                    # Process flow diagrams
✅ WIN_ODDS_FILES_LIST.md                      # This file list (current)
```

### 📁 **Data Directories**
```
✅ win_odds_data/                              # Win odds trends JSON files (167 files)
   ├── README.md                               # Folder documentation
   ├── win_odds_trends_2025_06_26_ST_R1.json  # Individual race files
   ├── win_odds_trends_2025_06_26_ST_R2.json
   └── ... (165 more files) - ALL INCLUDED IN GIT
```

### 📊 **Reference & Configuration Files**
```
✅ odds_dates.json                             # Available odds dates (6 dates)
✅ odds_dates_summary.json                     # Odds dates summary
✅ dates_comparison.json                       # Comparison between date files
✅ pocketbase_verification_report.json         # Latest verification report
✅ .env                                        # Environment configuration
```

### 🔄 **Backup Files (Optional)**
```
⚠️ extract_all_odds_data.py.backup_*          # Script backups (auto-generated)
⚠️ extract_missing_2_races.py.backup_*        # Script backups (auto-generated)
⚠️ extract_odds_to_pocketbase.py.backup_*     # Script backups (auto-generated)
⚠️ hkjc_win_odds_trends.py.backup_*           # Script backups (auto-generated)
⚠️ .env.backup_*                              # Environment backups (auto-generated)
```

## 🎯 **Recommended Files for Git**

### **Essential Files (Must Include)**
```bash
# Core extraction scripts
extract_all_odds_data.py
hkjc_win_odds_trends.py
extract_missing_2_races.py
extract_odds_to_pocketbase.py

# Verification & maintenance
verify_pocketbase_data.py
check_and_cleanup_duplicates.py
cleanup_invalid_venues.py
cross_check_race_counts.py

# Date management
create_odds_dates_json.py
update_race_dates_json.py

# Organization
organize_win_odds_files.py

# Documentation
WIN_ODDS_EXTRACTION_GUIDE.md
WIN_ODDS_QUICK_REFERENCE.md
WIN_ODDS_PROCESS_FLOW.md
WIN_ODDS_FILES_LIST.md

# Reference files
odds_dates.json
win_odds_data/  # ENTIRE FOLDER INCLUDING ALL JSON FILES

# Configuration template
.env.template  # (Create from .env with placeholder values)
```

### **Optional Files (Consider Including)**
```bash
# Additional verification scripts
cleanup_july_2_records.py
check_june_july_odds.py
debug_pocketbase_record.py

# Date generation utilities
create_race_dates_from_actual_data.py
create_race_dates_from_hkjc.py

# Summary files
odds_dates_summary.json
dates_comparison.json
```

### **Files to Exclude from Git**
```bash
# Sensitive data
.env                                    # Contains credentials
*.backup_*                              # Auto-generated backups

# Large data directories
race_data/                              # Race entries data
prompt_text_files/                      # Prompt files

# Generated reports
pocketbase_verification_report.json     # Auto-generated
race_sessions_summary.json              # Auto-generated

# System files
__pycache__/                            # Python cache
nohup.out                               # Process logs
```

## 📝 **Git Setup Recommendations**

### **Create .gitignore**
```gitignore
# Environment and credentials
.env
*.backup_*

# Data directories
race_data/
prompt_text_files/

# Generated reports
*_summary.json
*_report.json
*_comparison.json

# System files
__pycache__/
*.pyc
nohup.out
storage/

# IDE files
.vscode/
.idea/
```

### **Create .env.template**
```env
# PocketBase Configuration
POCKETBASE_URL=http://your-pocketbase-url:8081
POCKETBASE_EMAIL=your-email@example.com
POCKETBASE_PASSWORD=your-password

# Output Directory for JSON backups
OUTPUT_DIR=win_odds_data

# Race Information (for manual extraction)
RACE_DATE=2025/07/01
RACECOURSE=ST
TOTAL_RACES=12
```

### **Create requirements.txt**
```txt
playwright>=1.40.0
beautifulsoup4>=4.12.0
requests>=2.31.0
python-dotenv>=1.0.0
pocketbase>=0.8.0
```

## 🚀 **Git Commands for Setup**

### **Initial Setup**
```bash
# Initialize git repository
git init

# Add essential files
git add extract_all_odds_data.py
git add hkjc_win_odds_trends.py
git add verify_pocketbase_data.py
git add organize_win_odds_files.py
git add WIN_ODDS_*.md
git add odds_dates.json
git add win_odds_data/  # Entire folder with all 167 JSON files
git add .env.template
git add requirements.txt
git add .gitignore

# Initial commit
git commit -m "Initial commit: HKJC Win Odds Trends extraction system with complete data"
```

### **Add Remote Repository**
```bash
# Add remote origin
git remote add origin https://github.com/username/hkjc-win-odds.git

# Push to remote
git push -u origin main
```

## 📊 **File Statistics**

| Category | Count | Size | Include in Git |
|----------|-------|------|----------------|
| **Core Scripts** | 4 | ~50KB | ✅ Yes |
| **Verification Scripts** | 4 | ~40KB | ✅ Yes |
| **Utility Scripts** | 6 | ~60KB | ⚠️ Optional |
| **Documentation** | 4 | ~30KB | ✅ Yes |
| **Win Odds Data** | 167 | 1.4MB | ✅ Yes |
| **Reference Files** | 3 | ~5KB | ✅ Yes |
| **Backup Files** | 5+ | ~50KB | ❌ No |

**Total for Git**: ~1.6MB (including all data files)

## ✅ **Verification Checklist**

Before adding to git, verify:

- [ ] All scripts run without errors
- [ ] .env file excluded (use .env.template)
- [ ] Documentation is up-to-date
- [ ] No sensitive data in tracked files
- [ ] win_odds_data/ folder structure documented
- [ ] requirements.txt includes all dependencies
- [ ] .gitignore covers all sensitive/large files

This file list ensures a clean, professional git repository with all essential win odds extraction and upload functionality while excluding sensitive data and large files.
