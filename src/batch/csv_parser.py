"""
CSV parser for batch experiment creation.

This module handles parsing CSV files containing experiment prompts and configurations,
validating the format, and converting them into structured data for batch creation.
"""

import csv
import io
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ParsedExperiment:
    """Single experiment parsed from CSV."""
    prompt: str
    description: Optional[str] = None
    max_turns: int = 10
    row_number: int = 0  # For error reporting


@dataclass
class ParseResult:
    """Result of parsing a CSV file."""
    success: bool
    experiments: List[ParsedExperiment]
    errors: List[str]
    total_rows: int


def parse_csv(file_content: str, has_header: bool = True) -> ParseResult:
    """
    Parse CSV file content into experiments.
    
    Expected CSV format:
    prompt,description,max_turns
    "What is AI?","Basic AI question",10
    "Explain robots","Robotics explanation",15
    
    Or minimal format (just prompts):
    What is AI?
    Explain robots
    
    Args:
        file_content: String content of CSV file
        has_header: Whether first row is a header
        
    Returns:
        ParseResult with experiments or errors
    """
    experiments = []
    errors = []
    
    try:
        # Parse CSV
        reader = csv.DictReader(io.StringIO(file_content)) if has_header else None
        
        if not has_header:
            # Treat each line as a prompt
            reader = csv.reader(io.StringIO(file_content))
        
        row_num = 1 if has_header else 0
        
        for row in reader:
            row_num += 1
            
            try:
                if has_header:
                    # DictReader - expect columns
                    prompt = row.get('prompt', '').strip()
                    description = row.get('description', '').strip() or None
                    max_turns_str = row.get('max_turns', '10').strip()
                    
                    if not prompt:
                        errors.append(f"Row {row_num}: Missing prompt")
                        continue
                    
                    try:
                        max_turns = int(max_turns_str) if max_turns_str else 10
                        if max_turns < 1 or max_turns > 100:
                            errors.append(f"Row {row_num}: max_turns must be between 1-100")
                            max_turns = 10
                    except ValueError:
                        errors.append(f"Row {row_num}: Invalid max_turns '{max_turns_str}', using 10")
                        max_turns = 10
                else:
                    # Simple list - first column is prompt
                    if not row or not row[0]:
                        continue  # Skip empty lines
                    
                    prompt = row[0].strip()
                    description = row[1].strip() if len(row) > 1 and row[1] else None
                    
                    try:
                        max_turns = int(row[2]) if len(row) > 2 and row[2] else 10
                    except (ValueError, IndexError):
                        max_turns = 10
                
                experiments.append(ParsedExperiment(
                    prompt=prompt,
                    description=description,
                    max_turns=max_turns,
                    row_number=row_num
                ))
                
            except Exception as e:
                errors.append(f"Row {row_num}: Error parsing - {str(e)}")
        
        # Validation
        if not experiments:
            errors.append("No valid experiments found in CSV")
            return ParseResult(success=False, experiments=[], errors=errors, total_rows=row_num)
        
        if len(experiments) > 100:
            errors.append(f"Too many experiments ({len(experiments)}). Maximum is 100 per batch.")
            return ParseResult(success=False, experiments=[], errors=errors, total_rows=row_num)
        
        # Success - even if there were some row errors
        return ParseResult(
            success=True,
            experiments=experiments,
            errors=errors,
            total_rows=row_num
        )
        
    except Exception as e:
        return ParseResult(
            success=False,
            experiments=[],
            errors=[f"CSV parsing failed: {str(e)}"],
            total_rows=0
        )


def validate_csv_format(file_content: str) -> Dict[str, any]:
    """
    Quick validation of CSV format without full parsing.
    
    Returns:
        Dictionary with 'valid' boolean and 'message' string
    """
    if not file_content or not file_content.strip():
        return {"valid": False, "message": "File is empty"}
    
    lines = file_content.strip().split('\n')
    
    if len(lines) < 1:
        return {"valid": False, "message": "File has no content"}
    
    if len(lines) > 101:  # 100 + header
        return {"valid": False, "message": f"Too many rows ({len(lines)}). Maximum is 100 experiments."}
    
    # Check for basic CSV structure
    first_line = lines[0]
    if ',' not in first_line and ';' not in first_line:
        # Might be single-column format - that's ok
        pass
    
    return {"valid": True, "message": "Format looks valid"}
