"""
Tests for CSV parser functionality.

Tests cover valid CSV formats, error handling, and edge cases.
"""

import pytest
from src.batch import parse_csv, validate_csv_format


def test_parse_csv_basic_format():
    """Test parsing CSV with header row."""
    csv_content = """prompt,description,max_turns
What is AI?,Basic question,10
Explain robots,Robotics topic,15
Tell me about ML,Machine learning,20"""
    
    result = parse_csv(csv_content, has_header=True)
    
    assert result.success is True
    assert len(result.experiments) == 3
    assert result.experiments[0].prompt == "What is AI?"
    assert result.experiments[0].description == "Basic question"
    assert result.experiments[0].max_turns == 10
    assert result.experiments[2].max_turns == 20


def test_parse_csv_prompts_only():
    """Test parsing CSV with just prompts (no header)."""
    csv_content = """What is AI?
Explain robots
Tell me about machine learning"""
    
    result = parse_csv(csv_content, has_header=False)
    
    assert result.success is True
    assert len(result.experiments) == 3
    assert result.experiments[0].prompt == "What is AI?"
    assert result.experiments[0].max_turns == 10  # Default value
    assert result.experiments[1].prompt == "Explain robots"


def test_parse_csv_with_quotes():
    """Test parsing CSV with quoted fields containing commas."""
    csv_content = '''prompt,description,max_turns
"What is AI, exactly?","Question with, commas",10
"Explain robots, please",Another one,15'''
    
    result = parse_csv(csv_content, has_header=True)
    
    assert result.success is True
    assert len(result.experiments) == 2
    assert result.experiments[0].prompt == "What is AI, exactly?"
    assert result.experiments[0].description == "Question with, commas"


def test_parse_csv_missing_columns():
    """Test parsing CSV with optional missing columns."""
    csv_content = """prompt
What is AI?
Explain robots"""
    
    result = parse_csv(csv_content, has_header=True)
    
    assert result.success is True
    assert len(result.experiments) == 2
    assert result.experiments[0].description is None
    assert result.experiments[0].max_turns == 10  # Default


def test_parse_csv_invalid_max_turns():
    """Test parsing CSV with invalid max_turns values."""
    csv_content = """prompt,description,max_turns
Test prompt,Test,invalid
Another prompt,Test,150"""
    
    result = parse_csv(csv_content, has_header=True)
    
    assert result.success is True  # Parsing succeeds with warnings
    assert len(result.experiments) == 2
    assert result.experiments[0].max_turns == 10  # Defaults to 10 if invalid
    assert len(result.errors) > 0  # Should have error messages


def test_parse_csv_empty_file():
    """Test parsing empty CSV file."""
    result = parse_csv("", has_header=True)
    
    assert result.success is False
    assert len(result.experiments) == 0
    assert len(result.errors) > 0


def test_parse_csv_too_many_rows():
    """Test parsing CSV with more than 100 experiments."""
    # Create CSV with 101 experiments
    rows = ["prompt"] + [f"Test prompt {i}" for i in range(101)]
    csv_content = "\n".join(rows)
    
    result = parse_csv(csv_content, has_header=True)
    
    assert result.success is False
    assert "Too many experiments" in result.errors[0]


def test_validate_csv_format_valid():
    """Test CSV format validation with valid file."""
    csv_content = """prompt,description
Test 1,Description 1
Test 2,Description 2"""
    
    validation = validate_csv_format(csv_content)
    
    assert validation["valid"] is True


def test_validate_csv_format_empty():
    """Test CSV format validation with empty file."""
    validation = validate_csv_format("")
    
    assert validation["valid"] is False
    assert "empty" in validation["message"].lower()


def test_validate_csv_format_too_many_rows():
    """Test CSV format validation with too many rows."""
    csv_content = "\n".join([f"Prompt {i}" for i in range(102)])
    
    validation = validate_csv_format(csv_content)
    
    assert validation["valid"] is False
    assert "Too many" in validation["message"]


def test_parse_csv_skip_empty_lines():
    """Test that empty lines are skipped."""
    csv_content = """What is AI?

Explain robots

Tell me about ML"""
    
    result = parse_csv(csv_content, has_header=False)
    
    assert result.success is True
    assert len(result.experiments) == 3  # Empty lines skipped
