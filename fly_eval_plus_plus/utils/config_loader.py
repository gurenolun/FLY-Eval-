"""
Configuration Loader

Loads configuration from JSON files and Python modules.
"""

import json
import os
import sys
from typing import Dict, Any, Optional
from pathlib import Path


def load_eval_config(config_path: str) -> Dict[str, Any]:
    """
    Load EvalConfig from JSON file
    
    Args:
        config_path: Path to config JSON file
    
    Returns:
        Configuration dictionary
    """
    # TODO: Implement config loading from JSON
    # For now, return empty dict
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def load_field_limits() -> Dict[str, tuple]:
    """
    Load FIELD_LIMITS from validity_standard.py
    
    Returns:
        Dictionary mapping field names to (lower_bound, upper_bound) tuples
    """
    # Try to import from validity_standard.py
    try:
        # Add parent directories to path
        parent_dir = Path(__file__).parent.parent.parent.parent
        sys.path.insert(0, str(parent_dir))
        
        from validity_standard import FIELD_LIMITS
        return FIELD_LIMITS
    except ImportError:
        # Fallback: return empty dict
        return {}


def load_jump_thresholds() -> Dict[str, float]:
    """
    Load JUMP_THRESHOLDS from validity_change_standard.py
    
    Returns:
        Dictionary mapping field names to mutation thresholds
    """
    # Try to import from validity_change_standard.py
    try:
        # Add parent directories to path
        parent_dir = Path(__file__).parent.parent.parent.parent
        sys.path.insert(0, str(parent_dir))
        
        from validity_change_standard import JUMP_THRESHOLDS
        return JUMP_THRESHOLDS
    except ImportError:
        # Fallback: return empty dict
        return {}

