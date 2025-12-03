# xml_pipeline/schema_catalog.py
# Schema catalog for managing multiple XSD schemas

from pathlib import Path
from typing import Dict, Optional, List
import lxml.etree as ET


class SchemaCatalog:
    """
    Central registry for XML schemas.
    
    Loads and manages XSD schemas for validation.
    """
    
    def __init__(self, schema_dirs: Optional[List[str]] = None):
        """
        Initialize schema catalog.
        
        Args:
            schema_dirs: List of directories containing .xsd files
        """
        self.schemas: Dict[str, ET.XMLSchema] = {}
        self.schema_dirs = schema_dirs or []
        
        # Load default schemas
        default_schema_dir = Path(__file__).parent / "schemas"
        if default_schema_dir.exists():
            self.schema_dirs.insert(0, str(default_schema_dir))
        
        self._load_all_schemas()
    
    def _load_all_schemas(self) -> None:
        """Load all XSD files from configured directories."""
        for schema_dir in self.schema_dirs:
            path = Path(schema_dir)
            if not path.exists():
                continue
            
            for xsd_file in path.rglob("*.xsd"):
                self._load_schema(xsd_file)
    
    def _load_schema(self, xsd_path: Path) -> None:
        """
        Load a single XSD schema file.
        
        Args:
            xsd_path: Path to XSD file
        """
        try:
            schema_doc = ET.parse(str(xsd_path))
            schema = ET.XMLSchema(schema_doc)
            
            # Use targetNamespace as key, fallback to filename
            root = schema_doc.getroot()
            namespace = root.get("targetNamespace")
            key = namespace if namespace else xsd_path.stem
            
            self.schemas[key] = schema
        except Exception as e:
            # Don't fail on individual schema errors
            pass
    
    def get_schema(self, namespace_or_name: str) -> Optional[ET.XMLSchema]:
        """
        Get schema by namespace or name.
        
        Args:
            namespace_or_name: Schema namespace URI or file stem
        
        Returns:
            XMLSchema object or None
        """
        return self.schemas.get(namespace_or_name)
    
    def validate(self, xml: bytes, schema_key: Optional[str] = None) -> tuple[bool, Optional[str]]:
        """
        Validate XML against a schema.
        
        Args:
            xml: XML bytes to validate
            schema_key: Specific schema to use (namespace or name)
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            root = ET.fromstring(xml)
            
            if schema_key:
                schema = self.get_schema(schema_key)
                if not schema:
                    return False, f"Schema not found: {schema_key}"
                
                if schema.validate(root):
                    return True, None
                return False, str(schema.error_log)
            
            # Try all schemas if none specified
            for schema in self.schemas.values():
                if schema.validate(root):
                    return True, None
            
            return False, "No matching schema found"
        
        except Exception as e:
            return False, f"Validation error: {e}"
    
    def list_schemas(self) -> List[str]:
        """Get list of loaded schema keys."""
        return list(self.schemas.keys())
