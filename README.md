# Commissioner Data Processing Project

## Overview

A comprehensive data processing pipeline that converts broadcasting commissioner profiles from Notion exports into structured, schema-validated JSON data ready for Firebase Firestore or other database systems. The project features both parsing and AI-powered conversion capabilities with concurrent processing support.

## Project Status

✅ **266 commissioner profiles** successfully converted to structured JSON format  
✅ **Schema-validated data** using comprehensive OpenAPI 3.0.4 specification  
✅ **Concurrent processing** support (1-5 workers) for faster conversion  
✅ **Multiple input modes** - direct markdown processing or pre-parsed JSON  
✅ **Firefoo export** ready for direct Firestore import via Firefoo tool  
✅ **Data quality validation** with automatic cleaning of invalid/placeholder data  

## Architecture

### Data Flow
```
Notion Export (.md files) 
    ↓ 
[parse_commissioners.py] → Parsed JSON (253 files)
    ↓
[convert_to_schema.py] → Schema-validated JSON (266 files)
    ↓
[generate_firefoo_export.py] → Firefoo-compatible JSON (data quality cleaned)
    ↓
Firebase Firestore Import via Firefoo
```

## Key Features

### 1. **Dual Processing Modes**
- **Direct Markdown Processing**: Convert .md files directly to schema format
- **Parsed JSON Processing**: Convert pre-parsed JSON to schema format
- **Automatic Format Detection**: Handles both simple and extended profile formats

### 2. **AI-Powered Conversion**
- **OpenAI Integration**: Uses GPT-4o-mini for intelligent data extraction
- **Schema Validation**: Ensures all output matches the defined schema
- **Structured Outputs**: Leverages OpenAI's structured output capabilities

### 3. **Concurrent Processing**
- **Configurable Workers**: Process 1-5 files simultaneously
- **Thread-Safe Operations**: Safe concurrent API calls and file operations
- **Rate Limit Aware**: Respects API rate limits with controlled concurrency

### 4. **Comprehensive Schema**
- **24+ Structured Fields**: Complete profile representation
- **Enum Validation**: Standardized values for themes, formats, audience segments
- **Flexible Design**: Handles various profile formats and missing data

### 5. **Firefoo Export & Data Quality**
- **Direct Firestore Import**: One-click import via Firefoo tool
- **Automatic Data Cleaning**: Removes invalid emails, placeholder data, and empty fields
- **Quality Validation**: Detects and handles 10+ patterns of invalid/missing data
- **Optimized Format**: Proper timestamp formatting and document structure for Firestore

## File Structure

```
commissioner-data/
├── README.md                                    # This documentation
├── requirements.txt                             # Python dependencies
├── commissioning_profiles_data_schema.json     # OpenAPI 3.0.4 schema definition
├── 
├── # Scripts
├── parse_commissioners.py                       # Initial markdown parser
├── convert_to_schema.py                        # AI-powered schema converter
├── generate_firefoo_export.py                 # Firefoo export generator
├── test_single_conversion.py                  # Testing utilities
├── 
├── # Data Directories
├── notion/                                     # Original Notion export (307 .md files)
├── parsed/                                     # Parsed JSON files (253 files)
├── profiles/                                   # Final schema-validated JSON (266 files)
├── 
├── # Export Files
├── commissioner_profiles_firefoo_export.json  # Firefoo-ready export (cleaned data)
├── 
├── # Logs and Outputs
├── conversion.log                              # Processing logs
├── parse_output.txt                           # Parser output log
└── parsed_schema.json                         # Legacy schema file
```

## Data Schema

### Core Profile Structure
```json
{
  "id": "unique_identifier",
  "country_region": "geographical_location",
  "platform_type": "broadcaster_type_enum",
  "organization": "organization_name", 
  "role": "job_title",
  "commissioner_type": "content_type_enum",
  "email": "professional_contact",
  "location": "geographic_location",
  "name": "commissioner_name",
  "background": "programming_philosophy",
  
  "thematic_priorities": ["original_text_priorities"],
  "themes": ["standardized_theme_enums"],
  "content_not_wanted": ["content_restrictions"],
  "target_audience": ["original_audience_text"],
  "audience_segments": ["standardized_audience_enums"],
  "format_specifications": ["original_format_text"],
  "formats": ["standardized_format_enums"],
  
  "budget_parameters": "budget_information",
  "budget_min_usd": 50000,
  "budget_max_usd": 200000,
  
  "technical_requirements": ["delivery_specs"],
  "delivery_requirements": ["standardized_delivery_enums"],
  "current_calls": ["active_opportunities"],
  "submission_process": ["application_process"],
  
  "created_at": "2025-09-19T11:23:17.967502+00:00",
  "updated_at": "2025-09-19T11:23:17.967502+00:00",
  "source_file": "path/to/original/file.md"
}
```

### Enum Values

**Themes**: `arts_culture`, `natural_history`, `climate_environment`, `social_issues`, `science_technology`, `politics_current_affairs`, `business_economics`, `health_lifestyle`, `travel_adventure`, `food_cooking`, `sports_fitness`, `education_learning`, `religion_spirituality`, `crime_justice`, `entertainment_celebrity`, `family_relationships`, `history_biography`

**Audience Segments**: `general_audience`, `young_adults`, `families`, `children`, `seniors`, `professionals`, `niche_interest`, `international_audience`, `local_regional`, `premium_educated`

**Formats**: `documentary`, `factual_series`, `reality_tv`, `news_current_affairs`, `entertainment_variety`, `drama_scripted`, `childrens_content`, `educational_content`, `sports_content`, `lifestyle_content`, `animation`, `short_form_content`

**Platform Types**: `traditional_broadcaster`, `public_broadcaster`, `commercial_broadcaster`, `streaming_platform`, `cable_network`, `news_network`, `international_broadcaster`, `regional_broadcaster`, `specialty_channel`, `production_company`, `digital_platform`

## Usage Instructions

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Set up OpenAI API key in convert_to_schema.py (line 422)
```

### Basic Usage

#### Convert All Files (Sequential)
```bash
# Convert from markdown files (recommended)
python convert_to_schema.py --input-mode markdown

# Convert from pre-parsed JSON files
python convert_to_schema.py --input-mode parsed
```

#### Concurrent Processing
```bash
# Process 3 files concurrently
python convert_to_schema.py --concurrency 3

# Maximum concurrency (5 workers)
python convert_to_schema.py --concurrency 5
```

#### Single File Processing
```bash
# Convert a specific file
python convert_to_schema.py --single-file "filename.md"
```

#### Advanced Options
```bash
# Force reprocess all files
python convert_to_schema.py --force-reprocess

# Combine options
python convert_to_schema.py --input-mode markdown --concurrency 3 --force-reprocess
```

### Initial Parsing (if needed)
```bash
# Parse original markdown files to JSON
python parse_commissioners.py
```

### Generate Firefoo Export
```bash
# Generate Firefoo-compatible export for Firestore import
python generate_firefoo_export.py
```

## Data Quality & Coverage

### Processing Results
- **Total Profiles**: 266 successfully converted
- **Success Rate**: ~86% (266/307 original files)
- **Schema Validation**: 100% of converted files pass validation
- **Geographic Coverage**: 17+ countries/regions
- **Organizations**: 64+ different broadcasting organizations

### Field Coverage (Sample Analysis)
- **Core Fields**: 95-100% coverage (name, country, organization)
- **Contact Information**: ~94% have valid email addresses (invalid/placeholder emails removed)
- **Content Preferences**: 98%+ coverage for thematic priorities
- **Budget Information**: 90%+ coverage with standardized USD ranges
- **Technical Requirements**: 95%+ coverage with enum standardization

### Data Quality Improvements
- **12 invalid emails** cleaned (placeholder patterns like `/not_provided/undefined@mail.com`)
- **149 invalid fields** cleaned (empty strings, placeholder data, undefined values)
- **Automatic validation** for email format, domain, and placeholder patterns
- **Smart defaults** applied based on field type (null for emails, empty arrays for lists)

### Geographic Distribution
**Europe**: UK, Germany, France, Denmark, Finland, Estonia, Latvia, Lithuania, Poland, Czechia, Croatia, Bosnia, Serbia, Romania, Spain, Portugal, Switzerland, Sweden, Netherlands, Ireland, Italy, Greece, Turkey, Ukraine

**North America**: USA (Broadcasters & Streamers), Canada

**Middle East & Africa**: UAE, Saudi Arabia, Egypt, Morocco

**Asia-Pacific**: Australia, Japan

**International**: Al Jazeera, BBC World News, Deutsche Welle, France 24, Netflix Europe, Amazon Prime Europe, Apple TV Europe

## Firebase Firestore Integration

### Firefoo Import (Recommended)
The easiest way to import data into Firestore:

1. **Generate Export File:**
   ```bash
   python generate_firefoo_export.py
   ```

2. **Import via Firefoo:**
   - Open [Firefoo](https://firefoo.app) in your browser
   - Connect to your Firebase project
   - Import `commissioner_profiles_firefoo_export.json`
   - Data will be imported to `commissioner_profiles` collection

### Manual Import Script (Alternative)
```python
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os

# Initialize Firebase
cred = credentials.Certificate('path/to/serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

# Import all profiles
profiles_dir = 'profiles'
collection_ref = db.collection('commissioners')

for filename in os.listdir(profiles_dir):
    if filename.endswith('.json'):
        with open(os.path.join(profiles_dir, filename), 'r', encoding='utf-8') as f:
            profile = json.load(f)
            doc_id = profile['id']
            collection_ref.document(doc_id).set(profile)
            print(f"Imported: {profile['name']}")

print("Import completed!")
```

### Recommended Firestore Indexes
```javascript
// Compound indexes for common queries
db.collection('commissioners').createIndex([
  ['country_region', 'asc'],
  ['platform_type', 'asc']
]);

db.collection('commissioners').createIndex([
  ['themes', 'array-contains'],
  ['country_region', 'asc']
]);

db.collection('commissioners').createIndex([
  ['formats', 'array-contains'],
  ['budget_min_usd', 'asc']
]);
```

## API Integration

The structured data is perfect for building search and discovery APIs:

### Search by Theme
```javascript
// Find documentaries commissioners in Europe
const commissioners = await db.collection('commissioners')
  .where('formats', 'array-contains', 'documentary')
  .where('country_region', 'in', ['UK', 'Germany', 'France'])
  .get();
```

### Budget Range Filtering
```javascript
// Find commissioners with budget 100k-500k USD
const commissioners = await db.collection('commissioners')
  .where('budget_min_usd', '>=', 100000)
  .where('budget_max_usd', '<=', 500000)
  .get();
```

## Development & Maintenance

### Adding New Profiles
1. Add new .md files to the `notion/` directory structure
2. Run `python convert_to_schema.py --input-mode markdown`
3. Run `python generate_firefoo_export.py` to update the Firestore export
4. New profiles will be automatically processed, validated, and ready for import

### Schema Updates
1. Modify `commissioning_profiles_data_schema.json`
2. Update the `_prepare_structured_schema()` method in `convert_to_schema.py`
3. Reprocess existing data if needed with `--force-reprocess`
4. Regenerate Firefoo export with `python generate_firefoo_export.py`

### Monitoring & Logs
- **Processing Logs**: Check `conversion.log` for detailed processing information
- **Thread Safety**: Logs include thread names for concurrent processing tracking
- **Error Handling**: Failed conversions are logged with detailed error messages

## Technical Specifications

### Dependencies
- **Python 3.8+**
- **OpenAI API** (GPT-4o-mini)
- **jsonschema** for validation
- **concurrent.futures** for parallel processing

### Performance
- **Sequential Processing**: ~2-3 files per minute
- **Concurrent Processing (5 workers)**: ~8-12 files per minute
- **Memory Usage**: ~50-100MB during processing
- **API Rate Limits**: Automatically managed through concurrency controls

### Error Handling
- **Validation Failures**: Profiles that don't match schema are rejected
- **API Failures**: Automatic retry logic with detailed error logging
- **File System Errors**: Graceful handling of missing or corrupted files
- **Data Quality Issues**: Automatic detection and cleaning of invalid/placeholder data

## Future Enhancements

### Planned Features
- [ ] **Automatic Data Enrichment**: Web scraping for missing contact information
- [ ] **Real-time Sync**: Integration with Notion API for live updates
- [ ] **Advanced Search**: Elasticsearch integration for full-text search
- [ ] **Data Visualization**: Analytics dashboard for commissioner insights
- [ ] **Contact Verification**: Email validation and contact verification workflows

### Schema Evolution
- [ ] **Multi-language Support**: Internationalization for global profiles
- [ ] **Historical Tracking**: Version control for profile changes
- [ ] **Relationship Mapping**: Links between commissioners and productions
- [ ] **Advanced Filtering**: More granular content preferences and requirements

## Contributing

### Code Style
- Follow PEP 8 for Python code
- Use type hints for function parameters
- Maintain comprehensive logging
- Write unit tests for new features

### Testing
```bash
# Test single file conversion
python test_single_conversion.py

# Test Firefoo export generation
python generate_firefoo_export.py

# Validate schema compliance
python -c "import json; from jsonschema import validate; 
with open('commissioning_profiles_data_schema.json') as f: schema = json.load(f);
with open('profiles/sample.json') as f: data = json.load(f);
validate(data, schema['components']['schemas']['CommissioningProfile'])"
```

## Support & Contact

For questions, issues, or contributions:
- Check the `conversion.log` for processing details
- Review the schema documentation in `commissioning_profiles_data_schema.json`
- Examine sample outputs in the `profiles/` directory
- Test Firefoo export with `commissioner_profiles_firefoo_export.json`

## Quick Start Guide

1. **Convert profiles to schema format:**
   ```bash
   python convert_to_schema.py --input-mode markdown --concurrency 3
   ```

2. **Generate Firestore-ready export:**
   ```bash
   python generate_firefoo_export.py
   ```

3. **Import to Firestore:**
   - Open [Firefoo](https://firefoo.app)
   - Import `commissioner_profiles_firefoo_export.json`
   - Collection: `commissioner_profiles`

---

**Last Updated**: September 19, 2025  
**Total Profiles**: 266 converted profiles ready for production use  
**Schema Version**: 1.0.0 (OpenAPI 3.0.4 compliant)  
**Export Format**: Firefoo-compatible with data quality validation