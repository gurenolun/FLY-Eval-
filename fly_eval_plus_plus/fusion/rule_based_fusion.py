"""
Rule-Based Fusion

Fixed protocol aggregator that maps evidence to scores.
Uses gating rules and scoring rules.
"""

from typing import Dict, List, Any, Optional, Tuple
from ..core.data_structures import EvidenceAtom, Record


class RuleBasedFusion:
    """
    Rule-based fusion aggregator
    
    Maps evidence vectors to sub-scores/total scores using fixed protocol.
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
        
        Protocol/key safety constraint failures → ineligible with explicit upper limit/grade.
        
        Args:
            evidence_atoms: All evidence atoms
        
        Returns:
            (passed_gating, gating_reasons)
        """
        # TODO: Implement gating logic
        # Check gating_rules:
        # - protocol_failure: max_allowed = 0, severity = critical
        # - safety_constraint_violation: max_allowed = 0, severity = critical
        # - key_field_missing: max_allowed = 0, severity = critical
        
        passed = True
        reasons = []
        
        # Placeholder: Implement gating logic
        # For now, check for critical failures
        
        critical_failures = [e for e in evidence_atoms if e.severity.value == 'critical' and not e.pass_]
        if critical_failures:
            passed = False
            reasons.append(f"Found {len(critical_failures)} critical constraint violations")
        
        return passed, reasons
    
    def calculate_scores(self, record: Record, sample: Any = None, model_output: Any = None, 
                       context: Dict[str, Any] = None) -> Dict[str, float]:
        """
        Calculate scores from evidence
        
        Fixed protocol: gating + sub-scores + total score
        
        Args:
            record: Record with evidence_pack
            sample: Sample object (optional, for error calculation)
            model_output: ModelOutput object (optional, for error calculation)
            context: Context dict with reference data (optional, for error calculation)
        
        Returns:
            Dict with availability_score, constraint_satisfaction_score, conditional_error_score, total_score
        """
        evidence_atoms = record.evidence_pack.get('atoms', [])
        
        # 1. Availability Score (0-100)
        # Based on protocol_result field_completeness
        protocol_result = record.protocol_result
        field_completeness = protocol_result.get('field_completeness', {})
        completeness_rate = field_completeness.get('completeness_rate', 0.0)
        availability_score = completeness_rate  # Direct use of completeness rate
        
        # 2. Constraint Satisfaction Score (0-100)
        # Based on evidence atoms: count pass vs fail, weighted by severity
        if not evidence_atoms:
            constraint_satisfaction_score = 100.0  # No evidence = all pass
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
                if atom.pass_:
                    passed_weight += weight
            
            if total_weight > 0:
                constraint_satisfaction_score = (passed_weight / total_weight) * 100.0
            else:
                constraint_satisfaction_score = 100.0
        
        # 3. Conditional Error Score (0-100)
        # Only calculated for eligible samples (after gating)
        # Based on MAE/RMSE if reference data available
        conditional_error_score = None
        
        if sample and model_output and context:
            # Check if sample is eligible (has gold and passed gating)
            if sample.gold.get('available', False):
                # Calculate MAE/RMSE for eligible sample
                json_data = context.get('json_data')
                gold_data = sample.gold.get('next_second') or sample.gold.get('T+1', {})
                
                if json_data and gold_data:
                    errors = []
                    required_fields = context.get('required_fields', [])
                    
                    for field in required_fields:
                        if field in json_data and field in gold_data:
                            try:
                                pred_val = float(json_data[field])
                                gold_val = float(gold_data[field])
                                
                                # Handle M3 array values
                                if isinstance(pred_val, list) and isinstance(gold_val, list):
                                    for p, g in zip(pred_val, gold_val):
                                        errors.append(abs(float(p) - float(g)))
                                else:
                                    errors.append(abs(pred_val - gold_val))
                            except (ValueError, TypeError):
                                pass
                    
                    if errors:
                        mae = sum(errors) / len(errors)
                        rmse = (sum(e**2 for e in errors) / len(errors)) ** 0.5
                        
                        # Convert to score (0-100) using segmented scoring
                        # Similar to comprehensive_flight_evaluation_no_norm.py
                        mae_score = self._mae_to_score(mae)
                        rmse_score = self._rmse_to_score(rmse)
                        
                        # Combined error score (60% MAE + 40% RMSE)
                        conditional_error_score = mae_score * 0.6 + rmse_score * 0.4
        
        # If conditional_error_score not calculated, use constraint satisfaction as proxy
        if conditional_error_score is None:
            conditional_error_score = constraint_satisfaction_score
        
        # 4. Total Score
        # Use scoring_rules weights
        availability_weight = self.scoring_rules.get('availability_weight', 0.2)
        constraint_weight = self.scoring_rules.get('constraint_satisfaction_weight', 0.3)
        error_weight = self.scoring_rules.get('conditional_error_weight', 0.5)
        
        total_score = (
            availability_score * availability_weight +
            constraint_satisfaction_score * constraint_weight +
            conditional_error_score * error_weight
        )
        
        return {
            "availability_score": availability_score,
            "constraint_satisfaction_score": constraint_satisfaction_score,
            "conditional_error_score": conditional_error_score,
            "total_score": total_score
        }
    
    def _mae_to_score(self, mae: float) -> float:
        """
        Convert MAE to score (0-100) using segmented scoring
        
        Copied from comprehensive_flight_evaluation_no_norm.py
        """
        if mae < 5:
            return 100 - (mae / 5) * 10  # 90-100分
        elif mae < 20:
            return 90 - ((mae - 5) / 15) * 20  # 70-90分
        elif mae < 50:
            return 70 - ((mae - 20) / 30) * 20  # 50-70分
        elif mae < 100:
            return 50 - ((mae - 50) / 50) * 20  # 30-50分
        elif mae < 200:
            return 30 - ((mae - 100) / 100) * 15  # 15-30分
        else:
            return max(5, 15 - ((mae - 200) / 100) * 10)  # 5-15分
    
    def _rmse_to_score(self, rmse: float) -> float:
        """
        Convert RMSE to score (0-100) using segmented scoring
        
        Copied from comprehensive_flight_evaluation_no_norm.py
        """
        if rmse < 10:
            return 100 - (rmse / 10) * 10  # 90-100分
        elif rmse < 50:
            return 90 - ((rmse - 10) / 40) * 20  # 70-90分
        elif rmse < 100:
            return 70 - ((rmse - 50) / 50) * 20  # 50-70分
        elif rmse < 200:
            return 50 - ((rmse - 100) / 100) * 20  # 30-50分
        elif rmse < 300:
            return 30 - ((rmse - 200) / 100) * 15  # 15-30分
        else:
            return max(5, 15 - ((rmse - 300) / 100) * 10)  # 5-15分

