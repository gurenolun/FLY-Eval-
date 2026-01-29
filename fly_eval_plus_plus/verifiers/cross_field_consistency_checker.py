"""
Cross-Field Consistency Checker

Checks consistency between related fields:
- GPS altitude vs Baro altitude
- Ground speed vs Indicated airspeed
- Other cross-field consistency rules

TODO: Implement cross-field consistency rules
"""

from typing import List, Dict, Any
import math
from ..core.verifier_base import Verifier
from ..core.data_structures import EvidenceAtom, Severity, Scope


class CrossFieldConsistencyChecker(Verifier):
    """
    Cross-field consistency checker
    
    Checks consistency between related fields:
    - GPS altitude vs Baro altitude
    - Ground speed vs Indicated airspeed
    - Other cross-field consistency rules
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize cross-field consistency checker
        
        Args:
            config: Configuration dict with cross-field consistency rules
        """
        super().__init__(config, verifier_id="CROSS_FIELD_CONSISTENCY")
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
        Verify cross-field consistency
        
        Implements minimal set of high-value rules:
        1. GPS Altitude vs Baro Altitude consistency
        2. Ground Speed vs Velocity components consistency
        3. Track vs Vn/Ve direction consistency
        
        Args:
            sample: Sample data
            model_output: ModelOutput object
            context: Context dict with 'json_data'
        
        Returns:
            List of EvidenceAtom objects
        """
        evidence = []
        
        if not self.enabled:
            return evidence
        
        json_data = context.get('json_data')
        if json_data is None:
            return evidence
        
        # Rule 1: GPS Altitude vs Baro Altitude consistency
        # Note: GPS Alt (WGS84) and Baro Alt (pressure-based) are different systems
        # Typical difference: 0-2000ft is normal, >3000ft indicates potential issues
        gps_alt = json_data.get("GPS Altitude (WGS84 ft)")
        baro_alt = json_data.get("Baro Altitude (ft)")
        
        if gps_alt is not None and baro_alt is not None:
            try:
                # Handle both scalar and list formats
                gps_vals = self._normalize_to_list(gps_alt)
                baro_vals = self._normalize_to_list(baro_alt)
                
                # Check each timestep
                for idx, (gps_val, baro_val) in enumerate(zip(gps_vals, baro_vals)):
                    gps_float = float(gps_val)
                    baro_float = float(baro_val)
                    diff = abs(gps_float - baro_float)
                    
                    # ✅ 放宽阈值：基于实际数据分布（1500-1600 ft差异是常见的）
                    # Thresholds: < 2000ft = pass, 2000-3000ft = warning, > 3000ft = critical
                    if diff > 3000:
                        severity = Severity.CRITICAL
                        pass_check = False
                    elif diff > 2000:
                        severity = Severity.WARNING
                        pass_check = False
                    else:
                        severity = Severity.INFO
                        pass_check = True
                    
                    # Only add evidence for failures or first pass (to avoid too many atoms)
                    if not pass_check or idx == 0:
                        timestep_info = f"[t={idx}] " if len(gps_vals) > 1 else ""
                        evidence.append(EvidenceAtom(
                            id=self._generate_evidence_id(),
                            type="cross_field_consistency",
                            field="GPS_Alt_vs_Baro_Alt",
                            pass_=pass_check,
                            severity=severity,
                            scope=Scope.CROSS_FIELD,
                            message=f"{timestep_info}GPS Altitude ({gps_float:.1f}ft) vs Baro Altitude ({baro_float:.1f}ft) difference: {diff:.1f}ft",
                            meta={
                                "checker": "CrossFieldConsistencyChecker",
                                "rule": "altitude_consistency",
                                "timestep": idx if len(gps_vals) > 1 else None,
                                "gps_alt": gps_float,
                                "baro_alt": baro_float,
                                "difference": diff,
                                "threshold": 2000.0  # ✅ 更新为新阈值
                            }
                        ))
            except (ValueError, TypeError, IndexError) as e:
                pass
        
        # Rule 2: Ground Speed vs Velocity components consistency
        # GS ≈ sqrt(Ve^2 + Vn^2) (approximately, ignoring vertical component)
        gs = json_data.get("GPS Ground Speed (kt)")
        ve = json_data.get("GPS Velocity E (m/s)")
        vn = json_data.get("GPS Velocity N (m/s)")
        
        if gs is not None and ve is not None and vn is not None:
            try:
                # Handle both scalar and list formats
                gs_vals = self._normalize_to_list(gs)
                ve_vals = self._normalize_to_list(ve)
                vn_vals = self._normalize_to_list(vn)
                
                # Check each timestep
                for idx, (gs_val, ve_val, vn_val) in enumerate(zip(gs_vals, ve_vals, vn_vals)):
                    gs_float = float(gs_val)
                    ve_float = float(ve_val)
                    vn_float = float(vn_val)
                    
                    # Convert m/s to kt (1 m/s ≈ 1.944 kt)
                    ve_kt = ve_float * 1.944
                    vn_kt = vn_float * 1.944
                    calculated_gs = (ve_kt**2 + vn_kt**2)**0.5
                    
                    diff = abs(gs_float - calculated_gs)
                    # Threshold: < 5kt = pass, 5-15kt = warning, > 15kt = critical
                    if diff > 15:
                        severity = Severity.CRITICAL
                        pass_check = False
                    elif diff > 5:
                        severity = Severity.WARNING
                        pass_check = False
                    else:
                        severity = Severity.INFO
                        pass_check = True
                    
                    # Only add evidence for failures or first pass
                    if not pass_check or idx == 0:
                        timestep_info = f"[t={idx}] " if len(gs_vals) > 1 else ""
                        evidence.append(EvidenceAtom(
                            id=self._generate_evidence_id(),
                            type="cross_field_consistency",
                            field="Ground_Speed_vs_Velocity",
                            pass_=pass_check,
                            severity=severity,
                            scope=Scope.CROSS_FIELD,
                            message=f"{timestep_info}Ground Speed ({gs_float:.1f}kt) vs calculated from Ve/Vn ({calculated_gs:.1f}kt) difference: {diff:.1f}kt",
                            meta={
                                "checker": "CrossFieldConsistencyChecker",
                                "rule": "speed_consistency",
                                "timestep": idx if len(gs_vals) > 1 else None,
                                "ground_speed": gs_float,
                                "ve": ve_float,
                                "vn": vn_float,
                                "calculated_gs": calculated_gs,
                                "difference": diff,
                                "threshold": 5.0
                            }
                        ))
            except (ValueError, TypeError, IndexError):
                pass
        
        # Rule 3: Track vs Vn/Ve direction consistency
        # Track angle should match atan2(Ve, Vn) direction
        track = json_data.get("GPS Ground Track (deg true)")
        ve = json_data.get("GPS Velocity E (m/s)")
        vn = json_data.get("GPS Velocity N (m/s)")
        
        if track is not None and ve is not None and vn is not None:
            try:
                # Handle both scalar and list formats
                track_vals = self._normalize_to_list(track)
                ve_vals = self._normalize_to_list(ve)
                vn_vals = self._normalize_to_list(vn)
                
                # Check each timestep
                for idx, (track_val, ve_val, vn_val) in enumerate(zip(track_vals, ve_vals, vn_vals)):
                    track_float = float(track_val)
                    ve_float = float(ve_val)
                    vn_float = float(vn_val)
                    
                    # Calculate direction from velocity components
                    # atan2(ve, vn) gives angle in radians, convert to degrees
                    calculated_track = math.degrees(math.atan2(ve_float, vn_float))
                    # Normalize to 0-360
                    if calculated_track < 0:
                        calculated_track += 360
                    
                    # Use angle difference (considering wrap-around)
                    diff = abs(track_float - calculated_track)
                    if diff > 180:
                        diff = 360 - diff
                    
                    # Threshold: < 10deg = pass, 10-30deg = warning, > 30deg = critical
                    if diff > 30:
                        severity = Severity.CRITICAL
                        pass_check = False
                    elif diff > 10:
                        severity = Severity.WARNING
                        pass_check = False
                    else:
                        severity = Severity.INFO
                        pass_check = True
                    
                    # Only add evidence for failures or first pass
                    if not pass_check or idx == 0:
                        timestep_info = f"[t={idx}] " if len(track_vals) > 1 else ""
                        evidence.append(EvidenceAtom(
                            id=self._generate_evidence_id(),
                            type="cross_field_consistency",
                            field="Track_vs_Velocity_Direction",
                            pass_=pass_check,
                            severity=severity,
                            scope=Scope.CROSS_FIELD,
                            message=f"{timestep_info}Track ({track_float:.1f}°) vs calculated from Ve/Vn ({calculated_track:.1f}°) difference: {diff:.1f}°",
                            meta={
                                "checker": "CrossFieldConsistencyChecker",
                                "rule": "track_consistency",
                                "timestep": idx if len(track_vals) > 1 else None,
                                "track": track_float,
                                "ve": ve_float,
                                "vn": vn_float,
                                "calculated_track": calculated_track,
                                "difference": diff,
                                "threshold": 10.0
                            }
                        ))
            except (ValueError, TypeError, IndexError):
                pass
        
        return evidence
    
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities"""
        return ["cross_field_consistency"]

