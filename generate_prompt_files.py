#!/usr/bin/env python3
import os
import json
import glob
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the prompt input from environment variables
PROMPT_INPUT = os.getenv("PROMPT_INPUT", "作為資深評馬人，根據香港賽馬, 附上以下json資料,那些馬匹可能勝出入三甲及那些馬匹不可能勝出. 6次近績,由左至右排列，左邊是最近.")

# Input and output directories
INPUT_DIR = "race_data"
OUTPUT_DIR = "prompt_text_files"

def main():
    # Ensure the output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Get all JSON files in the input directory
    json_files = glob.glob(f"{INPUT_DIR}/*.json")
    
    # Process each JSON file
    for json_file in json_files:
        # Get the base filename without extension
        base_name = os.path.basename(json_file).split('.')[0]
        
        # Create the output filename
        output_file = f"{OUTPUT_DIR}/{base_name}_with_prompt.txt"
        
        # Check if the output file already exists
        if os.path.exists(output_file):
            print(f"File {output_file} already exists. Skipping.")
            continue
        
        try:
            # Read the JSON file
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Create the prompt file with the prompt input and JSON data
            with open(output_file, 'w', encoding='utf-8') as f:
                # Write the prompt input
                f.write(f"{PROMPT_INPUT}\n\n")
                
                # Write the JSON data
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"Created {output_file}")
        
        except Exception as e:
            print(f"Error processing {json_file}: {str(e)}")

if __name__ == "__main__":
    main()
