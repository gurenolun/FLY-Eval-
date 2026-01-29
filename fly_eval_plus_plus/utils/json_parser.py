"""
JSON Parser Utilities

Functions for extracting JSON from model responses and checking API errors.
Based on comprehensive_flight_evaluation_no_norm.py
"""

import json
import re
from typing import Optional, Dict, Any


def is_api_error(response: str) -> bool:
    """
    Check if response is an API error
    
    Copied from comprehensive_flight_evaluation_no_norm.py
    """
    if not isinstance(response, str):
        return False
    
    response_lower = response.lower()
    error_keywords = [
        'api error', 'api request failed', 'timeout', 
        'http error', 'status code',
        'forbidden', 'access denied', 'unauthorized', 'time out',
        'internal server error', 'rate limit exceeded', 
        'connection error', 'network error', 'failed to connect',
        'service unavailable', 'bad request', 'invalid request',
        'authentication failed', 'quota exceeded'
    ]
    
    return any(keyword in response_lower for keyword in error_keywords)


def extract_json_from_response(response: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON content from response
    
    Copied from comprehensive_flight_evaluation_no_norm.py
    """
    if isinstance(response, dict):
        return response
    
    if not isinstance(response, str):
        return None
    
    # Try direct parsing
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    # Try extracting from code blocks
    json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    matches = re.findall(json_pattern, response, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    # Try finding JSON object
    json_pattern2 = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_pattern2, response, re.DOTALL)
    
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    return None

