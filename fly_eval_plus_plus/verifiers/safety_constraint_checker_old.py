"""
Safety Constraint Checker

Checks safety-related constraints:
- Extreme values
- Emergency patterns
- Safety-critical violations

TODO: Implement safety constraint rules
"""

from typing import List, Dict, Any
from ..core.verifier_base import Verifier
from ..core.data_structures import EvidenceAtom, Severity, Scope


class SafetyConstraintChecker(Verifier):
    """
    Safety constraint checker
    
    Checks safety-related constraints:
    - Extreme values
    - Emergency patterns
    - Safety-critical violations
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize safety constraint checker
        
        Args:
            config: Configuration dict with safety constraint rules
        """
        super().__init__(config, verifier_id="SAFETY_CONSTRAINT")
        self.enabled = config.get('enabled', False)
        self.extreme_values = config.get('extreme_values', {})
        self.emergency_patterns = config.get('emergency_patterns', [])
    
    def _normalize_to_list(self, value):
        """Convert scalar or list to list format for uniform processing"""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]
    
    def verify(self, sample: Any, model_output: Any, context: Dict[str, Any]) -> List[EvidenceAtom]:
        """
        Verify safety constraints
        
        Implements minimal set of safety rules:
        1. Rapid descent detection
        2. Extreme speed/altitude detection
        3. Stall-like condition detection
        
        Args:
            sample: Sample data
            model_output: ModelOutput object
            context: Context dict with 'json_data', 'task_type'
        
        Returns:
            List of EvidenceAtom objects
        """
        evidence = []
        
        if not self.enabled:
            return evidence
        
        json_data = context.get('json_data')
        if json_data is None:
            return evidence
        
        task_type = context.get('task_type', 'S1')
        
        # Rule 1: Rapid descent detection
        # Vertical speed < -3000 fpm is dangerous
        vertical_speed = json_data.get("Vertical Speed (fpm)")
        altitude = json_data.get("GPS Altitude (WGS84 ft)")
        
        if vertical_speed is not None:
            try:
                # Handle both scalar and list formats
                vs_vals = self._normalize_to_list(vertical_speed)
                alt_vals = self._normalize_to_list(altitude) if altitude is not None else [None] * len(vs_vals)
                
                # Check each timestep
                for idx, (vs_val, alt_val) in enumerate(zip(vs_vals, alt_vals)):
                    vs_float = float(vs_val)
                    
                    # Check for rapid descent
                    if vs_float < -3000:  # Descending faster than 3000 fpm
                        timestep_info = f"[t={idx}] " if len(vs_vals) > 1 else ""
                        severity = Severity.CRITICAL
                        pass_check = False
                        evidence.append(EvidenceAtom(
                            id=self._generate_evidence_id(),
                            type="safety_constraint",
                            field="Rapid_Descent",
                            pass_=pass_check,
                            severity=severity,
                            scope=Scope.SAMPLE,
                            message=f"{timestep_info}Rapid descent detected: {vs_float:.1f} fpm (threshold: -3000 fpm)",
                            meta={
                                "checker": "SafetyConstraintChecker",
                                "rule": "rapid_descent",
                                "timestep": idx if len(vs_vals) > 1 else None,
                                "vertical_speed": vs_float,
                                "threshold": -3000.0,
                                "altitude": float(alt_val) if alt_val is not None else None
                            }
                        ))
                    elif vs_float < -2000:  # Warning threshold
                        timestep_info = f"[t={idx}] " if len(vs_vals) > 1 else ""
                        severity = Severity.WARNING
                        pass_check = False
                        evidence.append(EvidenceAtom(
                            id=self._generate_evidence_id(),
                            type="safety_constraint",
                            field="Rapid_Descent",
                            pass_=pass_check,
                            severity=severity,
                            scope=Scope.SAMPLE,
                            message=f"{timestep_info}High descent rate: {vs_float:.1f} fpm (warning threshold: -2000 fpm)",
                            meta={
                                "checker": "SafetyConstraintChecker",
                                "rule": "rapid_descent",
                                "timestep": idx if len(vs_vals) > 1 else None,
                                "vertical_speed": vs_float,
                                "threshold": -2000.0
                            }
                        ))
            except (ValueError, TypeError, IndexError):
                pass
        
        # Rule 2: Extreme speed/altitude detection
        # Check for values beyond safe operating limits
        airspeed = json_data.get("Indicated Airspeed (kt)")
        ground_speed = json_data.get("GPS Ground Speed (kt)")
        
        if airspeed is not None:
            try:
                # Handle both scalar and list formats
                ias_vals = self._normalize_to_list(airspeed)
                
                # Check each timestep
                for idx, ias_val in enumerate(ias_vals):
                    ias_float = float(ias_val)
                    timestep_info = f"[t={idx}] " if len(ias_vals) > 1 else ""
                    
                    # Extreme speeds: < 30kt (stall risk) or > 180kt (overspeed)
                    if ias_float < 30:
                        severity = Severity.CRITICAL
                        pass_check = False
                        evidence.append(EvidenceAtom(
                            id=self._generate_evidence_id(),
                            type="safety_constraint",
                            field="Extreme_Speed",
                            pass_=pass_check,
                            severity=severity,
                            scope=Scope.FIELD,
                            message=f"{timestep_info}Extremely low airspeed: {ias_float:.1f} kt (stall risk threshold: 30 kt)",
                            meta={
                                "checker": "SafetyConstraintChecker",
                                "rule": "extreme_speed",
                                "timestep": idx if len(ias_vals) > 1 else None,
                                "airspeed": ias_float,
                                "threshold": 30.0,
                                "type": "low"
                            }
                        ))
                    elif ias_float > 180:
                        severity = Severity.WARNING
                        pass_check = False
                        evidence.append(EvidenceAtom(
                            id=self._generate_evidence_id(),
                            type="safety_constraint",
                            field="Extreme_Speed",
                            pass_=pass_check,
                            severity=severity,
                            scope=Scope.FIELD,
                            message=f"{timestep_info}Extremely high airspeed: {ias_float:.1f} kt (overspeed threshold: 180 kt)",
                            meta={
                                "checker": "SafetyConstraintChecker",
                                "rule": "extreme_speed",
                                "timestep": idx if len(ias_vals) > 1 else None,
                                "airspeed": ias_float,
                                "threshold": 180.0,
                                "type": "high"
                            }
                        ))
            except (ValueError, TypeError, IndexError):
                pass
        
        if altitude is not None:
            try:
                # Handle both scalar and list formats
                alt_vals = self._normalize_to_list(altitude)
                
                # Check each timestep
                for idx, alt_val in enumerate(alt_vals):
                    alt_float = float(alt_val)
                    timestep_info = f"[t={idx}] " if len(alt_vals) > 1 else ""
                    
                    # Extreme altitudes: < 0ft (ground contact) or > 15000ft (high altitude)
                    if alt_float < 0:
                        severity = Severity.CRITICAL
                        pass_check = False
                        evidence.append(EvidenceAtom(
                            id=self._generate_evidence_id(),
                            type="safety_constraint",
                            field="Extreme_Altitude",
                            pass_=pass_check,
                            severity=severity,
                            scope=Scope.FIELD,
                            message=f"{timestep_info}Negative altitude: {alt_float:.1f} ft (ground contact risk)",
                            meta={
                                "checker": "SafetyConstraintChecker",
                                "rule": "extreme_altitude",
                                "timestep": idx if len(alt_vals) > 1 else None,
                                "altitude": alt_float,
                                "threshold": 0.0,
                                "type": "low"
                            }
                        ))
                    elif alt_float > 15000:
                        severity = Severity.WARNING
                        pass_check = False
                        evidence.append(EvidenceAtom(
                            id=self._generate_evidence_id(),
                            type="safety_constraint",
                            field="Extreme_Altitude",
                            pass_=pass_check,
                            severity=severity,
                            scope=Scope.FIELD,
                            message=f"{timestep_info}Extremely high altitude: {alt_float:.1f} ft (high altitude threshold: 15000 ft)",
                            meta={
                                "checker": "SafetyConstraintChecker",
                                "rule": "extreme_altitude",
                                "timestep": idx if len(alt_vals) > 1 else None,
                                "altitude": alt_float,
                                "threshold": 15000.0,
                                "type": "high"
                            }
                        ))
            except (ValueError, TypeError, IndexError):
                pass
        
        # Rule 3: Stall-like condition detection
        # Low airspeed + high pitch + low vertical speed = stall risk
        airspeed = json_data.get("Indicated Airspeed (kt)")
        pitch = json_data.get("Pitch (deg)")
        vertical_speed = json_data.get("Vertical Speed (fpm)")
        
        if airspeed is not None and pitch is not None and vertical_speed is not None:
            try:
                # Handle both scalar and list formats
                ias_vals = self._normalize_to_list(airspeed)
                pitch_vals = self._normalize_to_list(pitch)
                vs_vals = self._normalize_to_list(vertical_speed)
                
                # Check each timestep
                for idx, (ias_val, pitch_val, vs_val) in enumerate(zip(ias_vals, pitch_vals, vs_vals)):
                    ias_float = float(ias_val)
                    pitch_float = float(pitch_val)
                    vs_float = float(vs_val)
                    
                    # Stall indicators: low speed + high pitch + low/negative vertical speed
                    if ias_float < 50 and pitch_float > 15 and vs_float < 500:
                        timestep_info = f"[t={idx}] " if len(ias_vals) > 1 else ""
                        severity = Severity.CRITICAL
                        pass_check = False
                        evidence.append(EvidenceAtom(
                            id=self._generate_evidence_id(),
                            type="safety_constraint",
                            field="Stall_Condition",
                            pass_=pass_check,
                            severity=severity,
                            scope=Scope.SAMPLE,
                            message=f"{timestep_info}Stall-like condition: low airspeed ({ias_float:.1f}kt) + high pitch ({pitch_float:.1f}°) + low vertical speed ({vs_float:.1f}fpm)",
                            meta={
                                "checker": "SafetyConstraintChecker",
                                "rule": "stall_condition",
                                "timestep": idx if len(ias_vals) > 1 else None,
                                "airspeed": ias_float,
                                "pitch": pitch_float,
                                "vertical_speed": vs_float,
                                "thresholds": {"airspeed": 50.0, "pitch": 15.0, "vertical_speed": 500.0}
                            }
                        ))
            except (ValueError, TypeError, IndexError):
                pass
        
        return evidence
    
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities"""
        return ["safety_constraints"]

