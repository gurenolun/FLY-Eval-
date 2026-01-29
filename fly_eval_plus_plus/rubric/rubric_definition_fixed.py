"""
FLY-EVAL++ Rubric Definition (FIXED - Using Ratio Thresholds)

5-dimensional rubric with 4-grade levels (A/B/C/D) for LLM Judge.
Each grade level has explicit conditions based on evidence atoms.

修复: 使用比例阈值而非绝对数量阈值
"""

from typing import Dict, List, Any
from enum import Enum


class Grade(str, Enum):
    """Grade levels"""
    A = "A"  # Excellent
    B = "B"  # Good
    C = "C"  # Acceptable
    D = "D"  # Poor/Failed


class Dimension(str, Enum):
    """Evaluation dimensions"""
    PROTOCOL_SCHEMA = "protocol_schema_compliance"
    FIELD_VALIDITY = "field_validity_local_dynamics"
    PHYSICS_CONSISTENCY = "physics_cross_field_consistency"
    SAFETY_CONSTRAINT = "safety_constraint_satisfaction"
    PREDICTIVE_QUALITY = "predictive_quality_reliability"


# Grade to score mapping (fixed protocol, no manual weights)
GRADE_SCORE_MAP = {
    Grade.A: 1.0,
    Grade.B: 0.75,
    Grade.C: 0.5,
    Grade.D: 0.0
}


# Overall score aggregation (fixed protocol)
def aggregate_grade_scores(grade_scores: List[float]) -> float:
    """
    Aggregate grade scores to overall score
    
    Fixed protocol: arithmetic mean (can be changed to geometric mean if needed)
    """
    if not grade_scores:
        return 0.0
    return sum(grade_scores) / len(grade_scores)


# Rubric definition: 5 dimensions × 4 grades (FIXED - Using Ratio Thresholds)
RUBRIC = {
    Dimension.PROTOCOL_SCHEMA: {
        Grade.A: {
            "condition": "No protocol failures. All required fields present. JSON parsing successful.",
            "evidence_requirements": {
                "numeric_validity": {"max_failure_rate": 0.0},  # ✅ 0% 失败率
                "parsing": {"success": True},
                "field_completeness": {"rate": 1.0}
            },
            "description": "Perfect protocol compliance"
        },
        Grade.B: {
            "condition": "Minor protocol issues. All required fields present. JSON parsing successful.",
            "evidence_requirements": {
                "numeric_validity": {"max_failure_rate": 0.05},  # ✅ ≤5% 失败率
                "parsing": {"success": True},
                "field_completeness": {"rate": 1.0}
            },
            "description": "Good protocol compliance with minor issues"
        },
        Grade.C: {
            "condition": "Moderate protocol issues. Most required fields present. JSON parsing successful.",
            "evidence_requirements": {
                "numeric_validity": {"max_failure_rate": 0.15},  # ✅ ≤15% 失败率
                "parsing": {"success": True},
                "field_completeness": {"rate": 0.9}
            },
            "description": "Acceptable protocol compliance"
        },
        Grade.D: {
            "condition": "Severe protocol failures. Missing required fields or JSON parsing failed.",
            "evidence_requirements": {
                "numeric_validity": {"max_failure_rate": 1.0},  # ✅ >15% 失败率
                "parsing": {"success": False},  # OR parsing failed
                "field_completeness": {"rate": 0.8}  # OR completeness < 0.8
            },
            "description": "Poor protocol compliance"
        }
    },
    
    Dimension.FIELD_VALIDITY: {
        Grade.A: {
            "condition": "All fields valid. No range violations. No jump/mutation violations.",
            "evidence_requirements": {
                "range_sanity": {"max_failure_rate": 0.0},  # ✅ 0% 失败率
                "jump_dynamics": {"max_failure_rate": 0.0}  # ✅ 0% 失败率
            },
            "description": "Perfect field validity and local dynamics"
        },
        Grade.B: {
            "condition": "Minor range or jump violations. Most fields valid.",
            "evidence_requirements": {
                "range_sanity": {"max_failure_rate": 0.05},  # ✅ ≤5% 失败率
                "jump_dynamics": {"max_failure_rate": 0.05}  # ✅ ≤5% 失败率
            },
            "description": "Good field validity with minor issues"
        },
        Grade.C: {
            "condition": "Moderate range or jump violations. Some fields invalid.",
            "evidence_requirements": {
                "range_sanity": {"max_failure_rate": 0.15},  # ✅ ≤15% 失败率
                "jump_dynamics": {"max_failure_rate": 0.15}  # ✅ ≤15% 失败率
            },
            "description": "Acceptable field validity"
        },
        Grade.D: {
            "condition": "Severe range or jump violations. Multiple fields invalid.",
            "evidence_requirements": {
                "range_sanity": {"max_failure_rate": 1.0},  # ✅ >15% 失败率
                "jump_dynamics": {"max_failure_rate": 1.0}  # ✅ >15% 失败率
            },
            "description": "Poor field validity"
        }
    },
    
    Dimension.PHYSICS_CONSISTENCY: {
        Grade.A: {
            "condition": "Perfect cross-field consistency. All physics constraints satisfied.",
            "evidence_requirements": {
                "cross_field_consistency": {"max_failure_rate": 0.0},  # ✅ 0% 失败率
                "physics_constraint": {"max_failure_rate": 0.0}  # ✅ 0% 失败率
            },
            "description": "Perfect physics and cross-field consistency"
        },
        Grade.B: {
            "condition": "Minor cross-field or physics violations. Most constraints satisfied.",
            "evidence_requirements": {
                "cross_field_consistency": {"max_failure_rate": 0.10},  # ✅ ≤10% 失败率
                "physics_constraint": {"max_failure_rate": 0.10}  # ✅ ≤10% 失败率
            },
            "description": "Good physics consistency with minor issues"
        },
        Grade.C: {
            "condition": "Moderate cross-field or physics violations. Some constraints violated.",
            "evidence_requirements": {
                "cross_field_consistency": {"max_failure_rate": 0.25},  # ✅ ≤25% 失败率
                "physics_constraint": {"max_failure_rate": 0.25}  # ✅ ≤25% 失败率
            },
            "description": "Acceptable physics consistency"
        },
        Grade.D: {
            "condition": "Severe cross-field or physics violations. Critical constraints violated.",
            "evidence_requirements": {
                "cross_field_consistency": {"max_failure_rate": 1.0},  # ✅ >25% 失败率
                "physics_constraint": {"max_failure_rate": 1.0}  # ✅ >25% 失败率
            },
            "description": "Poor physics consistency"
        }
    },
    
    Dimension.SAFETY_CONSTRAINT: {
        Grade.A: {
            "condition": "No safety violations. All safety constraints satisfied.",
            "evidence_requirements": {
                "safety_constraint": {"max_failure_rate": 0.0}  # ✅ 0% 失败率
            },
            "description": "Perfect safety compliance"
        },
        Grade.B: {
            "condition": "Minor safety warnings. No critical safety violations.",
            "evidence_requirements": {
                "safety_constraint": {"max_failure_rate": 0.10}  # ✅ ≤10% 失败率
            },
            "description": "Good safety compliance with minor warnings"
        },
        Grade.C: {
            "condition": "Moderate safety warnings. No critical safety violations.",
            "evidence_requirements": {
                "safety_constraint": {"max_failure_rate": 0.25}  # ✅ ≤25% 失败率
            },
            "description": "Acceptable safety compliance"
        },
        Grade.D: {
            "condition": "Critical safety violations detected.",
            "evidence_requirements": {
                "safety_constraint": {"max_failure_rate": 1.0}  # ✅ >25% 失败率
            },
            "description": "Poor safety compliance"
        }
    },
    
    Dimension.PREDICTIVE_QUALITY: {
        Grade.A: {
            "condition": "Excellent predictive quality. Low error (nMAE < 5, nRMSE < 10). High reliability.",
            "evidence_requirements": {
                "conditional_error": {"mae_score": 90, "rmse_score": 90},  # High scores
                "reliability": {"high": True}  # If available
            },
            "description": "Excellent predictive quality and reliability"
        },
        Grade.B: {
            "condition": "Good predictive quality. Moderate error (5 ≤ nMAE < 20, 10 ≤ nRMSE < 50). Good reliability.",
            "evidence_requirements": {
                "conditional_error": {"mae_score": 70, "rmse_score": 70},
                "reliability": {"acceptable": True}
            },
            "description": "Good predictive quality and reliability"
        },
        Grade.C: {
            "condition": "Acceptable predictive quality. Higher error (20 ≤ nMAE < 50, 50 ≤ nRMSE < 100). Acceptable reliability.",
            "evidence_requirements": {
                "conditional_error": {"mae_score": 50, "rmse_score": 50},
                "reliability": {"min": True}
            },
            "description": "Acceptable predictive quality"
        },
        Grade.D: {
            "condition": "Poor predictive quality. High error (nMAE ≥ 50, nRMSE ≥ 100). Low reliability.",
            "evidence_requirements": {
                "conditional_error": {"mae_score": 0, "rmse_score": 0},  # Any low score
                "reliability": {"none": True}
            },
            "description": "Poor predictive quality"
        }
    }
}
