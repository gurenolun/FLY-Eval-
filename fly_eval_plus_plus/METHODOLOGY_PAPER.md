# FLY-EVAL++ Methodology for Paper

**Version**: v1.0.0  
**Date**: 2025-01-19

---

## 1. Overview

FLY-EVAL++ is an evidence-driven evaluation framework for safety-constrained embodied contexts. It models evaluation as "evidence-traceable adjudication" with LLM as an evaluator agent.

### Core Principles

1. **Evidence-First**: All objectively computable aspects (format/field validity/physical & safety constraints/error metrics) are computed offline to form an evidence pack.
2. **Clear LLM Responsibilities**: LLM only does three things: generate executable checklist, organize tool verification workflow, and output adjudication & attribution based on evidence.
3. **Optional and Reproducible Scoring**: If leaderboard total score is needed, use fixed-protocol aggregator (rule-based).
4. **Model-Level Confidence as Prior**: Model-level confidence does not enter sample-level adjudication, but serves as an independent dimension of model profile.

---

## 2. Data Structures

### 2.1 EvidenceAtom

**Definition**: Atomic evidence unit - the fundamental building block of evidence pack.

```python
EvidenceAtom {
    id: str                    # Unique evidence ID, e.g., "EVID_001"
    type: str                  # Verifier type: "numeric_validity", "range_sanity", 
                               # "jump_dynamics", "cross_field_consistency", 
                               # "physics_constraint", "safety_constraint"
    field: Optional[str]       # Field name if field-level check
    pass: bool                 # Verification result (True/False)
    severity: Severity         # CRITICAL, WARNING, or INFO
    scope: Scope               # FIELD, SAMPLE, or CROSS_FIELD
    message: str               # Human-readable message
    meta: Dict[str, Any]       # Checker name, timestamp, config version, thresholds
}
```

**Severity Levels**:
- `CRITICAL`: Severe violations (>threshold×1.5 or critical safety risks)
- `WARNING`: Warning violations (>threshold but <threshold×1.5)
- `INFO`: Passed checks

### 2.2 Sample

**Definition**: Sample-level input.

```python
Sample {
    sample_id: str             # Unique sample identifier
    task_id: str               # "S1", "M1", or "M3"
    context: Dict[str, Any]    # question, current_state, record_idx
    gold: Dict[str, Any]       # next_second or T+1, available flag
}
```

### 2.3 ModelOutput

**Definition**: Model output.

```python
ModelOutput {
    model_name: str            # Model identifier
    sample_id: str             # Matches Sample.sample_id
    raw_response_text: str      # Raw model response
    timestamp: str             # Response timestamp
    task_id: str               # Matches Sample.task_id
}
```

### 2.4 Record

**Definition**: Sample-level output - the most important deliverable.

```python
Record {
    sample_id: str
    model_name: str
    task_id: str
    protocol_result: Dict      # Parsing, field_completeness, type_validation
    evidence_pack: Dict        # {"atoms": List[EvidenceAtom]}
    agent_output: Dict         # checklist, adjudication, attribution
    optional_scores: Dict      # availability_score, constraint_satisfaction_score,
                               # conditional_error_score, total_score
    trace: Dict                # config_version, config_hash, schema_version,
                               # constraint_lib_version, timestamp, reproducibility_info
}
```

### 2.5 ModelConfidence

**Definition**: Model-level confidence prior (does not enter sample-level adjudication).

```python
ModelConfidence {
    model_name: str
    confidence_m: Dict         # {"S1_score": float, "M1_score": float, "M3_score": float}
    calculation_source: str    # Source script name
    version: str               # Calculation version
    metadata: Dict             # Calculation method, date, etc.
}
```

---

## 3. Verifier Graph

### 3.1 Verifier Base Class

All checks are implemented as verifier nodes in a DAG, each outputting `EvidenceAtom`.

```python
class Verifier(ABC):
    def verify(sample, model_output, context) -> List[EvidenceAtom]:
        """
        Perform verification and return evidence atoms.
        Each verifier checks specific constraints and outputs evidence.
        """
        pass
```

### 3.2 Verifier Types

**1. NumericValidityChecker**
- Checks: NaN, Inf, type validity, missing values
- Output: EvidenceAtom for each field (even if passing)

**2. RangeSanityChecker**
- Checks: Field values within valid ranges (using FIELD_LIMITS)
- Output: EvidenceAtom with severity based on deviation magnitude

**3. JumpDynamicsChecker**
- Checks: Mutation violations (using JUMP_THRESHOLDS)
- Handles: M3 array internal mutations, S1/M1 sequential mutations
- Special: Angle fields use shortest arc difference

**4. CrossFieldConsistencyChecker**
- Rules:
  - GPS Altitude vs Baro Altitude consistency (threshold: 500ft/1000ft)
  - Ground Speed vs Velocity components consistency (threshold: 5kt/15kt)
  - Track vs Vn/Ve direction consistency (threshold: 10deg/30deg)

**5. PhysicsConstraintChecker**
- Rules:
  - M3 array internal continuity/reachability
  - Velocity-altitude consistency
  - Attitude-velocity consistency

**6. SafetyConstraintChecker**
- Rules:
  - Rapid descent detection (threshold: -2000fpm/-3000fpm)
  - Extreme speed/altitude detection
  - Stall condition detection

### 3.3 Verifier Graph Execution

```python
class VerifierGraph:
    def execute(sample, model_output, context) -> List[EvidenceAtom]:
        """
        Execute all verifiers in dependency order (topological sort).
        Collect all evidence atoms.
        """
        all_evidence = []
        # Execute verifiers in dependency order
        # Return combined evidence atoms
        return all_evidence
```

---

## 4. Evaluator Agent

### 4.1 Agent Responsibilities

The evaluator agent (rule-based version) performs three tasks:

1. **Generate Executable Checklist**: Decompose "comprehensive judgment" into verifiable items, each binding to constraint_id/evidence_id.
2. **Organize Tool Verification Workflow**: Map checklist items to evidence atoms, update status (pass/fail/unknown).
3. **Output Adjudication and Attribution**: Based on evidence, output eligible/ineligible with Top-K failure reasons (must cite evidence IDs).

### 4.2 Checklist Generation

```python
def generate_checklist(task_spec, verifier_capabilities) -> List[Dict]:
    """
    Generate rule-based checklist.
    Each item has: item_id, constraint_id, evidence_id, status
    """
    checklist = []
    for capability in verifier_capabilities:
        checklist.append({
            "item_id": f"CHECK_{i:03d}",
            "constraint_id": map_to_constraint_id(capability),
            "evidence_id": None,  # Filled after verification
            "status": "unknown"   # Updated based on evidence
        })
    return checklist
```

### 4.3 Adjudication

```python
def adjudicate(evidence_atoms, checklist) -> Dict:
    """
    Output adjudication and attribution based on evidence.
    Must cite evidence IDs.
    """
    # Check for critical failures (gating rules)
    critical_failures = [e for e in evidence_atoms 
                        if e.severity == CRITICAL and not e.pass_]
    
    # Determine adjudication
    adjudication = ELIGIBLE if len(critical_failures) == 0 else INELIGIBLE
    
    # Generate Top-K attribution
    attribution = []
    for failure in all_failures[:5]:  # Top 5
        attribution.append({
            "reason": failure.message,
            "evidence_ids": [failure.id],
            "severity": failure.severity.value,
            "rank": i
        })
    
    return {
        "adjudication": adjudication.value,
        "attribution": attribution
    }
```

**Note**: The agent's role is **evidence orchestration and adjudication/attribution**, not "subjective scoring". The rule-based checklist version is one instantiation of the agent methodology.

---

## 5. Rule-Based Fusion

### 5.1 Gating Rules

Protocol/key safety constraint failures → ineligible with explicit upper limit/grade.

```python
def gate(evidence_atoms) -> Tuple[bool, List[str]]:
    """
    Apply gating rules.
    Returns: (passed_gating, gating_reasons)
    """
    # Check for critical failures
    critical_failures = [e for e in evidence_atoms 
                        if e.severity == CRITICAL and not e.pass_]
    
    if critical_failures:
        return False, [f"Found {len(critical_failures)} critical violations"]
    return True, []
```

### 5.2 Scoring Protocol

For eligible outputs, calculate sub-scores and total score using fixed protocol.

**Sub-Scores**:
1. **Availability Score (0-100)**: Based on field completeness rate
2. **Constraint Satisfaction Score (0-100)**: Based on evidence atoms, weighted by severity
   - Severity weights: CRITICAL=3.0, WARNING=1.0, INFO=0.5
3. **Conditional Error Score (0-100)**: Based on MAE/RMSE using segmented scoring

**Total Score**:
```
Total Score = Availability × 0.2 + Constraint Satisfaction × 0.3 + Conditional Error × 0.5
```

**Rationale**: The fixed weights (0.2:0.3:0.5) emphasize conditional error (accuracy) while maintaining balance with availability and constraint satisfaction. The paper also provides weight-free profiles (availability rate, violation rates, tail risk, conditional error) as supporting analysis.

---

## 6. Failure Taxonomy

### 6.1 Failure Modes

Based on evidence atom types and attribution:

1. **Numeric Validity Failures**
   - Missing fields
   - Invalid numeric values (NaN, Inf, type errors)

2. **Range Sanity Failures**
   - Values out of valid range
   - Severity based on deviation magnitude

3. **Jump Dynamics Failures**
   - Mutation violations (exceeding thresholds)
   - Array internal continuity violations (M3)

4. **Cross-Field Consistency Failures**
   - GPS Alt vs Baro Alt inconsistency
   - Ground Speed vs Velocity inconsistency
   - Track vs Velocity direction inconsistency

5. **Physics Constraint Failures**
   - M3 array continuity violations
   - Velocity-altitude inconsistency
   - Attitude-velocity inconsistency

6. **Safety Constraint Failures**
   - Rapid descent
   - Extreme speed/altitude
   - Stall-like conditions

### 6.2 Severity Classification

- **CRITICAL**: Protocol failures, safety risks, severe violations (>threshold×1.5)
- **WARNING**: Moderate violations (>threshold but <threshold×1.5)
- **INFO**: Passed checks (recorded for completeness)

---

## 7. Reproducibility and Trace

### 7.1 Version Locking

Each `Record` contains a `trace` field with:

```python
trace = {
    "config_version": "1.0.0",
    "config_hash": "81a5aef9181612b0",      # SHA256 hash of config
    "schema_version": "701d05763ec09361",    # SHA256 hash of schema
    "constraint_lib_version": "1552a46f1a440793",  # SHA256 hash of constraint_lib
    "evaluator_version": "1.0.0",
    "timestamp": "2025-01-19T10:30:00",
    "reproducibility_info": {
        "model": "gpt-4o",
        "temperature": 0,
        "verifier_count": 6,
        "verifier_ids": [...]
    }
}
```

### 7.2 Reproducibility Guarantee

- **Config Hash**: Detects configuration changes
- **Schema Version**: Detects schema definition changes
- **Constraint Lib Version**: Detects constraint library changes
- **Timestamp**: Evaluation execution time
- **Reproducibility Info**: Model and verifier configuration

To reproduce results, ensure:
1. Same config_hash
2. Same schema_version
3. Same constraint_lib_version
4. Same verifier configuration

---

## 8. Algorithm Pseudocode

### 8.1 Main Evaluation Algorithm

```
Algorithm: FLY-EVAL++ Evaluation
Input: Sample, ModelOutput, ModelConfidence (optional)
Output: Record

1. Parse JSON from ModelOutput.raw_response_text
2. Build context: {json_data, task_type, required_fields, previous_predictions}
3. Execute VerifierGraph → collect all EvidenceAtoms
4. Agent generates checklist from verifier capabilities
5. Agent organizes workflow: map checklist to evidence atoms
6. Agent adjudicates: eligible/ineligible + Top-K attribution
7. Apply gating rules
8. If passed gating:
     Calculate scores (availability, constraint_satisfaction, conditional_error)
     Total score = weighted sum (0.2:0.3:0.5)
9. Build Record with:
     - protocol_result
     - evidence_pack (all atoms)
     - agent_output (checklist, adjudication, attribution)
     - optional_scores
     - trace (version info)
10. Return Record
```

### 8.2 Task Summary Generation

```
Algorithm: Generate Task Summary
Input: List[Record], task_id
Output: TaskSummary

1. Calculate eligibility statistics
2. Calculate availability rate (field completeness)
3. Calculate compliance rates by constraint type
4. Build constraint satisfaction profile
5. Calculate conditional error statistics (eligible samples only)
6. Calculate tail risk (P95, P99, exceedance rates)
7. Analyze failure mode distribution
8. Return TaskSummary
```

### 8.3 Model Profile Generation

```
Algorithm: Generate Model Profile
Input: List[Record], ModelConfidence
Output: ModelProfile

1. Aggregate data-driven profile:
   - Eligibility rate
   - Score statistics (availability, constraint, error, total)
   - Constraint violations
   - Failure modes
   - Conditional error distribution
   - Tail risk metrics
2. Include model confidence prior (separate from data-driven)
3. Calculate optional total score
4. Return ModelProfile
```

---

## 9. Evidence Atom Naming Convention

**Format**: `constraint.<family>.<rule>`

**Examples**:
- `numeric_validity.missing_field`
- `numeric_validity.invalid_value`
- `range_sanity.out_of_range`
- `jump_dynamics.mutation_violation`
- `cross_field_consistency.altitude_consistency`
- `cross_field_consistency.speed_consistency`
- `cross_field_consistency.track_consistency`
- `physics_constraint.m3_array_continuity`
- `physics_constraint.velocity_altitude_consistency`
- `safety_constraint.rapid_descent`
- `safety_constraint.extreme_speed`
- `safety_constraint.stall_condition`

---

## 10. Fixed Protocol Weights

**Scoring Weights**:
- Availability: 0.2
- Constraint Satisfaction: 0.3
- Conditional Error: 0.5

**Rationale**: 
- Emphasizes conditional error (accuracy) as primary metric
- Maintains balance with availability and constraint satisfaction
- Paper provides weight-free profiles as supporting analysis

**Supporting Analysis** (weight-free):
- Availability rate distribution
- Constraint violation rates
- Tail risk metrics (P95, P99, exceedance rates)
- Conditional error distribution
- Failure mode distribution

These profiles allow readers to understand model performance beyond the single total score.

---

## 11. Agent Methodology Explanation

### 11.1 Agent Role

The evaluator agent is **not** a "subjective scorer". Instead, it:

1. **Orchestrates Evidence**: Generates checklist that maps verifier capabilities to specific checks
2. **Organizes Verification**: Maps checklist items to evidence atoms, updates status
3. **Adjudicates Based on Evidence**: Outputs eligible/ineligible decision with evidence-backed attribution

### 11.2 Rule-Based Instantiation

The current implementation uses a **rule-based agent** (no LLM calls), which:
- Generates checklist from verifier capabilities
- Maps evidence atoms to checklist items
- Adjudicates based on critical failures and evidence severity

This is one instantiation of the agent methodology. Future versions could use LLM-based agents with the same interface.

### 11.3 Evidence Attribution

Every adjudication decision must cite evidence IDs:

```python
attribution = [
    {
        "reason": "Field X out of range: value not in [lower, upper]",
        "evidence_ids": ["EVID_001", "EVID_002"],
        "severity": "critical",
        "rank": 1
    },
    ...
]
```

This ensures **full traceability** from decision to evidence.

---

## 12. Paper Integration

### 12.1 Method Section Structure

1. **Overview**: Evidence-driven evaluation framework
2. **Data Structures**: EvidenceAtom, Sample, ModelOutput, Record, ModelConfidence
3. **Verifier Graph**: 6 verifier types and execution
4. **Evaluator Agent**: Checklist generation, workflow organization, adjudication
5. **Rule-Based Fusion**: Gating rules, scoring protocol, fixed weights
6. **Failure Taxonomy**: 6 failure modes with severity classification
7. **Reproducibility**: Version locking and trace

### 12.2 Results Section

- **Main Table**: Model performance (availability, constraint satisfaction, conditional error, total score)
- **Constraint Satisfaction Table**: Violation counts by constraint type
- **Failure Mode Table**: Failure distribution by mode
- **Tail Risk Table**: P95, P99, high risk rates

### 12.3 Version Information for Paper

Record in paper:
- Config Hash: `81a5aef9181612b0`
- Schema Version: `701d05763ec09361`
- Constraint Lib Version: `1552a46f1a440793`
- Evaluator Version: `1.0.0`

These hashes ensure reproducibility.

---

**Document Version**: v1.0.0  
**Last Updated**: 2025-01-19

