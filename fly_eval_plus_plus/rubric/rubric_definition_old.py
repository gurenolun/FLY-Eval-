"""
FLY-EVAL++ Rubric Definition

5-dimensional rubric with 4-grade levels (A/B/C/D) for LLM Judge.
Each grade level has explicit conditions based on evidence atoms.
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


# Rubric definition: 5 dimensions × 4 grades
RUBRIC = {
    Dimension.PROTOCOL_SCHEMA: {
        Grade.A: {
            "condition": "No protocol failures. All required fields present. JSON parsing successful.",
            "evidence_requirements": {
                "numeric_validity": {"max_critical": 0, "max_warning": 0},
                "parsing": {"success": True},
                "field_completeness": {"rate": 1.0}
            },
            "description": "Perfect protocol compliance"
        },
        Grade.B: {
            "condition": "Minor protocol issues. All required fields present. JSON parsing successful.",
            "evidence_requirements": {
                "numeric_validity": {"max_critical": 0, "max_warning": 1},
                "parsing": {"success": True},
                "field_completeness": {"rate": 1.0}
            },
            "description": "Good protocol compliance with minor issues"
        },
        Grade.C: {
            "condition": "Moderate protocol issues. Most required fields present. JSON parsing successful.",
            "evidence_requirements": {
                "numeric_validity": {"max_critical": 0, "max_warning": 3},
                "parsing": {"success": True},
                "field_completeness": {"rate": 0.9}
            },
            "description": "Acceptable protocol compliance"
        },
        Grade.D: {
            "condition": "Severe protocol failures. Missing required fields or JSON parsing failed.",
            "evidence_requirements": {
                "numeric_validity": {"max_critical": 1},  # Any critical failure
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
                "range_sanity": {"max_critical": 0, "max_warning": 0},
                "jump_dynamics": {"max_critical": 0, "max_warning": 0}
            },
            "description": "Perfect field validity and local dynamics"
        },
        Grade.B: {
            "condition": "Minor range or jump violations. Most fields valid.",
            "evidence_requirements": {
                "range_sanity": {"max_critical": 0, "max_warning": 2},
                "jump_dynamics": {"max_critical": 0, "max_warning": 2}
            },
            "description": "Good field validity with minor issues"
        },
        Grade.C: {
            "condition": "Moderate range or jump violations. Some fields invalid.",
            "evidence_requirements": {
                "range_sanity": {"max_critical": 0, "max_warning": 5},
                "jump_dynamics": {"max_critical": 0, "max_warning": 5}
            },
            "description": "Acceptable field validity"
        },
        Grade.D: {
            "condition": "Severe range or jump violations. Multiple fields invalid.",
            "evidence_requirements": {
                "range_sanity": {"max_critical": 1},  # Any critical failure
                "jump_dynamics": {"max_critical": 1}  # OR any critical jump violation
            },
            "description": "Poor field validity"
        }
    },
    
    Dimension.PHYSICS_CONSISTENCY: {
        Grade.A: {
            "condition": "Perfect cross-field consistency. All physics constraints satisfied.",
            "evidence_requirements": {
                "cross_field_consistency": {"max_critical": 0, "max_warning": 0},
                "physics_constraint": {"max_critical": 0, "max_warning": 0}
            },
            "description": "Perfect physics and cross-field consistency"
        },
        Grade.B: {
            "condition": "Minor cross-field or physics violations. Most constraints satisfied.",
            "evidence_requirements": {
                "cross_field_consistency": {"max_critical": 0, "max_warning": 2},
                "physics_constraint": {"max_critical": 0, "max_warning": 2}
            },
            "description": "Good physics consistency with minor issues"
        },
        Grade.C: {
            "condition": "Moderate cross-field or physics violations. Some constraints violated.",
            "evidence_requirements": {
                "cross_field_consistency": {"max_critical": 0, "max_warning": 5},
                "physics_constraint": {"max_critical": 0, "max_warning": 5}
            },
            "description": "Acceptable physics consistency"
        },
        Grade.D: {
            "condition": "Severe cross-field or physics violations. Critical constraints violated.",
            "evidence_requirements": {
                "cross_field_consistency": {"max_critical": 1},  # Any critical failure
                "physics_constraint": {"max_critical": 1}  # OR any critical physics violation
            },
            "description": "Poor physics consistency"
        }
    },
    
    Dimension.SAFETY_CONSTRAINT: {
        Grade.A: {
            "condition": "No safety violations. All safety constraints satisfied.",
            "evidence_requirements": {
                "safety_constraint": {"max_critical": 0, "max_warning": 0}
            },
            "description": "Perfect safety compliance"
        },
        Grade.B: {
            "condition": "Minor safety warnings. No critical safety violations.",
            "evidence_requirements": {
                "safety_constraint": {"max_critical": 0, "max_warning": 1}
            },
            "description": "Good safety compliance with minor warnings"
        },
        Grade.C: {
            "condition": "Moderate safety warnings. No critical safety violations.",
            "evidence_requirements": {
                "safety_constraint": {"max_critical": 0, "max_warning": 3}
            },
            "description": "Acceptable safety compliance"
        },
        Grade.D: {
            "condition": "Critical safety violations detected.",
            "evidence_requirements": {
                "safety_constraint": {"max_critical": 1}  # Any critical safety violation
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
            "condition": "Good predictive quality. Moderate error (nMAE < 20, nRMSE < 50). Acceptable reliability.",
            "evidence_requirements": {
                "conditional_error": {"mae_score": 70, "rmse_score": 70},
                "reliability": {"high": False, "acceptable": True}
            },
            "description": "Good predictive quality"
        },
        Grade.C: {
            "condition": "Acceptable predictive quality. Higher error (nMAE < 50, nRMSE < 100). Low reliability.",
            "evidence_requirements": {
                "conditional_error": {"mae_score": 50, "rmse_score": 50},
                "reliability": {"acceptable": True}
            },
            "description": "Acceptable predictive quality"
        },
        Grade.D: {
            "condition": "Poor predictive quality. High error (nMAE >= 50, nRMSE >= 100). Low reliability.",
            "evidence_requirements": {
                "conditional_error": {"mae_score": 50},  # Below acceptable threshold
                "reliability": {"acceptable": False}
            },
            "description": "Poor predictive quality"
        }
    }
}


# Monotonicity sanity checks (hard rules)
MONOTONICITY_CHECKS = {
    "protocol_fail_blocks_high_grade": {
        "condition": "If protocol fails (parsing failed OR critical numeric validity), Protocol dimension cannot be A or B",
        "check": lambda evidence_summary, grade: (
            not (evidence_summary.get("parsing", {}).get("success", True) == False or
                 evidence_summary.get("numeric_validity", {}).get("critical_count", 0) > 0) or
            grade not in [Grade.A, Grade.B]
        )
    },
    "safety_critical_blocks_high_grade": {
        "condition": "If safety has critical violation, Safety dimension cannot be A or B",
        "check": lambda evidence_summary, grade: (
            not (evidence_summary.get("safety_constraint", {}).get("critical_count", 0) > 0) or
            grade not in [Grade.A, Grade.B]
        )
    },
    "high_error_blocks_high_quality_grade": {
        "condition": "If nMAE/nRMSE extremely poor and shows overconfidence, Quality dimension cannot be A",
        "check": lambda evidence_summary, grade: (
            not (evidence_summary.get("conditional_error", {}).get("mae_score", 100) < 50 and
                 evidence_summary.get("reliability", {}).get("overconfident", False)) or
            grade != Grade.A
        )
    }
}


def get_rubric_text() -> str:
    """Get rubric as text for LLM prompt"""
    lines = []
    lines.append("FLY-EVAL++ Evaluation Rubric")
    lines.append("=" * 80)
    lines.append("")
    
    for dim in Dimension:
        lines.append(f"## {dim.value.replace('_', ' ').title()}")
        lines.append("")
        for grade in [Grade.A, Grade.B, Grade.C, Grade.D]:
            rubric_entry = RUBRIC[dim][grade]
            lines.append(f"**{grade.value}**: {rubric_entry['description']}")
            lines.append(f"  Condition: {rubric_entry['condition']}")
            lines.append(f"  Evidence Requirements: {rubric_entry['evidence_requirements']}")
            lines.append("")
    
    return "\n".join(lines)


def get_evidence_atom_fields() -> Dict[str, Any]:
    """
    Return EvidenceAtom field definitions for LLM Judge
    
    This helps LLM understand what evidence is available.
    """
    return {
        "id": "Unique evidence ID (e.g., 'EVID_001')",
        "type": "Verifier type: numeric_validity, range_sanity, jump_dynamics, cross_field_consistency, physics_constraint, safety_constraint",
        "field": "Field name if field-level check (e.g., 'GPS Altitude (WGS84 ft)')",
        "pass_": "Boolean: True if check passed, False if failed",
        "severity": "Severity level: critical, warning, info",
        "scope": "Scope: field, sample, cross_field",
        "message": "Human-readable message describing the check result",
        "meta": {
            "checker": "Checker name (e.g., 'NumericValidityChecker')",
            "rule": "Specific rule name (e.g., 'NaN_Check', 'Range_Check')",
            "threshold": "Threshold value if applicable",
            "actual_value": "Actual value if applicable"
        }
    }


def get_verifier_families() -> List[str]:
    """Return list of verifier families (for LLM to understand available checks)"""
    return [
        "NumericValidityChecker",
        "RangeSanityChecker", 
        "JumpDynamicsChecker",
        "CrossFieldConsistencyChecker",
        "PhysicsConstraintChecker",
        "SafetyConstraintChecker"
    ]

