#!/usr/bin/env python3
"""Test script to validate the Mermaid error detection capabilities of the Validator Agent."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger
from smolagents import ToolCallingAgent
from toolkits.validator_toolkit import build_validator_tools
from utils.llm_factory import create_model
from prompts import prompts


def test_validator():
    """Run the validator against a file with intentionally broken Mermaid."""
    
    test_dir = Path("data/test_validation")
    test_file = "broken_mermaid.md"
    
    logger.info(f"🧪 Testing Validator Agent on {test_file}")
    
    # Read original content for comparison
    original_content = (test_dir / test_file).read_text()
    logger.info(f"📝 Original file has {len(original_content)} chars")
    
    # Build validator (use flash model for cost efficiency)
    model = create_model(role="sub_agent") 
    tools = build_validator_tools(target_root=test_dir)
    
    validator = ToolCallingAgent(
        name="markdown_validator",
        description="Validates and fixes markdown formatting.",
        tools=tools,
        model=model,
        instructions=prompts.VALIDATOR_AGENT_PROMPT,
    )
    
    # Run validation
    try:
        result = validator.run(f"Validate and fix formatting issues in '{test_file}'.")
        logger.info(f"✅ Validator completed. Result: {result}")
    except Exception as e:
        logger.error(f"❌ Validator failed: {e}")
        return
    
    # Check if file was modified
    new_content = (test_dir / test_file).read_text()
    
    if new_content != original_content:
        logger.success("🎉 Validator MODIFIED the file!")
        logger.info(f"📊 New file has {len(new_content)} chars (was {len(original_content)})")
        
        # Show diff summary
        original_lines = original_content.split('\n')
        new_lines = new_content.split('\n')
        logger.info(f"📏 Lines: {len(original_lines)} -> {len(new_lines)}")
        
        # Check if Mermaid was fixed
        if '["' in new_content and '["' not in original_content:
            logger.success("✅ Mermaid labels appear to be quoted now!")
        else:
            logger.warning("⚠️ Mermaid labels may not have been quoted.")
            
    else:
        logger.warning("⚠️ Validator DID NOT MODIFY the file - it either passed validation or failed to detect errors!")


if __name__ == "__main__":
    test_validator()
