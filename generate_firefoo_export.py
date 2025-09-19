#!/usr/bin/env python3
"""
Generate Firefoo-compatible export file from commissioner profiles.

This script converts all JSON profiles in the profiles/ directory into a single
Firefoo-compatible JSON file that can be imported into Firestore via Firefoo.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List
import uuid
import hashlib

def generate_document_id(profile_data: Dict[str, Any]) -> str:
    """Generate a consistent document ID based on profile data."""
    # Use the existing ID if available, otherwise generate from name + organization
    if 'id' in profile_data and profile_data['id']:
        base_string = profile_data['id']
    else:
        name = profile_data.get('name', 'unknown')
        org = profile_data.get('organization', 'unknown')
        base_string = f"{name}_{org}"
    
    # Create a hash to ensure consistent, valid Firestore document IDs
    hash_object = hashlib.md5(base_string.encode())
    doc_id = hash_object.hexdigest()[:20]  # Use first 20 chars for readability
    return doc_id

def convert_timestamp_to_firefoo_format(timestamp_str: str) -> Dict[str, str]:
    """Convert ISO timestamp to Firefoo timestamp format."""
    try:
        # Parse the timestamp and convert to Firefoo format
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return {"__time__": dt.isoformat().replace('+00:00', 'Z')}
    except Exception as e:
        # Fallback to current time if parsing fails
        current_time = datetime.now(timezone.utc)
        return {"__time__": current_time.isoformat().replace('+00:00', 'Z')}

def is_invalid_data(value: Any, field_name: str = "") -> bool:
    """Check if a value represents missing or invalid data."""
    if value is None:
        return True
    
    if isinstance(value, str):
        # Check for various patterns of missing/invalid data
        invalid_patterns = [
            "/not_provided/",
            "not_provided",
            "undefined",
            "@mail.com",
            "@example.com",
            "@notprovideddomain.com",
            "unknown@",
            "anonymous_email@",
            "/0@",
            "/@"
        ]
        
        value_lower = value.lower().strip()
        
        # Empty string
        if not value_lower:
            return True
            
        # Check for invalid patterns
        for pattern in invalid_patterns:
            if pattern in value_lower:
                return True
                
        # For email fields, additional validation
        if field_name == "email":
            # Very basic email validation - must have @ and domain
            if "@" not in value or value.count("@") != 1:
                return True
            parts = value.split("@")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                return True
            # Check for placeholder domains
            domain = parts[1].lower()
            if domain in ["example.com", "mail.com", "notprovideddomain.com"]:
                return True
    
    return False

def clean_data_value(value: Any, field_name: str = "") -> Any:
    """Clean and validate data values, returning appropriate defaults for invalid data."""
    if is_invalid_data(value, field_name):
        # Return appropriate default based on field type and name
        if field_name == "email":
            return None  # Email should be null if not provided
        elif field_name in ["additional_info", "background", "budget_parameters"]:
            return ""  # Text fields can be empty string
        elif field_name in ["thematic_priorities", "themes", "content_not_wanted", 
                           "target_audience", "audience_segments", "format_specifications", 
                           "formats", "duration_categories", "content_lengths", "languages",
                           "technical_requirements", "delivery_requirements", "current_calls", 
                           "submission_process"]:
            return []  # Array fields should be empty arrays
        elif isinstance(value, str):
            return ""  # Other string fields default to empty string
        else:
            return None  # Everything else defaults to null
    
    # Clean string values
    if isinstance(value, str):
        cleaned = value.strip()
        # Remove leading/trailing slashes that might be artifacts
        if cleaned.startswith("/") and cleaned.endswith("/"):
            cleaned = cleaned[1:-1].strip()
        return cleaned if cleaned else ""
    
    return value

def convert_profile_to_firefoo_format(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a profile to Firefoo document format with data cleaning."""
    converted = {}
    
    for key, value in profile_data.items():
        if key in ['created_at', 'updated_at']:
            # Convert timestamps to Firefoo format
            converted[key] = convert_timestamp_to_firefoo_format(value)
        elif key == 'id':
            # Skip the original ID as it becomes the document key
            continue
        else:
            # Clean the data value
            cleaned_value = clean_data_value(value, key)
            
            if cleaned_value is None:
                # Only include non-null values in Firestore
                continue
            elif isinstance(cleaned_value, bool):
                # Boolean values stay as is
                converted[key] = cleaned_value
            elif isinstance(cleaned_value, (int, float)):
                # Numeric values stay as is
                converted[key] = cleaned_value
            elif isinstance(cleaned_value, str):
                # Only include non-empty strings
                if cleaned_value:
                    converted[key] = cleaned_value
            elif isinstance(cleaned_value, list):
                # Only include non-empty arrays
                if cleaned_value:
                    converted[key] = cleaned_value
            elif isinstance(cleaned_value, dict):
                # Object values - recursively convert any nested timestamps
                converted_obj = convert_nested_object(cleaned_value)
                if converted_obj:  # Only include non-empty objects
                    converted[key] = converted_obj
            else:
                # Fallback - convert to string if not empty
                str_value = str(cleaned_value).strip()
                if str_value:
                    converted[key] = str_value
    
    # Add empty __collections__ as per Firefoo format
    converted["__collections__"] = {}
    
    return converted

def convert_nested_object(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively convert nested objects, handling timestamps."""
    converted = {}
    for key, value in obj.items():
        if isinstance(value, str) and ('T' in value and ('Z' in value or '+' in value)):
            # Looks like a timestamp
            converted[key] = convert_timestamp_to_firefoo_format(value)
        elif isinstance(value, dict):
            converted[key] = convert_nested_object(value)
        else:
            converted[key] = value
    return converted

def load_all_profiles(profiles_dir: Path) -> List[Dict[str, Any]]:
    """Load all JSON profiles from the profiles directory."""
    profiles = []
    
    if not profiles_dir.exists():
        print(f"Error: Profiles directory '{profiles_dir}' does not exist")
        return profiles
    
    json_files = list(profiles_dir.glob("*.json"))
    print(f"Found {len(json_files)} profile files")
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)
                profiles.append(profile_data)
        except Exception as e:
            print(f"Error loading {json_file}: {e}")
            continue
    
    print(f"Successfully loaded {len(profiles)} profiles")
    return profiles

def generate_firefoo_export(profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate the complete Firefoo export structure."""
    
    # Create the Firefoo metadata
    firefoo_export = {
        "meta": {
            "format": "JSON",
            "version": "1.1.0",
            "projectId": "commissioner-profiles",  # You may want to change this
            "resourcePath": ["commissioner_profiles"],
            "recursive": False,
            "creationTime": int(time.time()),
            "app": "firefoo"
        },
        "data": {}
    }
    
    # Convert each profile to Firefoo format
    for profile in profiles:
        doc_id = generate_document_id(profile)
        converted_profile = convert_profile_to_firefoo_format(profile)
        firefoo_export["data"][doc_id] = converted_profile
    
    return firefoo_export

def main():
    """Main function to generate the Firefoo export file."""
    print("Generating Firefoo export for commissioner profiles...")
    
    # Set up paths
    profiles_dir = Path("profiles")
    output_file = Path("commissioner_profiles_firefoo_export.json")
    
    # Load all profiles
    profiles = load_all_profiles(profiles_dir)
    
    if not profiles:
        print("No profiles found. Exiting.")
        return
    
    # Generate Firefoo export
    print("Converting profiles to Firefoo format with data cleaning...")
    firefoo_export = generate_firefoo_export(profiles)
    
    # Count data quality issues cleaned
    print("Data cleaning summary:")
    invalid_email_count = 0
    cleaned_field_count = 0
    
    for doc_id, doc_data in firefoo_export["data"].items():
        original_profile = next((p for p in profiles if generate_document_id(p) == doc_id), {})
        
        # Check for cleaned emails
        original_email = original_profile.get("email", "")
        if original_email and is_invalid_data(original_email, "email"):
            invalid_email_count += 1
            
        # Count other cleaned fields
        for field_name in original_profile.keys():
            if field_name != "email" and is_invalid_data(original_profile.get(field_name), field_name):
                cleaned_field_count += 1
    
    print(f"  - Invalid emails cleaned: {invalid_email_count}")
    print(f"  - Other invalid fields cleaned: {cleaned_field_count}")
    
    # Save the export file
    print(f"Saving cleaned export to {output_file}...")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(firefoo_export, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Successfully generated cleaned Firefoo export!")
        print(f"📁 File: {output_file}")
        print(f"📊 Profiles: {len(profiles)}")
        print(f"📏 File size: {output_file.stat().st_size / 1024:.1f} KB")
        
        # Show a sample of document IDs
        doc_ids = list(firefoo_export["data"].keys())
        print(f"\n📋 Sample document IDs:")
        for doc_id in doc_ids[:5]:
            profile_name = firefoo_export["data"][doc_id].get("name", "Unknown")
            print(f"  - {doc_id}: {profile_name}")
        if len(doc_ids) > 5:
            print(f"  ... and {len(doc_ids) - 5} more")
            
    except Exception as e:
        print(f"❌ Error saving export file: {e}")
        return
    
    print(f"\n🚀 Ready to import into Firestore via Firefoo!")
    print(f"   Collection path: commissioner_profiles")
    print(f"   Import file: {output_file}")
    print(f"\n📋 Data Quality Improvements:")
    print(f"   - Invalid emails are now excluded (null)")
    print(f"   - Empty/invalid fields are cleaned or excluded")
    print(f"   - Placeholder data patterns removed")
    print(f"   - Only valid, non-empty data included")

if __name__ == "__main__":
    main()
