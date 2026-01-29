"""
Physics Constraint Checker

Checks physics-based constraints:
- Velocity-altitude consistency
- Attitude-velocity consistency
- Other physics laws

TODO: Implement physics constraint rules
"""

from typing import List, Dict, Any
from ..core.verifier_base import Verifier
from ..core.data_structures import EvidenceAtom, Severity, Scope


class PhysicsConstraintChecker(Verifier):
    """
    Physics constraint checker
    
    Checks physics-based constraints:
    - Velocity-altitude consistency
    - Attitude-velocity consistency
    - Other physics laws
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize physics constraint checker
        
        Args:
            config: Configuration dict with physics constraint rules
        """
        super().__init__(config, verifier_id="PHYSICS_CONSTRAINT")
        self.enabled = config.get('enabled', False)
        self.rules = config.get('rules', {})
    
    def _normalize_to_list(self, value):
        """Convert scalar or list to list format for uniform processing"""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]
    
    def verify(self, sample: Any, model_output: Any, context: Dict[str, Any]) -> List[EvidenceAtom]:
        """
        Verify physics constraints
        
        Implements minimal set of physics rules:
        1. M3 array internal continuity/reachability
        2. Velocity-altitude consistency
        3. Attitude-velocity consistency
        
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
        
        # Rule 1: M3 array internal continuity/reachability
        # Check if array values form a physically reachable trajectory
        if task_type == 'M3':
            required_fields = context.get('required_fields', [])
            for field in required_fields:
                if field not in json_data:
                    continue
                
                value = json_data[field]
                if not isinstance(value, list) or len(value) < 2:
                    continue
                
                # Check continuity: each step should be reachable
                violations = []
                for i in range(1, len(value)):
                    try:
                        prev = float(value[i-1])
                        curr = float(value[i])
                        change = abs(curr - prev)
                        
                        # Get threshold from jump_dynamics if available
                        threshold = self.rules.get('m3_continuity_thresholds', {}).get(field)
                        if threshold is None:
                            # Use default: 2x the jump threshold
                            from ..utils.config_loader import load_jump_thresholds
                            jump_thresholds = load_jump_thresholds()
                            base_threshold = jump_thresholds.get(field, 0)
                            threshold = base_threshold * 2.0 if base_threshold > 0 else float('inf')
                        
                        if change > threshold:
                            violations.append({
                                'index': i,
                                'change': change,
                                'threshold': threshold
                            })
                    except (ValueError, TypeError):
                        continue
                
                if violations:
                    max_violation = max(violations, key=lambda x: x['change'])
                    severity = Severity.CRITICAL if max_violation['change'] > max_violation['threshold'] * 1.5 else Severity.WARNING
                    
                    evidence.append(EvidenceAtom(
                        id=self._generate_evidence_id(),
                        type="physics_constraint",
                        field=f"{field}_continuity",
                        pass_=False,
                        severity=severity,
                        scope=Scope.FIELD,
                        message=f"Field {field} has {len(violations)} continuity violations in M3 array (max change: {max_violation['change']:.3f} > {max_violation['threshold']:.3f})",
                        meta={
                            "checker": "PhysicsConstraintChecker",
                            "rule": "m3_array_continuity",
                            "field": field,
                            "violations": len(violations),
                            "max_change": max_violation['change'],
                            "threshold": max_violation['threshold']
                        }
                    ))
                else:
                    # Record pass
                    evidence.append(EvidenceAtom(
                        id=self._generate_evidence_id(),
                        type="physics_constraint",
                        field=f"{field}_continuity",
                        pass_=True,
                        severity=Severity.INFO,
                        scope=Scope.FIELD,
                        message=f"Field {field} M3 array continuity check passed",
                        meta={
                            "checker": "PhysicsConstraintChecker",
                            "rule": "m3_array_continuity",
                            "field": field,
                            "array_length": len(value)
                        }
                    ))
        
        # Rule 2: Velocity-altitude consistency (ALWAYS CHECK, not just low altitude)
        # ✅ 修改为所有高度都检查，确保S1/M1也生成evidence
        altitude = json_data.get("GPS Altitude (WGS84 ft)")
        vertical_speed = json_data.get("Vertical Speed (fpm)")
        
        if altitude is not None and vertical_speed is not None:
            try:
                # Handle both scalar and list formats
                alt_vals = self._normalize_to_list(altitude)
                vs_vals = self._normalize_to_list(vertical_speed)
                
                # Check each timestep
                for idx, (alt_val, vs_val) in enumerate(zip(alt_vals, vs_vals)):
                    alt_float = float(alt_val)
                    vs_float = float(vs_val)
                    
                    # ✅ 通用检查：所有高度都检查垂直速度合理性
                    # At low altitude (< 1000ft), vertical speed should be more limited
                    if alt_float < 1000:
                        max_vs = 2000  # fpm (stricter for low altitude)
                    else:
                        max_vs = 5000  # fpm (more lenient for higher altitude)
                    
                    if abs(vs_float) > max_vs:
                        severity = Severity.WARNING
                        pass_check = False
                    else:
                        severity = Severity.INFO
                        pass_check = True
                    
                    # ✅ 为所有样本生成evidence（不只是failures）
                    if not pass_check or idx == 0:
                            timestep_info = f"[t={idx}] " if len(alt_vals) > 1 else ""
                            evidence.append(EvidenceAtom(
                                id=self._generate_evidence_id(),
                                type="physics_constraint",
                                field="Velocity_Altitude_Consistency",
                                pass_=pass_check,
                                severity=severity,
                                scope=Scope.CROSS_FIELD,
                                message=f"{timestep_info}Low altitude ({alt_float:.1f}ft) with vertical speed ({vs_float:.1f}fpm) {'exceeds' if not pass_check else 'within'} limit ({max_vs}fpm)",
                                meta={
                                    "checker": "PhysicsConstraintChecker",
                                    "rule": "velocity_altitude_consistency",
                                    "timestep": idx if len(alt_vals) > 1 else None,
                                    "altitude": alt_float,
                                    "vertical_speed": vs_float,
                                    "max_vs": max_vs
                                }
                            ))
            except (ValueError, TypeError, IndexError):
                pass
        
        # Rule 3: Attitude-velocity consistency (ALWAYS CHECK)
        # ✅ 修改为通用检查：所有样本都检查姿态合理性
        roll = json_data.get("Roll (deg)")
        pitch = json_data.get("Pitch (deg)")
        vu = json_data.get("GPS Velocity U (m/s)")
        
        if roll is not None and pitch is not None and vu is not None:
            try:
                # Handle both scalar and list formats
                roll_vals = self._normalize_to_list(roll)
                pitch_vals = self._normalize_to_list(pitch)
                vu_vals = self._normalize_to_list(vu)
                
                # Check each timestep
                for idx, (roll_val, pitch_val, vu_val) in enumerate(zip(roll_vals, pitch_vals, vu_vals)):
                    roll_float = float(roll_val)
                    pitch_float = float(pitch_val)
                    vu_float = float(vu_val)
                    
                    # ✅ 通用检查：所有样本都检查
                    # 1. 基础合理性：roll/pitch在正常范围内（±60°）
                    if abs(roll_float) > 60 or abs(pitch_float) > 60:
                        severity = Severity.CRITICAL
                        pass_check = False
                        reason = "extreme_attitude"
                    # 2. 大俯仰角应该有对应的垂直速度
                    elif abs(pitch_float) > 15:  # ✅ 降低阈值到15°
                        vu_expected = abs(pitch_float) / 30.0 * 5.0  # Rough estimate
                        if abs(vu_float) < vu_expected * 0.3:  # ✅ 放宽到30%
                            severity = Severity.WARNING
                            pass_check = False
                            reason = "pitch_velocity_mismatch"
                        else:
                            severity = Severity.INFO
                            pass_check = True
                            reason = "normal"
                    else:
                        # Normal attitude
                        severity = Severity.INFO
                        pass_check = True
                        reason = "normal"
                    
                    # ✅ 为所有样本生成evidence（不只是failures）
                    if not pass_check or idx == 0:
                        timestep_info = f"[t={idx}] " if len(roll_vals) > 1 else ""
                        evidence.append(EvidenceAtom(
                            id=self._generate_evidence_id(),
                            type="physics_constraint",
                            field="Attitude_Velocity_Consistency",
                            pass_=pass_check,
                            severity=severity,
                            scope=Scope.CROSS_FIELD,
                            message=f"{timestep_info}Roll={roll_float:.1f}°, Pitch={pitch_float:.1f}°, Vu={vu_float:.2f}m/s: {reason}",
                            meta={
                                "checker": "PhysicsConstraintChecker",
                                "rule": "attitude_velocity_consistency",
                                "timestep": idx if len(roll_vals) > 1 else None,
                                "roll": roll_float,
                                "pitch": pitch_float,
                                "vertical_velocity": vu_float,
                                "reason": reason
                            }
                        ))
            except (ValueError, TypeError, IndexError):
                pass
        
        return evidence
    
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities"""
        return ["physics_constraints"]

