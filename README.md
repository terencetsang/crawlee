# HKJC Horse Race Entries Crawler

This script crawls the Hong Kong Jockey Club website to extract horse race entry information and saves it to both a PocketBase database and local JSON files.

## Features

- Extracts detailed race information (name, date, venue, track type, etc.)
- Extracts horse entries (name, jockey, trainer, weight, draw, etc.)
- Extracts reserve horses
- Processes races sequentially
- Saves data to both PocketBase and local JSON files
- Provides fallback mechanisms if PocketBase is unavailable

## Configuration

The script uses a `.env` file to store configuration variables. Create a `.env` file in the same directory as the script with the following variables:

```
# PocketBase Configuration
POCKETBASE_URL=http://your-pocketbase-url.com
POCKETBASE_EMAIL=your-email@example.com
POCKETBASE_PASSWORD=your-password
POCKETBASE_COLLECTION=race_entries

# Race Configuration
RACE_DATE=YYYY/MM/DD
RACECOURSE=ST
TOTAL_RACES=10

# Output Directory (for JSON files)
OUTPUT_DIR=race_data
```

### Configuration Variables

- `POCKETBASE_URL`: The URL of your PocketBase instance
- `POCKETBASE_EMAIL`: The email address for your PocketBase account
- `POCKETBASE_PASSWORD`: The password for your PocketBase account
- `POCKETBASE_COLLECTION`: The name of the collection to save the data to
- `RACE_DATE`: The date of the races in YYYY/MM/DD format
- `RACECOURSE`: The racecourse code (ST for Sha Tin, HV for Happy Valley)
- `TOTAL_RACES`: The total number of races to process
- `OUTPUT_DIR`: The directory to save JSON files to

## Installation

1. Clone the repository
2. Install the required packages:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your configuration
4. Run the script:

```bash
python hkjc_horse_entries_pocketbase.py
```

## Requirements

- Python 3.6+
- crawlee
- pocketbase
- python-dotenv
- requests

## Output

The script will save the data to both:

1. **Local JSON files** in the specified output directory
   - Each race will be saved as a separate JSON file with the format `race_YYYY_MM_DD_RACECOURSE_R{race_number}.json`
   - The JSON files contain the complete race data including race information, horse entries, reserve horses, and equipment legend

2. **PocketBase collection** specified in the configuration
   - Each race will be saved as a separate record with the following fields:
     - `race_number`: The race number
     - `race_date`: The race date
     - `race_name`: The race name
     - `venue`: The venue (Sha Tin or Happy Valley)
     - `race_time`: The race time
     - `track_type`: The track type (turf or all-weather)
     - `course`: The course
     - `distance`: The distance in meters
     - `prize_money`: The prize money
     - `rating`: The rating
     - `race_class`: The race class
     - `entries`: The horse entries (JSON)
     - `reserve_horses`: The reserve horses (JSON)
     - `equipment_legend`: The equipment legend (JSON)
     - `created_at`: The timestamp when the record was created

## License

This project is licensed under the MIT License - see the LICENSE file for details.
