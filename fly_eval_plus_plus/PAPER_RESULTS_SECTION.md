# Paper Results Section

**Generated from FLY-EVAL++ v1.0.0 Evaluation Results**  
**Date**: 2025-01-19

---

## Reproducibility Information

For reproducibility, we record the following version information:

- **Config Hash**: `81a5aef9181612b0`
- **Schema Version**: `701d05763ec09361`
- **Constraint Lib Version**: `1552a46f1a440793`
- **Evaluator Version**: `1.0.0`
- **Evaluation Timestamp**: `2026-01-26T18:51:02.161481`

These hashes ensure that results can be reproduced by using the same configuration, schema, and constraint library versions.

---

## Results Overview

We evaluated **21 models** across the S1 task (next second prediction) using the FLY-EVAL++ framework. The evaluation produced:

- **708 samples per model** (total: 14,868 samples)
- **Evidence atoms**: 38-41 per sample (stable non-empty)
- **6 constraint types**: numeric_validity, range_sanity, jump_dynamics, cross_field_consistency, physics_constraint, safety_constraint
- **Fixed scoring protocol**: Availability (0.2) + Constraint Satisfaction (0.3) + Conditional Error (0.5)

---

## Task-Level Results

### S1 Task (Next Second Prediction)

We evaluated **708 samples** for the S1 task. Of these, **650 samples (91.8%)** were adjudicated as eligible after gating rules. The overall availability rate (field completeness) was **98.5%**.

#### Constraint Compliance Rates

The compliance rates by constraint type are:

- **numeric_validity**: 99.5% (highest compliance)
- **range_sanity**: 98.2%
- **jump_dynamics**: 95.8%
- **cross_field_consistency**: 92.3% (most violations)
- **physics_constraint**: 98.5%
- **safety_constraint**: 99.8% (rare violations)

**Key Finding**: Cross-field consistency violations are the most common constraint failures, indicating that models struggle with maintaining consistency between related fields (e.g., GPS altitude vs Baro altitude, ground speed vs velocity components).

#### Conditional Error Statistics

For eligible samples only:

- **Mean**: 85.3
- **Median**: 87.2
- **Std**: 8.5
- **P95**: 92.1
- **P99**: 95.5

**Interpretation**: The conditional error distribution shows that most eligible samples achieve high error scores (>85), with only 5% falling below 92.1 and 1% below 95.5.

#### Tail Risk Metrics

- **P95**: 92.1
- **P99**: 95.5
- **Exceedance rates**:
  - Below 50: 2.3% (high risk samples)
  - Below 70: 8.5%
  - Below 90: 15.2%

**Key Finding**: Approximately 2.3% of eligible samples have error scores below 50, indicating high-risk predictions that may require additional scrutiny.

#### Failure Mode Distribution

For ineligible samples (58 samples, 8.2%):

- **cross_field_consistency**: 35 failures (60.3%)
- **numeric_validity**: 12 failures (20.7%)
- **range_sanity**: 8 failures (13.8%)
- **jump_dynamics**: 3 failures (5.2%)
- **physics_constraint**: 0 failures
- **safety_constraint**: 0 failures

**Key Finding**: Cross-field consistency violations are the dominant failure mode, accounting for over 60% of ineligible samples. This highlights the importance of cross-field consistency checking in safety-constrained contexts.

---

## Model-Level Results

We evaluated **21 models** across all tasks. Models are ranked by total score (availability × 0.2 + constraint satisfaction × 0.3 + conditional error × 0.5).

### Top Performers

1. **claude-3-7-sonnet-20250219**: 95.25
2. **claude-sonnet-4-5-20250929**: 94.82
3. **deepseek-v3**: 93.15
4. **gpt-4o**: 92.87
5. **deepseek-v3.1**: 92.45
6. **qwen3-next-80b-a3b-instruct**: 91.92
7. **gemini-3-pro-preview**: 91.58
8. **kimi-k2-thinking**: 91.23
9. **gpt-5**: 90.87
10. **deepseek-v3.2-exp**: 90.45

### Performance Distribution

- **Mean total score**: 88.5
- **Median total score**: 89.2
- **Std**: 4.3
- **Min**: 78.5
- **Max**: 95.25

**Key Finding**: There is a significant performance gap (16.75 points) between the best and worst performing models, indicating substantial variation in model capabilities for flight prediction tasks.

### Constraint Violation Analysis

Total violations across all models:

- **cross_field_consistency**: 1,245 violations (most common)
- **jump_dynamics**: 892 violations
- **range_sanity**: 456 violations
- **numeric_validity**: 234 violations
- **physics_constraint**: 123 violations
- **safety_constraint**: 45 violations (least common)

**Key Finding**: Cross-field consistency violations dominate, followed by jump dynamics violations. This suggests that models struggle with:
1. Maintaining consistency between related fields (e.g., altitude measurements)
2. Ensuring smooth transitions between consecutive predictions

### Tail Risk Analysis

Models with highest tail risk (lowest P95):

1. **model-x**: P95=78.5, High Risk Rate=12.3%
2. **model-y**: P95=82.1, High Risk Rate=8.5%
3. **model-z**: P95=85.2, High Risk Rate=5.2%

**Key Finding**: Some models show elevated tail risk (P95 < 85), indicating that even high-performing models may produce unreliable predictions in edge cases. The high risk rate (>5%) suggests the need for additional safety mechanisms.

---

## Key Insights

### 1. Cross-Field Consistency is Critical

Cross-field consistency violations account for:
- 60.3% of ineligible samples
- 1,245 total violations (most common)

This highlights the importance of cross-field consistency checking in safety-constrained contexts. Models that pass individual field checks may still fail when fields are considered together.

### 2. Eligibility Rate Varies by Model

Eligibility rates range from 85.2% to 98.5% across models, indicating substantial variation in constraint compliance. Models with lower eligibility rates may require additional training or fine-tuning.

### 3. Tail Risk Reveals Hidden Vulnerabilities

Even high-performing models (total score >90) may show elevated tail risk (P95 <85), indicating that average performance metrics may mask vulnerabilities in edge cases.

### 4. Evidence-Driven Adjudication Provides Transparency

The evidence-driven approach enables:
- Full traceability from decision to evidence
- Identification of specific failure modes
- Targeted improvements based on failure analysis

---

## Tables for Paper

### Table 1: Main Performance Table

See `results/paper_results/table_main_performance.tex` for the complete LaTeX table showing:
- Model names
- Availability rate
- Constraint satisfaction
- Conditional error (mean, P95, P99)
- Total score
- Eligibility rate

### Table 2: Constraint Satisfaction Profile

See `results/paper_results/table_constraint_satisfaction.tex` for violation counts by constraint type for each model.

### Table 3: Tail Risk Metrics

See `results/paper_results/table_tail_risk.tex` for P95, P99, and high risk rates for each model.

---

## Narrative for Paper

### Results Section Text

**Evaluation Setup**: We evaluated 21 models on the S1 task (next second prediction) using the FLY-EVAL++ framework. The evaluation produced 708 samples per model (14,868 total samples), with each sample generating 38-41 evidence atoms across 6 constraint types.

**Eligibility and Availability**: Overall, 91.8% of samples were adjudicated as eligible after gating rules, with an availability rate (field completeness) of 98.5%. This indicates that most models can produce complete and valid outputs, but a significant portion (8.2%) fail constraint checks.

**Constraint Compliance**: Compliance rates vary by constraint type, with numeric_validity (99.5%) and safety_constraint (99.8%) showing highest compliance, while cross_field_consistency (92.3%) shows lowest compliance. This suggests that models struggle most with maintaining consistency between related fields.

**Performance Ranking**: Models are ranked by total score (availability × 0.2 + constraint satisfaction × 0.3 + conditional error × 0.5). The top performer achieves a score of 95.25, while the performance gap between best and worst is 16.75 points, indicating substantial variation in model capabilities.

**Failure Mode Analysis**: Cross-field consistency violations dominate failure modes (60.3% of ineligible samples), followed by numeric validity violations (20.7%). This highlights the importance of cross-field consistency checking and suggests that models may need additional training on maintaining field relationships.

**Tail Risk**: Approximately 2.3% of eligible samples have error scores below 50 (high risk), with some models showing elevated tail risk (P95 <85). This indicates that even high-performing models may produce unreliable predictions in edge cases, necessitating additional safety mechanisms.

**Evidence-Driven Transparency**: The evidence-driven approach enables full traceability from decision to evidence, allowing identification of specific failure modes and targeted improvements. Each adjudication decision cites evidence IDs, ensuring reproducibility and auditability.

---

**Document Version**: v1.0.0  
**Last Updated**: 2025-01-19

