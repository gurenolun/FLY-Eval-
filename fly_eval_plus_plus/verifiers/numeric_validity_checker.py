"""
Numeric Validity Checker

Checks for NaN, Inf, type validity, and missing values.
Based on comprehensive_flight_evaluation_no_norm.py
"""

import numpy as np
from typing import List, Dict, Any, Optional
from ..core.verifier_base import Verifier
from ..core.data_structures import EvidenceAtom, Severity, Scope


class NumericValidityChecker(Verifier):
    """
    Numeric validity checker
    
    Checks:
    - NaN values
    - Inf values
    - Type validity
    - Missing values
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize numeric validity checker
        
        Args:
            config: Configuration dict with 'check_nan', 'check_inf', 'check_type', 'check_missing'
        """
        super().__init__(config, verifier_id="NUMERIC_VALIDITY")
        self.check_nan = config.get('check_nan', True)
        self.check_inf = config.get('check_inf', True)
        self.check_type = config.get('check_type', True)
        self.check_missing = config.get('check_missing', True)
    
    def is_valid_numeric_value(self, value):
        """
        Check if value is a valid numeric value
        
        Copied from comprehensive_flight_evaluation_no_norm.py
        """
        if value is None:
            return False
        if isinstance(value, str):
            value = value.strip()
            if value == "" or value.lower() in ['null', 'none', 'nan', 'n/a', 'undefined']:
                return False
        try:
            float_val = float(value)
            return not (np.isnan(float_val) or np.isinf(float_val))
        except (ValueError, TypeError):
            return False
    
    def verify(self, sample: Any, model_output: Any, context: Dict[str, Any]) -> List[EvidenceAtom]:
        """
        Verify numeric validity
        
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
                if self.check_missing:
                    evidence.append(EvidenceAtom(
                        id=self._generate_evidence_id(),
                        type="numeric_validity",
                        field=field,
                        pass_=False,
                        severity=Severity.CRITICAL,
                        scope=Scope.FIELD,
                        message=f"Field {field} is missing",
                        meta={"checker": "NumericValidityChecker", "check_type": "missing"}
                    ))
                continue
            
            value = json_data[field]
            
            # Handle M3 task array values
            if isinstance(value, list):
                for i, v in enumerate(value):
                    if not self.is_valid_numeric_value(v):
                        evidence.append(EvidenceAtom(
                            id=self._generate_evidence_id(),
                            type="numeric_validity",
                            field=f"{field}[{i}]",
                            pass_=False,
                            severity=Severity.CRITICAL,
                            scope=Scope.FIELD,
                            message=f"Field {field}[{i}] has invalid numeric value: {v}",
                            meta={"checker": "NumericValidityChecker", "check_type": "invalid_value", "value": str(v)}
                        ))
                    else:
                        # ✅ 修复：即使通过也要记录evidence atom
                        evidence.append(EvidenceAtom(
                            id=self._generate_evidence_id(),
                            type="numeric_validity",
                            field=f"{field}[{i}]",
                            pass_=True,
                            severity=Severity.INFO,
                            scope=Scope.FIELD,
                            message=f"Field {field}[{i}] has valid numeric value",
                            meta={"checker": "NumericValidityChecker", "check_type": "valid_value", "value": str(v)}
                        ))
            else:
                # Single value
                if not self.is_valid_numeric_value(value):
                    evidence.append(EvidenceAtom(
                        id=self._generate_evidence_id(),
                        type="numeric_validity",
                        field=field,
                        pass_=False,
                        severity=Severity.CRITICAL,
                        scope=Scope.FIELD,
                        message=f"Field {field} has invalid numeric value: {value}",
                        meta={"checker": "NumericValidityChecker", "check_type": "invalid_value", "value": str(value)}
                    ))
                else:
                    # ✅ 修复：即使通过也要记录evidence atom
                    evidence.append(EvidenceAtom(
                        id=self._generate_evidence_id(),
                        type="numeric_validity",
                        field=field,
                        pass_=True,
                        severity=Severity.INFO,
                        scope=Scope.FIELD,
                        message=f"Field {field} has valid numeric value",
                        meta={"checker": "NumericValidityChecker", "check_type": "valid_value", "value": str(value)}
                    ))
        
        return evidence
    
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities"""
        return ["numeric_validity"]

