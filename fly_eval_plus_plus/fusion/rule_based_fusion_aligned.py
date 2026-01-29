"""
Rule-Based Fusion (Aligned with LLM Judge Version)

Fixed protocol aggregator that maps evidence to scores using the same 5 dimensions as LLM Judge.
This version aligns with LLM Judge's 5-dimensional rubric for consistency.
"""

from typing import Dict, List, Any, Optional, Tuple
from ..core.data_structures import EvidenceAtom, Record
from ..rubric.rubric_definition import GRADE_SCORE_MAP, Grade, Dimension, RUBRIC


class RuleBasedFusionAligned:
    """
    Rule-based fusion aggregator (aligned with LLM Judge)
    
    Maps evidence vectors to 5-dimensional scores matching LLM Judge's rubric.
    Uses deterministic rules instead of LLM to assign grades.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize rule-based fusion
        
        Args:
            config: Fusion protocol config with gating_rules and scoring_rules
        """
        self.config = config
        self.gating_rules = config.get('gating_rules', {})
        self.scoring_rules = config.get('scoring_rules', {})
    
    def gate(self, evidence_atoms: List[EvidenceAtom]) -> Tuple[bool, List[str]]:
        """
        Apply gating rules
        
        Protocol/key safety constraint failures → ineligible
        
        Args:
            evidence_atoms: All evidence atoms
        
        Returns:
            (passed_gating, gating_reasons)
        """
        passed = True
        reasons = []
        
        # Check for critical failures
        critical_failures = [e for e in evidence_atoms if e.severity.value == 'critical' and not e.pass_]
        if critical_failures:
            passed = False
            reasons.append(f"Found {len(critical_failures)} critical constraint violations")
        
        return passed, reasons
    
    def _count_evidence_by_type(self, evidence_atoms: List[EvidenceAtom]) -> Dict[str, Dict[str, int]]:
        """Count evidence atoms by type and severity"""
        counts = {}
        
        for atom in evidence_atoms:
            # Handle string representation of EvidenceAtom (from JSON serialization)
            if isinstance(atom, str):
                # Parse string representation: EvidenceAtom(id='...', type='...', ..., severity=<Severity.XXX: '...'>, ..., pass_=True/False, ...)
                import re
                type_match = re.search(r"type='([^']+)'", atom)
                severity_match = re.search(r"severity=<Severity\.([^:]+):\s*'([^']+)'", atom)
                pass_match = re.search(r"pass_=([^,)]+)", atom)
                
                if type_match and severity_match and pass_match:
                    ev_type = type_match.group(1)
                    severity_str = severity_match.group(2).lower()  # INFO -> info
                    pass_val = pass_match.group(1).strip()
                    pass_bool = pass_val.lower() == 'true'
                    
                    # Map severity string to count key
                    severity_map = {
                        'critical': 'critical',
                        'warning': 'warning',
                        'info': 'info'
                    }
                    severity_key = severity_map.get(severity_str, 'info')
                else:
                    # Skip if cannot parse
                    continue
            else:
                # Handle EvidenceAtom object
                ev_type = atom.type
                severity_key = atom.severity.value
                pass_bool = atom.pass_
            
            if ev_type not in counts:
                counts[ev_type] = {
                    'critical': 0,
                    'warning': 0,
                    'info': 0,
                    'pass': 0,
                    'fail': 0
                }
            
            counts[ev_type][severity_key] += 1
            if pass_bool:
                counts[ev_type]['pass'] += 1
            else:
                counts[ev_type]['fail'] += 1
        
        return counts
    
    def _determine_grade(self, dimension: Dimension, evidence_counts: Dict[str, Dict[str, int]], 
                        protocol_result: Dict[str, Any], conditional_error: Optional[Dict[str, Any]] = None) -> Grade:
        """
        Determine grade for a dimension based on evidence counts and rubric
        
        Args:
            dimension: Evaluation dimension
            evidence_counts: Evidence counts by type
            protocol_result: Protocol result dict
            conditional_error: Conditional error dict (optional)
        
        Returns:
            Grade (A/B/C/D)
        """
        rubric_dim = RUBRIC.get(dimension, {})
        
        # Check each grade from A to D (best to worst)
        for grade in [Grade.A, Grade.B, Grade.C, Grade.D]:
            if grade not in rubric_dim:
                continue
            
            requirements = rubric_dim[grade].get('evidence_requirements', {})
            matches = True
            
            # Check Protocol/Schema Compliance
            if dimension == Dimension.PROTOCOL_SCHEMA:
                # Check numeric_validity
                if 'numeric_validity' in requirements:
                    req = requirements['numeric_validity']
                    numeric_counts = evidence_counts.get('numeric_validity', {})
                    
                    # ✅ 使用失败率而不是绝对数量
                    total = numeric_counts.get('pass', 0) + numeric_counts.get('fail', 0)
                    if total > 0:
                        failure_rate = numeric_counts.get('fail', 0) / total
                        max_failure_rate = req.get('max_failure_rate', float('inf'))
                        if failure_rate > max_failure_rate:
                            matches = False
                
                # Check parsing
                if 'parsing' in requirements:
                    parsing_success = protocol_result.get('parsing', {}).get('success', False)
                    if requirements['parsing'].get('success', True) != parsing_success:
                        matches = False
                
                # Check field_completeness
                if 'field_completeness' in requirements:
                    completeness_rate = protocol_result.get('field_completeness', {}).get('completeness_rate', 0.0)
                    required_rate = requirements['field_completeness'].get('rate', 1.0)
                    if completeness_rate < required_rate:
                        matches = False
            
            # Check Field Validity & Local Dynamics
            elif dimension == Dimension.FIELD_VALIDITY:
                # Check range_sanity
                if 'range_sanity' in requirements:
                    req = requirements['range_sanity']
                    range_counts = evidence_counts.get('range_sanity', {})
                    
                    # ✅ 使用失败率而不是绝对数量
                    total = range_counts.get('pass', 0) + range_counts.get('fail', 0)
                    if total > 0:
                        failure_rate = range_counts.get('fail', 0) / total
                        max_failure_rate = req.get('max_failure_rate', float('inf'))
                        if failure_rate > max_failure_rate:
                            matches = False
                
                # Check jump_dynamics
                if 'jump_dynamics' in requirements:
                    req = requirements['jump_dynamics']
                    jump_counts = evidence_counts.get('jump_dynamics', {})
                    
                    # ✅ 使用失败率而不是绝对数量
                    total = jump_counts.get('pass', 0) + jump_counts.get('fail', 0)
                    if total > 0:
                        failure_rate = jump_counts.get('fail', 0) / total
                        max_failure_rate = req.get('max_failure_rate', float('inf'))
                        if failure_rate > max_failure_rate:
                            matches = False
            
            # Check Physics/Cross-field Consistency
            elif dimension == Dimension.PHYSICS_CONSISTENCY:
                # Check cross_field_consistency
                if 'cross_field_consistency' in requirements:
                    req = requirements['cross_field_consistency']
                    cross_counts = evidence_counts.get('cross_field_consistency', {})
                    
                    # ✅ 使用失败率而不是绝对数量
                    total = cross_counts.get('pass', 0) + cross_counts.get('fail', 0)
                    if total > 0:
                        failure_rate = cross_counts.get('fail', 0) / total
                        max_failure_rate = req.get('max_failure_rate', float('inf'))
                        if failure_rate > max_failure_rate:
                            matches = False
                
                # Check physics_constraint
                if 'physics_constraint' in requirements:
                    req = requirements['physics_constraint']
                    physics_counts = evidence_counts.get('physics_constraint', {})
                    
                    # ✅ 使用失败率而不是绝对数量
                    total = physics_counts.get('pass', 0) + physics_counts.get('fail', 0)
                    if total > 0:
                        failure_rate = physics_counts.get('fail', 0) / total
                        max_failure_rate = req.get('max_failure_rate', float('inf'))
                        if failure_rate > max_failure_rate:
                            matches = False
            
            # Check Safety Constraint Satisfaction
            elif dimension == Dimension.SAFETY_CONSTRAINT:
                # Check safety_constraint
                if 'safety_constraint' in requirements:
                    req = requirements['safety_constraint']
                    safety_counts = evidence_counts.get('safety_constraint', {})
                    
                    # ✅ 使用失败率而不是绝对数量
                    total = safety_counts.get('pass', 0) + safety_counts.get('fail', 0)
                    if total > 0:
                        failure_rate = safety_counts.get('fail', 0) / total
                        max_failure_rate = req.get('max_failure_rate', float('inf'))
                        if failure_rate > max_failure_rate:
                            matches = False
            
            # Check Predictive Quality & Reliability
            elif dimension == Dimension.PREDICTIVE_QUALITY:
                # Check conditional_error
                if 'conditional_error' in requirements and conditional_error:
                    req = requirements['conditional_error']
                    mae_score = conditional_error.get('mae_score', 0)
                    rmse_score = conditional_error.get('rmse_score', 0)
                    if req.get('mae_score', 0) > mae_score:
                        matches = False
                    if req.get('rmse_score', 0) > rmse_score:
                        matches = False
                
                # Check reliability (if available)
                if 'reliability' in requirements:
                    # For now, assume acceptable if conditional_error is available
                    if conditional_error is None:
                        matches = False
            
            if matches:
                return grade
        
        # Default to D if no grade matches
        return Grade.D
    
    def calculate_scores(self, record: Record, sample: Any = None, model_output: Any = None, 
                       context: Dict[str, Any] = None) -> Dict[str, float]:
        """
        Calculate scores from evidence using 5-dimensional rubric (aligned with LLM Judge)
        
        Args:
            record: Record with evidence_pack
            sample: Sample object (optional, for error calculation)
            model_output: ModelOutput object (optional, for error calculation)
            context: Context dict with reference data (optional, for error calculation)
        
        Returns:
            Dict with dimension scores, overall_score matching LLM Judge format
        """
        evidence_atoms = record.evidence_pack.get('atoms', [])
        protocol_result = record.protocol_result
        
        # Count evidence by type
        evidence_counts = self._count_evidence_by_type(evidence_atoms)
        
        # Calculate conditional error if available
        conditional_error = None
        if sample and model_output and context:
            json_data = context.get('json_data')
            gold_data = sample.gold.get('next_second') or sample.gold.get('T+1', {})
            
            if json_data and gold_data:
                errors = []
                required_fields = context.get('required_fields', [])
                
                for field in required_fields:
                    if field in json_data and field in gold_data:
                        try:
                            pred_val = json_data[field]
                            gold_val = gold_data[field]
                            
                            # Handle list case (for M3 task with multiple time steps)
                            if isinstance(pred_val, list) and isinstance(gold_val, list):
                                for p, g in zip(pred_val, gold_val):
                                    try:
                                        errors.append(abs(float(p) - float(g)))
                                    except (ValueError, TypeError):
                                        pass
                            # Handle scalar case (for S1/M1 tasks)
                            else:
                                try:
                                    pred_val_float = float(pred_val)
                                    gold_val_float = float(gold_val)
                                    errors.append(abs(pred_val_float - gold_val_float))
                                except (ValueError, TypeError):
                                    pass
                        except (ValueError, TypeError):
                            pass
                
                if errors:
                    mae = sum(errors) / len(errors)
                    rmse = (sum(e**2 for e in errors) / len(errors)) ** 0.5
                    
                    mae_score = self._mae_to_score(mae)
                    rmse_score = self._rmse_to_score(rmse)
                    
                    conditional_error = {
                        "mae": mae,
                        "rmse": rmse,
                        "mae_score": mae_score,
                        "rmse_score": rmse_score,
                        "combined_score": (mae_score + rmse_score) / 2.0  # Arithmetic mean for dimension 5
                    }
        
        # Determine grades for each dimension (except Predictive Quality)
        grade_vector = {}
        dimension_scores = {}
        
        for dimension in Dimension:
            # Dimension 5 (Predictive Quality) uses direct score calculation, not grade-based
            if dimension == Dimension.PREDICTIVE_QUALITY:
                # Use direct score calculation: arithmetic mean of mae_score and rmse_score
                if conditional_error:
                    mae_score = conditional_error.get('mae_score', 0)
                    rmse_score = conditional_error.get('rmse_score', 0)
                    # Arithmetic mean (not weighted average) - score is already 0-100
                    predictive_quality_score = (mae_score + rmse_score) / 2.0
                    dimension_scores[dimension.value] = predictive_quality_score / 100.0  # Normalize to 0-1 for consistency
                    # Set grade to None or skip for dimension 5
                    grade_vector[dimension.value] = None  # No grade for dimension 5
                else:
                    # No conditional error available (not eligible), score is 0
                    dimension_scores[dimension.value] = 0.0
                    grade_vector[dimension.value] = None
            else:
                # Other dimensions use grade-based scoring
                grade = self._determine_grade(dimension, evidence_counts, protocol_result, conditional_error)
                grade_vector[dimension.value] = grade.value
                dimension_scores[dimension.value] = GRADE_SCORE_MAP[grade]
        
        # Compute overall score (mean of dimension scores, same as LLM Judge)
        # Note: dimension_scores are normalized to 0-1 range
        overall_score = sum(dimension_scores.values()) / len(dimension_scores) if dimension_scores else 0.0
        
        # Determine overall grade
        overall_grade_value = overall_score
        if overall_grade_value >= 0.875:  # (1.0 + 0.75) / 2
            overall_grade = Grade.A.value
        elif overall_grade_value >= 0.625:  # (0.75 + 0.5) / 2
            overall_grade = Grade.B.value
        elif overall_grade_value >= 0.25:  # (0.5 + 0.0) / 2
            overall_grade = Grade.C.value
        else:
            overall_grade = Grade.D.value
        
        # Also compute legacy scores for backward compatibility
        availability_score = protocol_result.get('field_completeness', {}).get('completeness_rate', 0.0) * 100.0
        
        # Constraint satisfaction from evidence atoms
        if not evidence_atoms:
            constraint_satisfaction_score = 100.0
        else:
            total_weight = 0.0
            passed_weight = 0.0
            
            severity_weights = {
                'critical': 3.0,
                'warning': 1.0,
                'info': 0.5
            }
            
            for atom in evidence_atoms:
                weight = severity_weights.get(atom.severity.value, 1.0)
                total_weight += weight
                
                # 优先使用 score 字段（支持多级评分：0.0, 0.25, 0.5, 0.75, 1.0）
                if hasattr(atom, 'score') and atom.score is not None:
                    passed_weight += weight * atom.score
                elif atom.pass_:
                    # 向后兼容：使用 pass_ 字段（二元评分）
                    passed_weight += weight
            
            if total_weight > 0:
                constraint_satisfaction_score = (passed_weight / total_weight) * 100.0
            else:
                constraint_satisfaction_score = 100.0
        
        # Conditional error score (for backward compatibility)
        if conditional_error:
            conditional_error_score = conditional_error['combined_score']
        else:
            conditional_error_score = constraint_satisfaction_score
        
        # Dimension 5 score (for explicit reporting) - already calculated above
        predictive_quality_score = dimension_scores.get(Dimension.PREDICTIVE_QUALITY.value, 0.0) * 100.0
        
        return {
            # 5-dimensional scores (aligned with LLM Judge)
            "grade_vector": grade_vector,
            "overall_grade": overall_grade,
            "dimension_scores": dimension_scores,  # Normalized to 0-1
            "dimension_scores_scaled": {k: v * 100.0 for k, v in dimension_scores.items()},  # Scaled to 0-100
            "overall_score": overall_score * 100.0,  # Scale to 0-100
            # Dimension 5 specific scores (direct from nMAE/nRMSE calculation)
            "predictive_quality_score": predictive_quality_score,
            "mae_score": conditional_error.get('mae_score', 0.0) if conditional_error else 0.0,
            "rmse_score": conditional_error.get('rmse_score', 0.0) if conditional_error else 0.0,
            # Legacy scores (for backward compatibility)
            "availability_score": availability_score,
            "constraint_satisfaction_score": constraint_satisfaction_score,
            "conditional_error_score": conditional_error_score,
            "total_score": overall_score * 100.0  # Use overall_score as total_score
        }
    
    def _mae_to_score(self, mae: float) -> float:
        """Convert MAE to score (0-100) using segmented scoring"""
        if mae < 5:
            return 100 - (mae / 5) * 10
        elif mae < 20:
            return 90 - ((mae - 5) / 15) * 20
        elif mae < 50:
            return 70 - ((mae - 20) / 30) * 20
        elif mae < 100:
            return 50 - ((mae - 50) / 50) * 20
        elif mae < 200:
            return 30 - ((mae - 100) / 100) * 15
        else:
            return max(5, 15 - ((mae - 200) / 100) * 10)
    
    def _rmse_to_score(self, rmse: float) -> float:
        """Convert RMSE to score (0-100) using segmented scoring"""
        if rmse < 10:
            return 100 - (rmse / 10) * 10
        elif rmse < 50:
            return 90 - ((rmse - 10) / 40) * 20
        elif rmse < 100:
            return 70 - ((rmse - 50) / 50) * 20
        elif rmse < 200:
            return 50 - ((rmse - 100) / 100) * 20
        elif rmse < 300:
            return 30 - ((rmse - 200) / 100) * 15
        else:
            return max(5, 15 - ((rmse - 300) / 100) * 10)

