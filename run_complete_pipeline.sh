#!/bin/bash
# ============================================================================
# HKJC Complete Data Processing Pipeline
# ============================================================================
# This script runs the complete HKJC data extraction and upload pipeline:
# 1. Extract race dates with metadata
# 2. Extract race data with sectional fixes and field analysis  
# 3. Upload to PocketBase (8 collections)
# ============================================================================

echo
echo "============================================================================"
echo "HKJC Complete Data Processing Pipeline"
echo "============================================================================"
echo
echo "This script will run the complete HKJC data processing workflow:"
echo
echo "📅 Step 1: Extract race dates with metadata verification"
echo "🏇 Step 2: Extract race data with automatic fixes"
echo "🗄️  Step 3: Upload to PocketBase collections"
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ ERROR: Python3 is not installed or not in PATH"
    echo "Please install Python3 and try again"
    echo "  sudo apt update && sudo apt install python3 python3-pip"
    read -p "Press Enter to continue..."
    exit 1
fi

# Check if all required scripts exist
missing_files=0

if [ ! -f "extract_race_dates_to_json.py" ]; then
    echo "❌ Missing: extract_race_dates_to_json.py"
    missing_files=1
fi

if [ ! -f "batch_extract_races.py" ]; then
    echo "❌ Missing: batch_extract_races.py"
    missing_files=1
fi

if [ ! -f "hkjc_race_results_scraper.py" ]; then
    echo "❌ Missing: hkjc_race_results_scraper.py"
    missing_files=1
fi

if [ ! -f "upload_all_simple.py" ]; then
    echo "❌ Missing: upload_all_simple.py"
    missing_files=1
fi

if [ $missing_files -eq 1 ]; then
    echo
    echo "❌ ERROR: Required script files are missing"
    echo "Please make sure you're in the correct directory"
    read -p "Press Enter to continue..."
    exit 1
fi

echo "✅ All required scripts found"
echo

# Check if arguments were provided
if [ $# -eq 0 ]; then
    # Interactive mode - show pipeline options
    echo "🚀 Pipeline options:"
    echo
    echo "1. June 2025 pipeline (recommended for current data)"
    echo "2. Latest 10 race days pipeline (quick processing)"
    echo "3. Latest 5 race days pipeline (testing)"
    echo "4. Custom pipeline"
    echo

    read -p "Enter your choice (1-4): " choice

    case $choice in
        1)
            extract_args="--status completed --month 2025/06"
            echo
            echo "📅 Selected: June 2025 pipeline"
            ;;
        2)
            extract_args="--status completed --limit 10"
            echo
            echo "📅 Selected: Latest 10 race days pipeline"
            ;;
        3)
            extract_args="--status completed --limit 5"
            echo
            echo "📅 Selected: Latest 5 race days pipeline"
            ;;
        4)
            echo
            echo "🔧 Custom pipeline configuration:"
            echo
            echo "Extraction arguments (e.g., --month 2025/05 --limit 10):"
            read -p "Enter extraction args: " extract_args
            ;;
        *)
            echo "❌ Invalid choice. Exiting."
            exit 1
            ;;
    esac

    echo
    echo "⏱️  Estimated time: 10-30 minutes depending on data volume"
    echo "🌐 This will make requests to HKJC website and PocketBase"
    echo

    read -p "Proceed with pipeline? (y/N): " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        echo "Pipeline cancelled."
        exit 0
    fi
else
    # Non-interactive mode - use provided arguments
    extract_args="$*"
    echo "🚀 Running pipeline with arguments: $extract_args"
    echo
    echo "⏱️  Estimated time: 10-30 minutes depending on data volume"
    echo "🌐 This will make requests to HKJC website and PocketBase"
    echo
fi

echo
echo "============================================================================"
echo "📅 STEP 1: Extracting race dates with metadata"
echo "============================================================================"
echo

python3 extract_race_dates_to_json.py

if [ $? -ne 0 ]; then
    echo
    echo "❌ ERROR: Step 1 failed - Race dates extraction"
    read -p "Press Enter to continue..."
    exit 1
fi

echo
echo "✅ Step 1 completed successfully!"
echo

echo "============================================================================"
echo "🏇 STEP 2: Extracting race data"
echo "============================================================================"
echo

python3 batch_extract_races.py $extract_args

if [ $? -ne 0 ]; then
    echo
    echo "❌ ERROR: Step 2 failed - Race data extraction"
    read -p "Press Enter to continue..."
    exit 1
fi

echo
echo "✅ Step 2 completed successfully!"
echo

echo "============================================================================"
echo "🗄️  STEP 3: Uploading to PocketBase"
echo "============================================================================"
echo

# Upload only files from the extracted month/period
if [[ "$extract_args" == *"--month"* ]]; then
    # Extract month from args (e.g., "2025/01" from "--month 2025/01")
    month=$(echo "$extract_args" | grep -o '[0-9]\{4\}/[0-9]\{2\}' | head -1)
    if [ -n "$month" ]; then
        # Convert 2025/01 to 2025-01 for file pattern
        file_month=$(echo "$month" | tr '/' '-')
        echo "📅 Uploading files for month: $month (pattern: performance_$file_month-*)"

        # Create temporary directory with only the month's files
        temp_dir="temp_upload_${file_month}"
        mkdir -p "$temp_dir"
        cp performance_data/performance_${file_month}-*.json "$temp_dir/" 2>/dev/null

        if [ $? -eq 0 ] && [ "$(ls -A $temp_dir)" ]; then
            echo "📁 Created temporary directory with $(ls $temp_dir | wc -l) files"
            python3 upload_all_simple.py --directory "$temp_dir"
            upload_result=$?
            rm -rf "$temp_dir"

            if [ $upload_result -ne 0 ]; then
                echo "❌ Upload failed"
                exit 1
            fi
        else
            echo "⚠️  No files found for month $month, skipping PocketBase upload"
            echo "✅ Step 3 skipped (no data to upload)"
        fi
    else
        echo "⚠️  Could not extract month from args, uploading all files"
        python3 upload_all_simple.py --directory performance_data
    fi
else
    # For non-month based extractions, upload all files
    echo "📁 Uploading all performance files"
    python3 upload_all_simple.py --directory performance_data
fi

if [ $? -ne 0 ]; then
    echo
    echo "❌ ERROR: Step 3 failed - PocketBase upload"
    echo
    echo "🔧 The data extraction was successful, but upload failed."
    echo "You can retry the upload later using ./3_upload_to_pocketbase.sh"
    read -p "Press Enter to continue..."
    exit 1
fi

echo
echo "============================================================================"
echo "✅ PIPELINE COMPLETED SUCCESSFULLY!"
echo "============================================================================"
echo
echo "🎉 All steps completed successfully:"
echo "  ✅ Race dates extracted with metadata"
echo "  ✅ Race data extracted with automatic fixes"
echo "  ✅ Data uploaded to PocketBase (8 collections)"
echo
echo "🌐 View your data at: http://terence.myds.me:8081/_/"
echo
echo "📊 Generated files:"
echo "  - race_dates.json (race dates with metadata)"
echo "  - performance_data/*.json (race performance data)"
echo

# Show summary statistics
if [ -d "performance_data" ]; then
    file_count=$(ls performance_data/performance_*.json 2>/dev/null | wc -l)
    echo "📁 Performance files generated: $file_count"
fi

echo
echo "Press Enter to exit..."
read
