import json
import os
import logging
import argparse
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
        logging.FileHandler('conversion.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CommissionerConverter:
    def __init__(self, api_key: str, input_mode: str = "markdown"):
        """Initialize the converter with OpenAI client and schema.
        
        Args:
            api_key: OpenAI API key
            input_mode: "markdown" for original .md files (default) or "parsed" for pre-parsed JSON
        """
        self.client = OpenAI(api_key=api_key)
        self.schema = self._load_schema()
        self.input_mode = input_mode
        
        # Set up directories based on input mode
        if input_mode == "markdown":
            self.input_dir = Path("notion/Commissioning Assistant Profiles 2724b6c9c50780d6aa98f69ccc91f0b3")
        else:  # parsed mode
            self.input_dir = Path("parsed")
            
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
        """Validate the converted data against the original schema."""
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
    
    def _validate_converted_data_structured(self, data: Dict[str, Any]) -> bool:
        """Validate the converted data against the structured schema."""
        try:
            validate(instance=data, schema=self.structured_schema)
            return True
        except jsonschema.ValidationError as e:
            logger.error(f"Structured schema validation failed: {e.message}")
            logger.error(f"Failed at path: {' -> '.join(str(p) for p in e.absolute_path)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected validation error: {e}")
            return False
    
    def _load_markdown_file(self, file_path: Path) -> Optional[str]:
        """Load content from a markdown file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading markdown file {file_path}: {e}")
            return None
    
    def _find_markdown_files(self) -> list[Path]:
        """Find all markdown files in the notion directory structure using the same logic as parse_commissioners.py."""
        md_files = []
        
        if not self.input_dir.exists():
            return md_files
        
        # Look for all .md files in country/organization subdirectories (same logic as parse_commissioners.py)
        for root, dirs, files in os.walk(self.input_dir):
            # Only process files in subdirectories that have the ID pattern
            if any(folder_id in str(root) for folder_id in ['2724b6c9c5078', '2734b6c9c5078']):
                for file in files:
                    if file.endswith('.md'):
                        # Skip the summary files (those in the root directory)
                        file_path = Path(root) / file
                        # Check if this is a profile file (in a subfolder, not the summary)
                        if file_path.parent.name != self.input_dir.name:
                            md_files.append(file_path)
        
        return md_files
    
    def _convert_single_commissioner(self, input_data: Dict[str, Any] | str, source_file: str = "") -> Optional[Dict[str, Any]]:
        """Convert a single commissioner's data using OpenAI structured outputs.
        
        Args:
            input_data: Either parsed JSON data (dict) or raw markdown content (str)
            source_file: Source file path for reference
        """
        try:
            # Prepare different prompts based on input type
            if isinstance(input_data, str):
                # Markdown input mode
                system_prompt = """You are an expert data conversion specialist. Convert the provided raw markdown commissioner profile to match the exact schema format provided.

Key conversion guidelines:
1. Extract all relevant information from the markdown content
2. Generate a unique ID based on the commissioner name and organization
3. Categorize thematic priorities into the predefined themes enum values
4. Classify target audience into the audience_segments enum values  
5. Convert format specifications to the formats enum values
6. Extract budget ranges and convert to min/max USD values where possible
7. Determine platform_type, commissioner_type, geographic_scope based on the content
8. Set appropriate boolean flags for diversity_focus, sustainability_focus, festival_potential_required
9. Convert technical requirements to delivery_requirements enum values
10. Determine appropriate production_values level
11. Set commissioning_cycles and co_production_openness based on context
12. Extract and standardize languages
13. Parse all structured information while preserving original text in appropriate fields

Ensure all required fields are populated and all enum values match exactly."""

                user_prompt = f"Convert this raw markdown commissioner profile to the schema format:\n\nSource file: {source_file}\n\nContent:\n{input_data}"
            else:
                # Parsed JSON input mode (original functionality)
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

                user_prompt = f"Convert this commissioner data to the schema format:\n\n{json.dumps(input_data, indent=2)}"
            
            # Make the API call with structured output
            response = self.client.responses.create(
                model="gpt-4o-mini",  # Use gpt-4o-mini as it's available
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
                # Handle different response structures
                output_item = response.output[0]
                if hasattr(output_item, 'content') and output_item.content:
                    content = output_item.content[0]
                    if hasattr(content, 'type') and content.type == "refusal":
                        logger.error(f"API refused to process: {content.refusal}")
                        return None
            
            # Parse the response - use output_text directly
            converted_data = json.loads(response.output_text)
            
            # Add timestamps and source file
            from datetime import timezone
            now = datetime.now(timezone.utc).isoformat()
            converted_data["created_at"] = now
            converted_data["updated_at"] = now
            
            # Add source file if provided
            if source_file:
                converted_data["source_file"] = source_file
            
            return converted_data
            
        except Exception as e:
            logger.error(f"Error converting commissioner data: {e}")
            return None
    
    def convert_all_commissioners(self, force_reprocess: bool = False) -> Dict[str, str]:
        """Convert all commissioners based on the selected input mode."""
        results = {"success": [], "failed": [], "skipped": []}
        
        # Get already processed files
        processed_files = set() if force_reprocess else self._get_processed_files()
        
        if self.input_mode == "markdown":
            # Get all markdown files
            input_files = self._find_markdown_files()
            if not input_files:
                logger.warning("No markdown files found in the notion directory")
                return results
            logger.info(f"Found {len(input_files)} markdown files to process")
        else:
            # Get all parsed JSON files (original functionality)
            input_files = list(self.input_dir.glob("*.json"))
            if not input_files:
                logger.warning("No parsed files found in the parsed directory")
                return results
            logger.info(f"Found {len(input_files)} parsed files to process")
        
        logger.info(f"Already processed: {len(processed_files)} files")
        
        for file_path in input_files:
            # Generate commissioner ID from file path
            if self.input_mode == "markdown":
                # For markdown files, use the filename without extension as ID
                commissioner_id = file_path.stem
            else:
                # For JSON files, use existing logic
                commissioner_id = file_path.stem
            
            # Skip if already processed
            if commissioner_id in processed_files:
                logger.info(f"Skipping {commissioner_id} - already processed")
                results["skipped"].append(commissioner_id)
                continue
            
            logger.info(f"Processing {commissioner_id}...")
            
            try:
                if self.input_mode == "markdown":
                    # Load markdown content
                    input_data = self._load_markdown_file(file_path)
                    if input_data is None:
                        logger.error(f"Failed to load markdown file {commissioner_id}")
                        results["failed"].append(commissioner_id)
                        continue
                    
                    # Convert using OpenAI with source file path
                    source_file = str(file_path).replace(str(Path.cwd()) + os.sep, "")
                    converted_data = self._convert_single_commissioner(input_data, source_file)
                else:
                    # Load parsed JSON data (original functionality)
                    with open(file_path, "r", encoding="utf-8") as f:
                        input_data = json.load(f)
                    
                    # Convert using OpenAI
                    converted_data = self._convert_single_commissioner(input_data)
                
                if converted_data is None:
                    logger.error(f"Failed to convert {commissioner_id}")
                    results["failed"].append(commissioner_id)
                    continue
                
                # Validate converted data using the structured schema
                if not self._validate_converted_data_structured(converted_data):
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
        file_path = self.input_dir / filename
        if not file_path.exists():
            logger.error(f"File not found: {filename}")
            return False
        
        commissioner_id = file_path.stem
        logger.info(f"Converting single file: {commissioner_id}")
        
        try:
            if self.input_mode == "markdown":
                # Load markdown content
                input_data = self._load_markdown_file(file_path)
                if input_data is None:
                    logger.error(f"Failed to load markdown file {commissioner_id}")
                    return False
                
                # Convert using OpenAI with source file path
                source_file = str(file_path).replace(str(Path.cwd()) + os.sep, "")
                converted_data = self._convert_single_commissioner(input_data, source_file)
            else:
                # Load parsed JSON data (original functionality)
                with open(file_path, "r", encoding="utf-8") as f:
                    input_data = json.load(f)
                
                # Convert using OpenAI
                converted_data = self._convert_single_commissioner(input_data)
            
            if converted_data is None:
                logger.error(f"Failed to convert {commissioner_id}")
                return False
            
            if not self._validate_converted_data_structured(converted_data):
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
    # Set up command line arguments
    parser = argparse.ArgumentParser(description="Convert commissioner profiles to structured JSON format")
    parser.add_argument(
        "--input-mode", 
        choices=["markdown", "parsed"], 
        default="markdown",
        help="Input mode: 'markdown' for original .md files (default) or 'parsed' for pre-parsed JSON files"
    )
    parser.add_argument(
        "--force-reprocess", 
        action="store_true",
        help="Force reprocessing of all files, even if already processed"
    )
    parser.add_argument(
        "--single-file",
        type=str,
        help="Convert only a single file (specify filename)"
    )
    
    args = parser.parse_args()
    
    # Hardcoded API key
    api_key = "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"
    
    # Initialize converter with selected input mode
    converter = CommissionerConverter(api_key, input_mode=args.input_mode)
    
    print(f"Using input mode: {args.input_mode}")
    if args.input_mode == "markdown":
        print("Processing original .md files from notion folder structure")
    else:
        print("Processing pre-parsed JSON files from parsed folder")
    
    if args.single_file:
        # Convert single file
        logger.info(f"Converting single file: {args.single_file}")
        success = converter.convert_single_file(args.single_file)
        if success:
            print(f"✅ Successfully converted {args.single_file}")
        else:
            print(f"❌ Failed to convert {args.single_file}")
    else:
        # Convert all commissioners
        logger.info("Starting conversion process...")
        results = converter.convert_all_commissioners(force_reprocess=args.force_reprocess)
        
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
