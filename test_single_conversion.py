#!/usr/bin/env python3
"""
Test script to convert a single commissioner file for testing purposes.
Usage: python test_single_conversion.py <filename>
"""

import sys
import os
from convert_to_schema import CommissionerConverter

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_single_conversion.py <filename>")
        print("Example: python test_single_conversion.py Abdullah_Al_Arif_UAE.json")
        return
    
    filename = sys.argv[1]
    
    # Load API key
    try:
        with open("main.py", "r") as f:
            content = f.read()
            import re
            match = re.search(r'api_key="([^"]+)"', content)
            if match:
                api_key = match.group(1)
            else:
                raise ValueError("API key not found in main.py")
    except Exception as e:
        print(f"Could not load API key from main.py: {e}")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("No API key found. Please set OPENAI_API_KEY environment variable or update main.py")
            return
    
    # Initialize converter and convert single file
    converter = CommissionerConverter(api_key)
    success = converter.convert_single_file(filename)
    
    if success:
        print(f"✅ Successfully converted {filename}")
    else:
        print(f"❌ Failed to convert {filename}")

if __name__ == "__main__":
    main()
