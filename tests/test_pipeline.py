import pytest
import asyncio
from xml_pipeline import Pipeline
from lxml import etree

def test_repair_malformed():
    """Test that Pipeline can repair malformed XML."""
    broken = b"<cad-task>broken</cad"
    
    # Pipeline.process() is async, so we need to run it with asyncio
    pipeline = Pipeline()
    repaired, root_tag, version = asyncio.run(pipeline.process(broken))
    
    # Check that the output is well-formed and complete
    assert b"</cad-task>" in repaired or b"cad-task" in repaired
    assert root_tag == "cad-task"
    
    # Verify it's valid XML
    tree = etree.fromstring(repaired)
    assert tree is not None


def test_pipeline_basic():
    """Test basic pipeline functionality with valid XML."""
    valid_xml = b'<cad-task version="1.0">test content</cad-task>'
    
    pipeline = Pipeline()
    canonical, root_tag, version = asyncio.run(pipeline.process(valid_xml))
    
    assert root_tag == "cad-task"
    assert version == "1.0"
    assert b"cad-task" in canonical
    
    # Verify it's valid XML
    tree = etree.fromstring(canonical)
    assert tree is not None
