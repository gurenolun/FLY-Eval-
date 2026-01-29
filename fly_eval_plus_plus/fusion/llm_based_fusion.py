"""
LLM-Based Fusion

Fusion that uses LLM Judge output (grades) to compute final scores.
Replaces rule-based fusion with LLM-driven scoring.
"""

from typing import Dict, List, Any, Optional
from ..core.data_structures import EvidenceAtom, Record
from ..agents.llm_judge import LLMJudge, JudgeOutput
from ..rubric.rubric_definition import GRADE_SCORE_MAP, aggregate_grade_scores, Grade


class LLMBasedFusion:
    """
    LLM-based fusion aggregator
    
    Uses LLM Judge to output grades, then maps to scores using fixed protocol.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LLM-based fusion
        
        Args:
            config: Fusion protocol config with llm_judge config
        """
        self.config = config
        self.llm_judge = LLMJudge(config.get('llm_judge', {
            'model': 'gpt-4o',
            'temperature': 0,
            'api_key': None,
            'max_retries': 3
        }))
        self.gating_rules = config.get('gating_rules', {})
    
    def gate(self, evidence_atoms: List[EvidenceAtom]) -> tuple[bool, List[str]]:
        """
        Apply gating rules (same as rule-based, for consistency)
        
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
    
    def calculate_scores(self, record: Record, sample: Any = None, model_output: Any = None, 
                       context: Dict[str, Any] = None) -> Dict[str, float]:
        """
        Calculate scores from LLM Judge output
        
        Fixed protocol: LLM outputs grades → map to scores → aggregate
        
        Args:
            record: Record with evidence_pack
            sample: Sample object (optional, for error calculation)
            model_output: ModelOutput object (optional, for error calculation)
            context: Context dict with reference data (optional, for error calculation)
        
        Returns:
            Dict with dimension scores, overall_score, and LLM judge metadata
        """
        evidence_atoms = record.evidence_pack.get('atoms', [])
        protocol_result = record.protocol_result
        
        # Calculate conditional error if available
        conditional_error = None
        if sample and model_output and context:
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
                    mae_score = self._mae_to_score(mae)
                    rmse_score = self._rmse_to_score(rmse)
                    
                    conditional_error = {
                        "mae": mae,
                        "rmse": rmse,
                        "mae_score": mae_score,
                        "rmse_score": rmse_score,
                        "combined_score": mae_score * 0.6 + rmse_score * 0.4
                    }
        
        # Get task spec from context or config
        task_spec = context.get('task_spec', {}) if context else {}
        
        # Call LLM Judge (evidence-only, no raw response)
        judge_output = self.llm_judge.judge(
            evidence_atoms=evidence_atoms,
            protocol_result=protocol_result,
            task_spec=task_spec,
            conditional_error=conditional_error
        )
        
        # Map grades to scores using fixed protocol
        dimension_scores = {}
        for dimension, grade in judge_output.grade_vector.items():
            dimension_scores[dimension] = self.llm_judge.grade_to_score(grade)
        
        # Compute overall score using fixed aggregation protocol
        overall_score = self.llm_judge.compute_overall_score(judge_output)
        
        # Also compute availability and constraint satisfaction for backward compatibility
        # (These are still computed from evidence, but not used for final score)
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
                if atom.pass_:
                    passed_weight += weight
            
            if total_weight > 0:
                constraint_satisfaction_score = (passed_weight / total_weight) * 100.0
            else:
                constraint_satisfaction_score = 100.0
        
        # Conditional error score (from LLM judge's predictive quality dimension)
        predictive_quality_grade = judge_output.grade_vector.get('predictive_quality_reliability', 'D')
        conditional_error_score = self.llm_judge.grade_to_score(predictive_quality_grade) * 100.0
        
        return {
            # LLM Judge outputs (primary)
            "llm_judge_output": {
                "grade_vector": judge_output.grade_vector,
                "overall_grade": judge_output.overall_grade,
                "dimension_scores": dimension_scores,
                "overall_score": overall_score,
                "critical_findings": judge_output.critical_findings,
                "checklist": judge_output.checklist,
                "reasoning": judge_output.reasoning,
                "judge_metadata": judge_output.judge_metadata
            },
            # Legacy scores (for backward compatibility, not used for final ranking)
            "availability_score": availability_score,
            "constraint_satisfaction_score": constraint_satisfaction_score,
            "conditional_error_score": conditional_error_score,
            # Final score (from LLM Judge)
            "total_score": overall_score * 100.0  # Scale to 0-100
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

