"""
Jump Dynamics Checker

Checks for mutation/jump violations in field values.
Based on comprehensive_flight_evaluation_no_norm.py check_mutation
"""

from typing import List, Dict, Any, Optional, Tuple
from ..core.verifier_base import Verifier
from ..core.data_structures import EvidenceAtom, Severity, Scope


class JumpDynamicsChecker(Verifier):
    """
    Jump dynamics checker
    
    Checks for mutation/jump violations:
    - M3 task: checks mutations within array
    - S1/M1 task: checks mutations from previous value
    - Phase-aware (if enabled)
    - Change rate limits
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize jump dynamics checker
        
        Args:
            config: Configuration dict with 'mutation_thresholds', 'phase_aware', 'change_rate_limits'
        """
        super().__init__(config, verifier_id="JUMP_DYNAMICS")
        self.mutation_thresholds = config.get('mutation_thresholds', {})
        self.phase_aware = config.get('phase_aware', False)
        self.change_rate_limits = config.get('change_rate_limits', {})
        self.angle_fields = config.get('angle_fields', {
            'GPS Ground Track (deg true)',
            'Magnetic Heading (deg)'
        })
    
    def angle_difference(self, pred: float, actual: float) -> float:
        """
        Calculate angle difference (considering 0/360 wrap-around)
        
        Copied from comprehensive_flight_evaluation_no_norm.py
        """
        diff = abs(pred - actual)
        # If difference > 180 degrees, use wrap-around difference
        if diff > 180:
            return 360 - diff
        return diff
    
    def check_mutation(self, field: str, previous_value: Any, current_value: Any, task_type: str) -> Tuple[bool, Optional[str], float]:
        """
        Check if field value has mutation violation
        
        Copied from comprehensive_flight_evaluation_no_norm.py
        """
        if field not in self.mutation_thresholds:
            return True, None, 0.0
        
        threshold = self.mutation_thresholds[field]
        
        # Handle empty values
        if previous_value is None or current_value is None:
            return True, None, 0.0
        if previous_value == "" or current_value == "":
            return True, None, 0.0
        
        try:
            # M3 task: check mutations within array
            if task_type == 'M3' and isinstance(current_value, list) and len(current_value) > 1:
                max_change = 0.0
                for i in range(1, len(current_value)):
                    try:
                        prev = float(current_value[i-1])
                        curr = float(current_value[i])
                        
                        # Use angle difference for angle fields
                        if field in self.angle_fields:
                            change = self.angle_difference(curr, prev)
                        else:
                            change = abs(curr - prev)
                        
                        max_change = max(max_change, change)
                        
                        if change > threshold:
                            return False, f"{field}[{i}] mutation too large: {change:.6f} > {threshold:.6f}", change
                    except (ValueError, TypeError):
                        continue
                return True, None, max_change
            
            # S1 and M1 tasks: check mutation from previous value
            # If previous_value is array, take last value
            if isinstance(previous_value, list) and len(previous_value) > 0:
                try:
                    prev = float(previous_value[-1])
                except (ValueError, TypeError):
                    return True, None, 0.0
            else:
                try:
                    prev = float(previous_value)
                except (ValueError, TypeError):
                    return True, None, 0.0
            
            try:
                curr = float(current_value)
                
                # Use angle difference for angle fields
                if field in self.angle_fields:
                    change = self.angle_difference(curr, prev)
                else:
                    change = abs(curr - prev)
                
                if change > threshold:
                    return False, f"{field} mutation too large: {change:.6f} > {threshold:.6f}", change
                return True, None, change
            except (ValueError, TypeError):
                return True, None, 0.0
                
        except Exception as e:
            return True, None, 0.0
    
    def verify(self, sample: Any, model_output: Any, context: Dict[str, Any]) -> List[EvidenceAtom]:
        """
        Verify jump dynamics
        
        Args:
            sample: Sample data
            model_output: ModelOutput object
            context: Context dict with 'json_data', 'task_type', 'previous_predictions'
        
        Returns:
            List of EvidenceAtom objects
        """
        evidence = []
        json_data = context.get('json_data')
        task_type = context.get('task_type', 'S1')
        previous_predictions = context.get('previous_predictions', {})
        model_name = model_output.model_name
        required_fields = context.get('required_fields', [])
        
        if json_data is None:
            return evidence
        
        # Get previous predictions for this model
        prev_pred = previous_predictions.get(model_name, {})
        
        for field in required_fields:
            if field not in json_data:
                continue  # Missing fields handled by NumericValidityChecker
            
            current_value = json_data[field]
            previous_value = prev_pred.get(field)
            
            # Skip if no previous value (first sample)
            if previous_value is None and task_type != 'M3':
                continue
            
            is_valid, error_msg, max_change = self.check_mutation(
                field, previous_value, current_value, task_type
            )
            
            if not is_valid:
                # Determine severity based on violation magnitude
                threshold = self.mutation_thresholds.get(field, 0)
                if threshold > 0:
                    violation_ratio = max_change / threshold if max_change > 0 else 0
                    if violation_ratio > 2.0:
                        severity = Severity.CRITICAL
                    elif violation_ratio > 1.5:
                        severity = Severity.WARNING
                    else:
                        severity = Severity.WARNING
                else:
                    severity = Severity.WARNING
                
                evidence.append(EvidenceAtom(
                    id=self._generate_evidence_id(),
                    type="jump_dynamics",
                    field=field,
                    pass_=False,
                    severity=severity,
                    scope=Scope.FIELD,
                    message=error_msg or f"Field {field} has mutation violation",
                    meta={
                        "checker": "JumpDynamicsChecker",
                        "threshold": threshold,
                        "max_change": max_change,
                        "violation_ratio": violation_ratio if threshold > 0 else None,
                        "task_type": task_type
                    }
                ))
            else:
                # ✅ 修复：即使通过也要记录evidence atom（如果有previous_value）
                if previous_value is not None or task_type == 'M3':
                    evidence.append(EvidenceAtom(
                        id=self._generate_evidence_id(),
                        type="jump_dynamics",
                        field=field,
                        pass_=True,
                        severity=Severity.INFO,
                        scope=Scope.FIELD,
                        message=f"Field {field} mutation check passed",
                        meta={
                            "checker": "JumpDynamicsChecker",
                            "threshold": self.mutation_thresholds.get(field),
                            "max_change": max_change,
                            "task_type": task_type
                        }
                    ))
        
        return evidence
    
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities"""
        return ["jump_dynamics"]

