import json
from typing import Type, Dict, Any, TypeVar, Optional
from pydantic import BaseModel
from app.core.logger import logger

T = TypeVar("T", bound=BaseModel)

class AIResponseParsingError(Exception):
    """
    Custom exception raised when response parsing or schema validation fails permanently.
    """
    pass

class ResponseParser:
    """
    Cleans raw LLM outputs, repairs missing optional properties, and validates structured data into Pydantic models.
    """
    @staticmethod
    def clean_raw_output(text: str) -> str:
        """
        Strips markdown JSON code fences (e.g., ```json ... ```) from the LLM output.
        """
        cleaned = text.strip()
        
        # Strip leading markdown tags
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
            
        # Strip trailing markdown tags
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
            
        return cleaned.strip()

    @staticmethod
    def repair_fields(data: Dict[str, Any], schema_cls: Type[T]) -> Dict[str, Any]:
        """
        Inspects the expected schema fields and repairs missing or null values 
        with default lists, strings, dicts, or field default values where possible.
        """
        repaired = dict(data)
        
        # Pydantic v2 exposes fields via model_fields
        for field_name, field_info in schema_cls.model_fields.items():
            if field_name not in repaired or repaired[field_name] is None:
                annotation = field_info.annotation
                
                # Check for container types (List, Dict) or basic types
                origin = getattr(annotation, "__origin__", None)
                
                if origin is list:
                    repaired[field_name] = []
                elif origin is dict:
                    repaired[field_name] = {}
                elif annotation is str:
                    repaired[field_name] = ""
                elif field_info.default is not None and str(field_info.default) != "PydanticUndefined":
                    repaired[field_name] = field_info.default
                elif field_info.default_factory is not None:
                    repaired[field_name] = field_info.default_factory()
                    
        return repaired

    def parse_and_validate(self, raw_text: str, schema_cls: Type[T]) -> T:
        """
        Cleans the raw text, parses JSON, repairs missing fields, and validates against the schema class.
        Raises AIResponseParsingError on failure.
        """
        # 1. Clean markdown formatting
        cleaned_text = self.clean_raw_output(raw_text)
        
        # 2. Parse JSON structure
        try:
            parsed_data = json.loads(cleaned_text)
        except Exception as err:
            try:
                from app.utils.json_repair import parse_repaired_json
                parsed_data = parse_repaired_json(cleaned_text)
            except Exception as repair_err:
                logger.error(
                    f"ResponseParser: Failed to parse clean string as JSON. "
                    f"Error: {err}. Repair error: {repair_err}. Raw snippet: '{cleaned_text[:200]}'"
                )
                raise AIResponseParsingError(f"Raw output is not valid JSON: {err}")

        # 3. Repair missing optional structures
        if isinstance(parsed_data, dict):
            try:
                parsed_data = self.repair_fields(parsed_data, schema_cls)
            except Exception as err:
                logger.warning(f"ResponseParser: Field repair encountered an error: {err}")
        else:
            raise AIResponseParsingError("Parsed JSON is not a dictionary payload")

        # 4. Perform schema validation
        try:
            return schema_cls.model_validate(parsed_data)
        except Exception as err:
            logger.error(
                f"ResponseParser: Schema validation failed for model {schema_cls.__name__}. "
                f"Error: {err}. Repaired payload keys: {list(parsed_data.keys())}"
            )
            raise AIResponseParsingError(f"Response does not conform to validation schema: {err}")

response_parser = ResponseParser()
