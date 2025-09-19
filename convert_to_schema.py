import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from openai import OpenAI
import jsonschema
from jsonschema import validate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('conversion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CommissionerConverter:
    def __init__(self, api_key: str):
        """Initialize the converter with OpenAI client and schema."""
        self.client = OpenAI(api_key=api_key)
        self.schema = self._load_schema()
        self.parsed_dir = Path("parsed")
        self.profiles_dir = Path("profiles")
        
        # Create profiles directory if it doesn't exist
        self.profiles_dir.mkdir(exist_ok=True)
        
        # Extract just the schema part for validation
        self.validation_schema = self.schema["components"]["schemas"]["CommissioningProfile"]
        
        # Prepare schema for structured outputs (ensure additionalProperties: false)
        self.structured_schema = self._prepare_structured_schema(self.validation_schema)
        
    def _load_schema(self) -> Dict[str, Any]:
        """Load the commissioning profiles data schema."""
        try:
            with open("commissioning_profiles_data_schema.json", "r", encoding="utf-8") as f:
                schema = json.load(f)
            logger.info("Successfully loaded commissioning profiles data schema")
            return schema
        except Exception as e:
            logger.error(f"Failed to load schema: {e}")
            raise
    
    def _prepare_structured_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare schema for OpenAI structured outputs by ensuring additionalProperties: false and all properties are required."""
        import copy
        structured_schema = copy.deepcopy(schema)
        
        def prepare_for_structured_output(obj, path=""):
            if isinstance(obj, dict):
                if obj.get("type") == "object":
                    # Handle the special case of additional_info which allows arbitrary properties
                    if "additional_info" in path:
                        # Convert to a simple string field for structured outputs
                        obj["type"] = "string"
                        obj.pop("additionalProperties", None)
                        obj.pop("properties", None)
                    else:
                        obj["additionalProperties"] = False
                        # For structured outputs, all properties must be required
                        if "properties" in obj:
                            obj["required"] = list(obj["properties"].keys())
                
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    prepare_for_structured_output(value, new_path)
            elif isinstance(obj, list):
                for item in obj:
                    prepare_for_structured_output(item, path)
        
        prepare_for_structured_output(structured_schema)
        return structured_schema
    
    def _get_processed_files(self) -> set:
        """Get list of already processed commissioner files."""
        processed = set()
        if self.profiles_dir.exists():
            for file_path in self.profiles_dir.glob("*.json"):
                processed.add(file_path.stem)
        return processed
    
    def _validate_converted_data(self, data: Dict[str, Any]) -> bool:
        """Validate the converted data against the schema."""
        try:
            validate(instance=data, schema=self.validation_schema)
            return True
        except jsonschema.ValidationError as e:
            logger.error(f"Schema validation failed: {e.message}")
            logger.error(f"Failed at path: {' -> '.join(str(p) for p in e.absolute_path)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected validation error: {e}")
            return False
    
    def _convert_single_commissioner(self, parsed_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert a single commissioner's parsed data using OpenAI structured outputs."""
        try:
            # Prepare the prompt
            system_prompt = """You are an expert data conversion specialist. Convert the provided parsed commissioner data to match the exact schema format provided.

Key conversion guidelines:
1. Map all existing fields to their schema equivalents
2. Categorize thematic_priorities into the predefined themes enum values
3. Classify target_audience into the audience_segments enum values  
4. Convert format_specifications to the formats enum values
5. Extract budget ranges and convert to min/max USD values where possible
6. Determine platform_type, commissioner_type, geographic_scope based on the data
7. Set appropriate boolean flags for diversity_focus, sustainability_focus, festival_potential_required
8. Convert technical_requirements to delivery_requirements enum values
9. Determine appropriate production_values level
10. Set commissioning_cycles and co_production_openness based on context
11. Extract and standardize languages
12. Preserve all original data in appropriate fields while also providing sanitized enum versions

Ensure all required fields are populated and all enum values match exactly."""

            user_prompt = f"Convert this commissioner data to the schema format:\n\n{json.dumps(parsed_data, indent=2)}"
            
            # Make the API call with structured output
            response = self.client.responses.create(
                model="gpt-5-nano",  # Use gpt-5-nano as specified
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "commissioning_profile",
                        "schema": self.structured_schema,
                        "strict": True
                    }
                }
            )
            
            # Check for refusal or errors
            if response.status != "completed":
                logger.error(f"API call incomplete. Status: {response.status}")
                if hasattr(response, 'incomplete_details'):
                    logger.error(f"Incomplete reason: {response.incomplete_details.reason}")
                return None
            
            # Check if the response was refused
            if response.output and len(response.output) > 0:
                content = response.output[0].content[0]
                if hasattr(content, 'type') and content.type == "refusal":
                    logger.error(f"API refused to process: {content.refusal}")
                    return None
            
            # Parse the response
            converted_data = json.loads(response.output_text)
            
            # Add timestamps
            now = datetime.utcnow().isoformat()
            converted_data["created_at"] = now
            converted_data["updated_at"] = now
            
            return converted_data
            
        except Exception as e:
            logger.error(f"Error converting commissioner data: {e}")
            return None
    
    def convert_all_commissioners(self, force_reprocess: bool = False) -> Dict[str, str]:
        """Convert all commissioners in the parsed directory."""
        results = {"success": [], "failed": [], "skipped": []}
        
        # Get already processed files
        processed_files = set() if force_reprocess else self._get_processed_files()
        
        # Get all parsed JSON files
        parsed_files = list(self.parsed_dir.glob("*.json"))
        
        if not parsed_files:
            logger.warning("No parsed files found in the parsed directory")
            return results
        
        logger.info(f"Found {len(parsed_files)} parsed files to process")
        logger.info(f"Already processed: {len(processed_files)} files")
        
        for file_path in parsed_files:
            commissioner_id = file_path.stem
            
            # Skip if already processed
            if commissioner_id in processed_files:
                logger.info(f"Skipping {commissioner_id} - already processed")
                results["skipped"].append(commissioner_id)
                continue
            
            logger.info(f"Processing {commissioner_id}...")
            
            try:
                # Load parsed data
                with open(file_path, "r", encoding="utf-8") as f:
                    parsed_data = json.load(f)
                
                # Convert using OpenAI
                converted_data = self._convert_single_commissioner(parsed_data)
                
                if converted_data is None:
                    logger.error(f"Failed to convert {commissioner_id}")
                    results["failed"].append(commissioner_id)
                    continue
                
                # Validate converted data
                if not self._validate_converted_data(converted_data):
                    logger.error(f"Validation failed for {commissioner_id}")
                    results["failed"].append(commissioner_id)
                    continue
                
                # Save converted data
                output_path = self.profiles_dir / f"{commissioner_id}.json"
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(converted_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Successfully converted and saved {commissioner_id}")
                results["success"].append(commissioner_id)
                
            except Exception as e:
                logger.error(f"Error processing {commissioner_id}: {e}")
                results["failed"].append(commissioner_id)
        
        return results
    
    def convert_single_file(self, filename: str) -> bool:
        """Convert a single commissioner file."""
        file_path = self.parsed_dir / filename
        if not file_path.exists():
            logger.error(f"File not found: {filename}")
            return False
        
        commissioner_id = file_path.stem
        logger.info(f"Converting single file: {commissioner_id}")
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                parsed_data = json.load(f)
            
            converted_data = self._convert_single_commissioner(parsed_data)
            
            if converted_data is None:
                logger.error(f"Failed to convert {commissioner_id}")
                return False
            
            if not self._validate_converted_data(converted_data):
                logger.error(f"Validation failed for {commissioner_id}")
                return False
            
            output_path = self.profiles_dir / f"{commissioner_id}.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(converted_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Successfully converted and saved {commissioner_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing {commissioner_id}: {e}")
            return False


def main():
    """Main function to run the conversion process."""
    # Load API key from main.py or environment
    try:
        with open("main.py", "r") as f:
            content = f.read()
            # Extract API key from main.py
            import re
            match = re.search(r'api_key="([^"]+)"', content)
            if match:
                api_key = match.group(1)
            else:
                raise ValueError("API key not found in main.py")
    except Exception as e:
        logger.error(f"Could not load API key from main.py: {e}")
        logger.info("Trying environment variable OPENAI_API_KEY...")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("No API key found. Please set OPENAI_API_KEY environment variable or update main.py")
            return
    
    # Initialize converter
    converter = CommissionerConverter(api_key)
    
    # Convert all commissioners
    logger.info("Starting conversion process...")
    results = converter.convert_all_commissioners()
    
    # Print summary
    print("\n" + "="*50)
    print("CONVERSION SUMMARY")
    print("="*50)
    print(f"Successfully converted: {len(results['success'])} files")
    print(f"Failed conversions: {len(results['failed'])} files") 
    print(f"Skipped (already processed): {len(results['skipped'])} files")
    
    if results["failed"]:
        print(f"\nFailed files:")
        for failed in results["failed"]:
            print(f"  - {failed}")
    
    if results["success"]:
        print(f"\nSuccessfully converted files:")
        for success in results["success"][:5]:  # Show first 5
            print(f"  - {success}")
        if len(results["success"]) > 5:
            print(f"  ... and {len(results['success']) - 5} more")
    
    logger.info("Conversion process completed")


if __name__ == "__main__":
    main()
