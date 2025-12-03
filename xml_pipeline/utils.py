# xml_pipeline/utils.py
# Utility functions for XML processing

import hashlib
from typing import Optional
import lxml.etree as ET


def compute_xml_hash(xml: bytes, algorithm: str = "sha256") -> str:
    """
    Compute cryptographic hash of canonical XML.
    
    Args:
        xml: XML bytes (should be canonical)
        algorithm: Hash algorithm (sha256, sha512, etc.)
    
    Returns:
        Hex-encoded hash string
    """
    h = hashlib.new(algorithm)
    h.update(xml)
    return h.hexdigest()


def extract_attribute(xml: bytes, attr_name: str) -> Optional[str]:
    """
    Extract an attribute from XML root element.
    
    Args:
        xml: XML bytes
        attr_name: Name of attribute to extract
    
    Returns:
        Attribute value or None
    """
    try:
        root = ET.fromstring(xml)
        return root.get(attr_name)
    except Exception:
        return None


def extract_text(xml: bytes, xpath: str) -> Optional[str]:
    """
    Extract text content using XPath.
    
    Args:
        xml: XML bytes
        xpath: XPath expression
    
    Returns:
        Text content or None
    """
    try:
        root = ET.fromstring(xml)
        elements = root.xpath(xpath)
        if elements:
            return str(elements[0]) if not isinstance(elements[0], ET._Element) else elements[0].text
        return None
    except Exception:
        return None


def pretty_print_xml(xml: bytes) -> str:
    """
    Pretty print XML for debugging.
    
    Args:
        xml: XML bytes
    
    Returns:
        Pretty-printed XML string
    """
    try:
        root = ET.fromstring(xml)
        return ET.tostring(root, pretty_print=True, encoding="unicode")
    except Exception as e:
        return f"<!-- Failed to parse XML: {e} -->\n{xml.decode('utf-8', errors='replace')}"


def validate_xml_wellformed(xml: bytes) -> tuple[bool, Optional[str]]:
    """
    Check if XML is well-formed.
    
    Args:
        xml: XML bytes to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        ET.fromstring(xml)
        return True, None
    except ET.XMLSyntaxError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error: {e}"
