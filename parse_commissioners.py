#!/usr/bin/env python3
"""
Commissioner Profile Parser
Converts markdown commissioner profiles to structured JSON for Firebase Firestore
"""

import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

class CommissionerParser:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.commissioners = []
        
    def clean_text(self, text: str) -> str:
        """Clean markdown formatting and normalize text"""
        if not text:
            return ""
        
        # Remove markdown formatting
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*([^*]+)\*', r'\1', text)      # Italic
        text = re.sub(r'`([^`]+)`', r'\1', text)        # Code
        text = re.sub(r'#+\s*', '', text)               # Headers
        text = re.sub(r'^\s*[-•]\s*', '', text, flags=re.MULTILINE)  # Bullet points
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def extract_country_from_path(self, file_path: str) -> str:
        """Extract country/region from folder structure"""
        path_parts = Path(file_path).parts
        
        # Find the parent folder that contains the profile
        for i, part in enumerate(path_parts):
            if 'Commissioning Assistant Profiles' in part:
                # Get the next part which should be the country folder
                if i + 1 < len(path_parts):
                    country_folder = path_parts[i + 1]
                    # Clean up the folder name to get country/region
                    # Split by space and take everything before the ID
                    country_parts = country_folder.split(' ')
                    if len(country_parts) > 1:
                        # Join all parts except the last one (which is usually the ID)
                        country = ' '.join(country_parts[:-1])
                    else:
                        country = country_parts[0]
                    
                    # Remove any leading numbers
                    country = re.sub(r'^\d+\s*', '', country)
                    return country
        
        return "Unknown"
    
    def parse_list_items(self, text: str) -> List[str]:
        """Parse bullet points and list items into array"""
        if not text:
            return []
        
        # Split by lines and clean up
        lines = text.split('\n')
        items = []
        current_item = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                # Empty line - if we have a current item, save it
                if current_item:
                    items.append(self.clean_text(current_item))
                    current_item = ""
                continue
            
            # Check if this line starts a new list item
            if re.match(r'^\s*[-•·]\s*', line) or re.match(r'^\s*\d+\.\s*', line):
                # Save previous item if exists
                if current_item:
                    items.append(self.clean_text(current_item))
                
                # Start new item, removing bullet/number
                current_item = re.sub(r'^\s*[-•·]\s*', '', line)
                current_item = re.sub(r'^\s*\d+\.\s*', '', current_item)
            else:
                # Continuation of current item (multi-line)
                if current_item:
                    current_item += " " + line
                else:
                    current_item = line
        
        # Don't forget the last item
        if current_item:
            items.append(self.clean_text(current_item))
        
        return [item for item in items if item and len(item.strip()) > 0]
    
    def extract_field_content(self, content: str, field_name: str, is_list: bool = False) -> Any:
        """Extract content for a specific field"""
        # Pattern to match field sections - use simpler patterns that work
        patterns = [
            # Simple format: "Field Name: value" (single line)
            rf'^{re.escape(field_name)}:\s*([^\n]+)',
            # Markdown bold format: "**Field Name**\n\ncontent" until next section
            rf'\*\*{re.escape(field_name)}\*\*\s*\n\n(.*?)\n\n\*\*',
            # Markdown bold format: "**Field Name**\n\ncontent" until end of file
            rf'\*\*{re.escape(field_name)}\*\*\s*\n\n(.*?)$',
            # Header format: "# Field Name\n\ncontent" until next section
            rf'#{re.escape(field_name)}\s*\n\n(.*?)\n\n#',
            # Header format: "# Field Name\n\ncontent" until end of file
            rf'#{re.escape(field_name)}\s*\n\n(.*?)$',
            # Inline bold format with newline
            rf'\*\*{re.escape(field_name)}\*\*\s*\n(.*?)\n\n\*\*',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE | re.MULTILINE)
            if match:
                text = match.group(1).strip()
                if is_list:
                    # For lists, preserve newlines for proper parsing
                    return self.parse_list_items(text)
                else:
                    # For single values, clean the text
                    return self.clean_text(text)
        
        return [] if is_list else ""
    
    def parse_basic_info(self, content: str) -> Dict[str, str]:
        """Parse basic information section (extended format)"""
        info = {}
        
        # Extract structured basic info
        patterns = {
            'full_name': r'\*\*Full Name:\*\*\s*([^\n]+)',
            'job_title': r'\*\*Job Title:\*\*\s*([^\n]+)',
            'department': r'\*\*Department:\*\*\s*([^\n]+)',
            'organization': r'\*\*Organization:\*\*\s*([^\n]+)',
            'professional_contact': r'\*\*Professional Contact:\*\*\s*([^\n]+)',
            'reporting_structure': r'\*\*Reporting Structure:\*\*\s*([^\n]+)',
            'location': r'\*\*Location:\*\*\s*([^\n]+)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                info[key] = self.clean_text(match.group(1))
        
        return info
    
    def parse_simple_format(self, content: str, file_path: str) -> Dict[str, Any]:
        """Parse simple format profiles"""
        commissioner = {
            'id': self.generate_id(file_path),
            'country_region': self.extract_country_from_path(file_path),
            'source_file': str(file_path),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
        }
        
        # Extract simple format fields
        field_mappings = {
            'organization': ('Organization', False),
            'role': ('Role', False),
            'email': ('Professional Contact', False),
            'location': ('Location', False),
            'background': ('Background & Programming Philosophy', False),
            'thematic_priorities': ('Thematic Priorities', True),
            'content_not_wanted': ('Content Not Wanted', True),
            'target_audience': ('Target Audience', True),
            'format_specifications': ('Format Specifications', True),
            'budget_parameters': ('Budget Parameters', False),
            'technical_requirements': ('Technical Requirements', True),
            'current_calls': ('Current Specific Calls / Focus', True),
            'submission_process': ('Submission Process', True),
        }
        
        for field_key, (field_name, is_list) in field_mappings.items():
            commissioner[field_key] = self.extract_field_content(content, field_name, is_list)
        
        # Extract name from title or content
        title_match = re.search(r'^#\s*([^\n]+)', content, re.MULTILINE)
        if title_match:
            title = self.clean_text(title_match.group(1))
            # Try to extract name from "Commissioner Profile:" line
            name_match = re.search(r'\*\*Commissioner Profile:\s*([^\*\n]+)', content)
            if name_match:
                commissioner['name'] = self.clean_text(name_match.group(1))
            else:
                # Fall back to cleaning up the title
                name = title.replace('_FULL', '').replace('_', ' ')
                name = re.sub(r'^\w+\s+', '', name)  # Remove prefix like "AJD_"
                commissioner['name'] = name
        
        return commissioner
    
    def parse_extended_format(self, content: str, file_path: str) -> Dict[str, Any]:
        """Parse extended format profiles"""
        commissioner = {
            'id': self.generate_id(file_path),
            'country_region': self.extract_country_from_path(file_path),
            'source_file': str(file_path),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
        }
        
        # Parse basic information section
        basic_info = self.parse_basic_info(content)
        commissioner.update(basic_info)
        
        # Map basic info to standard fields
        if 'full_name' in basic_info:
            commissioner['name'] = basic_info['full_name']
        if 'job_title' in basic_info:
            commissioner['role'] = basic_info['job_title']
        if 'professional_contact' in basic_info:
            commissioner['email'] = basic_info['professional_contact']
        
        # Extract other fields
        field_mappings = {
            'background': ('Background & Programming Philosophy', False),
            'thematic_priorities': ('Thematic Priorities', True),
            'content_not_wanted': ('Content Not Wanted', True),
            'target_audience': ('Target Audience', True),
            'format_specifications': ('Format Specifications', True),
            'budget_parameters': ('Budget Parameters', False),
            'technical_requirements': ('Technical Requirements', True),
            'current_calls': ('Current Specific Calls', True),
            'submission_process': ('Submission Process', True),
            'recent_commissions': ('Recent Representative Commissions', False),
            'specialist_areas': ('Focus on Specialist Areas', True),
        }
        
        for field_key, (field_name, is_list) in field_mappings.items():
            result = self.extract_field_content(content, field_name, is_list)
            if result:  # Only add if not empty
                commissioner[field_key] = result
        
        # Extract additional information
        additional_info = {}
        additional_patterns = {
            'commissioning_cycles': r'Commissioning Cycles:\*\*\s*([^\n]+)',
            'strategic_shifts': r'Strategic Shifts:\*\*\s*([^\n]+)',
            'diversity_inclusion': r'Diversity & Inclusion:\*\*\s*([^\n]+)',
            'sustainability': r'Sustainability:\*\*\s*([^\n]+)',
            'regional_production': r'Regional Production:\*\*\s*([^\n]+)',
            'independent_production': r'Independent Production:\*\*\s*([^\n]+)',
        }
        
        for key, pattern in additional_patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                additional_info[key] = self.clean_text(match.group(1))
        
        if additional_info:
            commissioner['additional_info'] = additional_info
        
        return commissioner
    
    def generate_id(self, file_path: str) -> str:
        """Generate unique ID from filename"""
        filename = Path(file_path).stem
        # Clean up the filename to create ID
        id_str = filename.lower()
        id_str = re.sub(r'_full$', '', id_str)
        id_str = re.sub(r'[^a-z0-9_]', '_', id_str)
        id_str = re.sub(r'_+', '_', id_str)
        id_str = id_str.strip('_')
        return id_str
    
    def is_extended_format(self, content: str) -> bool:
        """Determine if this is an extended format profile"""
        return '# Basic Information' in content or '**Full Name:**' in content
    
    def parse_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Parse a single markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.strip():
                return None
            
            # Determine format and parse accordingly
            if self.is_extended_format(content):
                commissioner = self.parse_extended_format(content, file_path)
            else:
                commissioner = self.parse_simple_format(content, file_path)
            
            # Ensure required fields are present
            required_fields = ['name', 'organization', 'role', 'email', 'location']
            for field in required_fields:
                if field not in commissioner or not commissioner[field]:
                    print(f"Warning: Missing required field '{field}' in {file_path}")
            
            return commissioner
            
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None
    
    def find_profile_files(self) -> List[str]:
        """Find all commissioner profile markdown files"""
        profile_files = []
        
        # Look for all .md files in country/organization subdirectories
        for root, dirs, files in os.walk(self.base_path):
            # Only process files in subdirectories that have the ID pattern
            if any(folder_id in root for folder_id in ['2724b6c9c5078', '2734b6c9c5078']):
                for file in files:
                    if file.endswith('.md'):
                        # Skip the summary files (those in the root directory)
                        file_path = os.path.join(root, file)
                        # Check if this is a profile file (in a subfolder, not the summary)
                        if os.path.basename(root) != os.path.basename(self.base_path):
                            profile_files.append(file_path)
        
        return profile_files
    
    def parse_all(self) -> List[Dict[str, Any]]:
        """Parse all commissioner profiles"""
        profile_files = self.find_profile_files()
        print(f"Found {len(profile_files)} profile files")
        
        commissioners = []
        for file_path in profile_files:
            try:
                print(f"Parsing: {os.path.basename(file_path)}")
                commissioner = self.parse_file(file_path)
                if commissioner:
                    commissioners.append(commissioner)
            except UnicodeEncodeError:
                # Handle Unicode issues in file names
                print(f"Parsing: [Unicode filename]")
                commissioner = self.parse_file(file_path)
                if commissioner:
                    commissioners.append(commissioner)
        
        self.commissioners = commissioners
        return commissioners
    
    def save_json(self, output_path: str = 'commissioners_data.json'):
        """Save parsed data to JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.commissioners, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(self.commissioners)} commissioner profiles to {output_path}")
    
    def save_individual_json_files(self, output_dir: str = 'parsed'):
        """Save each commissioner as an individual JSON file"""
        import os
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        saved_count = 0
        for commissioner in self.commissioners:
            # Create filename from person name and country
            name = commissioner.get('name', 'Unknown')
            country = commissioner.get('country_region', 'Unknown')
            
            # Clean up name and country for filename
            clean_name = re.sub(r'[^\w\s-]', '', name)  # Remove special chars except spaces and hyphens
            clean_name = re.sub(r'\s+', '_', clean_name)  # Replace spaces with underscores
            clean_country = re.sub(r'[^\w\s-]', '', country)  # Remove special chars
            clean_country = re.sub(r'\s+', '_', clean_country)  # Replace spaces with underscores
            
            filename = f"{clean_name}_{clean_country}.json"
            filepath = os.path.join(output_dir, filename)
            
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(commissioner, f, indent=2, ensure_ascii=False)
                saved_count += 1
            except Exception as e:
                print(f"Error saving {filename}: {e}")
        
        print(f"Saved {saved_count} individual commissioner JSON files to {output_dir}/ directory")
        return saved_count
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the parsed data"""
        if not self.commissioners:
            return {}
        
        stats = {
            'total_commissioners': len(self.commissioners),
            'countries_regions': list(set(c.get('country_region', 'Unknown') for c in self.commissioners)),
            'organizations': list(set(c.get('organization', 'Unknown') for c in self.commissioners)),
            'field_coverage': {}
        }
        
        # Check field coverage
        all_fields = set()
        for commissioner in self.commissioners:
            all_fields.update(commissioner.keys())
        
        for field in all_fields:
            count = sum(1 for c in self.commissioners if c.get(field))
            stats['field_coverage'][field] = {
                'count': count,
                'percentage': round(count / len(self.commissioners) * 100, 1)
            }
        
        return stats

def main():
    # Initialize parser
    base_path = "notion/Commissioning Assistant Profiles 2724b6c9c50780d6aa98f69ccc91f0b3"
    parser = CommissionerParser(base_path)
    
    # Parse all profiles
    commissioners = parser.parse_all()
    
    # Save individual JSON files
    parser.save_individual_json_files()
    
    # Print statistics
    stats = parser.get_statistics()
    print("\n=== PARSING STATISTICS ===")
    print(f"Total commissioners: {stats['total_commissioners']}")
    print(f"Countries/regions: {len(stats['countries_regions'])}")
    print(f"Organizations: {len(stats['organizations'])}")
    
    print(f"\nCountries/regions: {', '.join(sorted(stats['countries_regions']))}")
    
    print(f"\nField coverage:")
    for field, info in sorted(stats['field_coverage'].items()):
        print(f"  {field}: {info['count']}/{stats['total_commissioners']} ({info['percentage']}%)")

if __name__ == "__main__":
    main()
