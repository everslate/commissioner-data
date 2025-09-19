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
    
    # Hardcoded API key
    api_key = "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"
    
    # Initialize converter and convert single file
    converter = CommissionerConverter(api_key)
    success = converter.convert_single_file(filename)
    
    if success:
        print(f"✅ Successfully converted {filename}")
    else:
        print(f"❌ Failed to convert {filename}")

if __name__ == "__main__":
    main()
