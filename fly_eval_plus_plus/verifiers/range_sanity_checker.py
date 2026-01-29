"""
Range Sanity Checker

Checks if field values are within valid ranges.
Based on comprehensive_flight_evaluation_no_norm.py check_range_validity
"""

from typing import List, Dict, Any, Optional, Tuple
from ..core.verifier_base import Verifier
from ..core.data_structures import EvidenceAtom, Severity, Scope


class RangeSanityChecker(Verifier):
    """
    Range sanity checker
    
    Checks if field values are within valid domain/unit/range limits.
    Uses FIELD_LIMITS from validity_standard.py
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize range sanity checker
        
        Args:
            config: Configuration dict with 'field_limits' dict
        """
        super().__init__(config, verifier_id="RANGE_SANITY")
        self.field_limits = config.get('field_limits', {})
        self.unit_validation = config.get('unit_validation', True)
    
    def check_range_validity(self, field: str, value: Any) -> Tuple[bool, Optional[str]]:
        """
        Check if field value is within valid range
        
        Copied from comprehensive_flight_evaluation_no_norm.py
        """
        if field not in self.field_limits:
            return True, None
        
        lower_bound, upper_bound = self.field_limits[field]
        
        # Handle empty values
        if value is None or value == "":
            return True, None  # Empty values handled by other checks
        
        # Handle M3 task array values
        if isinstance(value, list):
            for i, v in enumerate(value):
                if v is None or v == "":
                    continue  # Skip empty values
                try:
                    num_val = float(v)
                    if num_val < lower_bound or num_val > upper_bound:
                        return False, f"{field}[{i}] out of range: {num_val} not in [{lower_bound}, {upper_bound}]"
                except (ValueError, TypeError):
                    return False, f"{field}[{i}] cannot be converted to numeric"
            return True, None
        
        # Handle single value
        try:
            num_val = float(value)
            if num_val < lower_bound or num_val > upper_bound:
                return False, f"{field} out of range: {num_val} not in [{lower_bound}, {upper_bound}]"
            return True, None
        except (ValueError, TypeError):
            return False, f"{field} cannot be converted to numeric"
    
    def verify(self, sample: Any, model_output: Any, context: Dict[str, Any]) -> List[EvidenceAtom]:
        """
        Verify range sanity
        
        Args:
            sample: Sample data
            model_output: ModelOutput object
            context: Context dict with 'json_data' (parsed JSON)
        
        Returns:
            List of EvidenceAtom objects
        """
        evidence = []
        json_data = context.get('json_data')
        required_fields = context.get('required_fields', [])
        
        if json_data is None:
            return evidence
        
        for field in required_fields:
            if field not in json_data:
                continue  # Missing fields handled by NumericValidityChecker
            
            value = json_data[field]
            is_valid, error_msg = self.check_range_validity(field, value)
            
            if not is_valid:
                # Determine severity based on how far out of range
                severity = Severity.CRITICAL
                if error_msg:
                    # Calculate deviation for severity assessment
                    if field in self.field_limits:
                        lower, upper = self.field_limits[field]
                        try:
                            if isinstance(value, list):
                                # For arrays, check first value
                                num_val = float(value[0]) if value else 0
                            else:
                                num_val = float(value)
                            
                            # Calculate deviation percentage
                            if num_val < lower:
                                deviation = abs(num_val - lower) / (upper - lower) if (upper - lower) > 0 else 1.0
                            elif num_val > upper:
                                deviation = abs(num_val - upper) / (upper - lower) if (upper - lower) > 0 else 1.0
                            else:
                                deviation = 0.0
                            
                            # Adjust severity based on deviation
                            if deviation > 0.5:
                                severity = Severity.CRITICAL
                            elif deviation > 0.2:
                                severity = Severity.WARNING
                            else:
                                severity = Severity.WARNING
                        except (ValueError, TypeError):
                            pass
                
                evidence.append(EvidenceAtom(
                    id=self._generate_evidence_id(),
                    type="range_sanity",
                    field=field,
                    pass_=False,
                    severity=severity,
                    scope=Scope.FIELD,
                    message=error_msg or f"Field {field} out of valid range",
                    meta={"checker": "RangeSanityChecker", "field_limits": self.field_limits.get(field), "deviation": deviation if 'deviation' in locals() else None}
                ))
            else:
                # ✅ 修复：即使通过也要记录evidence atom
                evidence.append(EvidenceAtom(
                    id=self._generate_evidence_id(),
                    type="range_sanity",
                    field=field,
                    pass_=True,
                    severity=Severity.INFO,
                    scope=Scope.FIELD,
                    message=f"Field {field} within valid range",
                    meta={"checker": "RangeSanityChecker", "field_limits": self.field_limits.get(field)}
                ))
        
        return evidence
    
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities"""
        return ["range_sanity"]

