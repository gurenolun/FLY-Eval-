"""
Test LLM Judge

Test script for LLM Judge functionality.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fly_eval_plus_plus.agents.llm_judge import LLMJudge
from fly_eval_plus_plus.core.data_structures import EvidenceAtom, Severity, Scope
from fly_eval_plus_plus.rubric.rubric_definition import Dimension, Grade


def create_test_evidence_atoms() -> list[EvidenceAtom]:
    """Create test evidence atoms"""
    evidence = []
    
    # Protocol/Schema: All pass
    evidence.append(EvidenceAtom(
        id="EVID_001",
        type="numeric_validity",
        field="GPS Altitude (WGS84 ft)",
        pass_=True,
        severity=Severity.INFO,
        scope=Scope.FIELD,
        message="Field is valid",
        meta={"checker": "NumericValidityChecker", "rule": "NaN_Check"}
    ))
    
    # Field Validity: Minor warning
    evidence.append(EvidenceAtom(
        id="EVID_002",
        type="range_sanity",
        field="GPS Ground Speed (kt)",
        pass_=False,
        severity=Severity.WARNING,
        scope=Scope.FIELD,
        message="Value slightly outside normal range",
        meta={"checker": "RangeSanityChecker", "rule": "Range_Check", "threshold": 500, "actual_value": 520}
    ))
    
    # Physics Consistency: Pass
    evidence.append(EvidenceAtom(
        id="EVID_003",
        type="cross_field_consistency",
        field="GPS Altitude (WGS84 ft), Baro Altitude (ft)",
        pass_=True,
        severity=Severity.INFO,
        scope=Scope.CROSS_FIELD,
        message="Altitudes are consistent",
        meta={"checker": "CrossFieldConsistencyChecker", "rule": "GPS_Alt_vs_Baro_Alt"}
    ))
    
    # Safety: Pass
    evidence.append(EvidenceAtom(
        id="EVID_004",
        type="safety_constraint",
        field="Vertical Speed (fpm)",
        pass_=True,
        severity=Severity.INFO,
        scope=Scope.SAMPLE,
        message="No safety violations",
        meta={"checker": "SafetyConstraintChecker", "rule": "Rapid_Descent"}
    ))
    
    return evidence


def test_llm_judge():
    """Test LLM Judge"""
    print("=" * 80)
    print("Testing LLM Judge")
    print("=" * 80)
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  Warning: OPENAI_API_KEY not set. Using placeholder.")
        print("   Set it with: export OPENAI_API_KEY=your_key")
        api_key = None
    
    # Initialize LLM Judge
    config = {
        "model": "gpt-4o",
        "temperature": 0,
        "api_key": api_key,
        "max_retries": 3
    }
    
    judge = LLMJudge(config)
    
    # Create test evidence
    evidence_atoms = create_test_evidence_atoms()
    
    # Protocol result
    protocol_result = {
        "parsing": {
            "success": True,
            "error": None
        },
        "field_completeness": {
            "completeness_rate": 1.0,
            "missing_fields": []
        }
    }
    
    # Task spec
    task_spec = {
        "name": "Next Second Prediction",
        "output_schema": {},
        "protocol": "single_value"
    }
    
    # Conditional error (optional)
    conditional_error = {
        "mae": 10.5,
        "rmse": 15.2,
        "mae_score": 85.0,
        "rmse_score": 82.0,
        "combined_score": 83.8
    }
    
    print("\n📊 Test Evidence:")
    print(f"  Total evidence atoms: {len(evidence_atoms)}")
    for atom in evidence_atoms:
        status = "✅" if atom.pass_ else "❌"
        print(f"  {status} {atom.id}: {atom.type} - {atom.message}")
    
    print("\n🔍 Calling LLM Judge...")
    
    try:
        # Call LLM Judge
        judge_output = judge.judge(
            evidence_atoms=evidence_atoms,
            protocol_result=protocol_result,
            task_spec=task_spec,
            conditional_error=conditional_error
        )
        
        print("\n✅ LLM Judge Output:")
        print(f"  Overall Grade: {judge_output.overall_grade}")
        print(f"\n  Dimension Grades:")
        for dimension, grade in judge_output.grade_vector.items():
            score = judge.grade_to_score(grade)
            print(f"    {dimension}: {grade} (score: {score:.2f})")
        
        print(f"\n  Overall Score: {judge.compute_overall_score(judge_output):.2f}")
        
        print(f"\n  Critical Findings: {len(judge_output.critical_findings)}")
        for finding in judge_output.critical_findings[:3]:
            print(f"    - {finding.get('reason', 'N/A')} (evidence: {finding.get('evidence_ids', [])})")
        
        print(f"\n  Checklist Items: {len(judge_output.checklist)}")
        for item in judge_output.checklist[:3]:
            print(f"    - {item.get('description', 'N/A')} ({item.get('status', 'N/A')})")
        
        print(f"\n  Reasoning: {judge_output.reasoning[:200]}...")
        
        print(f"\n  Judge Metadata:")
        print(f"    Model: {judge_output.judge_metadata.get('model')}")
        print(f"    Temperature: {judge_output.judge_metadata.get('temperature')}")
        print(f"    Prompt Hash: {judge_output.judge_metadata.get('prompt_hash')}")
        
        print("\n✅ LLM Judge test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print("\n⚠️  Note: If this is an API error, make sure:")
        print("  1. OPENAI_API_KEY is set")
        print("  2. OpenAI library is installed: pip install openai")
        print("  3. You have API credits")


if __name__ == "__main__":
    test_llm_judge()

