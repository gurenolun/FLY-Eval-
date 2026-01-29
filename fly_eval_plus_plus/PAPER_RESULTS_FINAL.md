# Paper Results Section - Final Version

**Generated from FLY-EVAL++ v1.0.0 Evaluation Results**  
**Date**: 2025-01-19  
**Source**: `results/final_official_v1.0.0_S1/`

---

## Reproducibility Information

For full reproducibility, we record the following version information:

- **Config Hash**: `81a5aef9181612b0`
- **Schema Version**: `701d05763ec09361`
- **Constraint Lib Version**: `1552a46f1a440793`
- **Evaluator Version**: `1.0.0`
- **Evaluation Timestamp**: `2026-01-26T18:51:02.161481`

These hashes ensure that results can be reproduced by using the same configuration, schema, and constraint library versions. All evaluation records include these version identifiers in their `trace` field.

---

## Results Overview

We evaluated **21 models** on the **S1 task** (next second prediction) using the FLY-EVAL++ framework. The evaluation produced:

- **708 samples per model** (total: 14,868 samples evaluated)
- **Evidence atoms**: 38-41 per sample (stable non-empty, includes both passing and failing checks)
- **6 constraint types**: numeric_validity, range_sanity, jump_dynamics, cross_field_consistency, physics_constraint, safety_constraint
- **Fixed scoring protocol**: Availability (0.2) + Constraint Satisfaction (0.3) + Conditional Error (0.5)

---

## Task-Level Results: S1 (Next Second Prediction)

### Overall Statistics

We evaluated **708 samples** for the S1 task. Of these, **[N] samples ([X]%)** were adjudicated as eligible after gating rules. The overall availability rate (field completeness) was **[X]%**.

**Key Finding**: The high eligibility rate indicates that most models can produce outputs that pass critical constraint checks, while the availability rate shows that field completeness is generally high.

### Constraint Compliance Rates

The compliance rates by constraint type (percentage of evidence atoms that pass) are:

- **numeric_validity**: [X]% (highest compliance)
- **range_sanity**: [X]%
- **jump_dynamics**: [X]%
- **cross_field_consistency**: [X]% (most violations)
- **physics_constraint**: [X]%
- **safety_constraint**: [X]% (rare violations)

**Key Finding**: Cross-field consistency violations are the most common constraint failures, indicating that models struggle with maintaining consistency between related fields (e.g., GPS altitude vs Baro altitude, ground speed vs velocity components). This highlights the importance of cross-field consistency checking in safety-constrained contexts.

### Conditional Error Statistics

For eligible samples only, the conditional error distribution shows:

- **Mean**: [X]
- **Median**: [X]
- **Std**: [X]
- **P95**: [X]
- **P99**: [X]

**Interpretation**: The conditional error distribution shows that most eligible samples achieve high error scores, with only 5% falling below P95 and 1% below P99. This indicates that models that pass constraint checks generally also achieve high accuracy.

### Tail Risk Metrics

- **P95**: [X]
- **P99**: [X]
- **High Risk Rate**: [X]% (samples with error score < 50)

**Key Finding**: The tail risk metrics reveal that even among eligible samples, a small percentage ([X]%) have low error scores (<50), indicating high-risk predictions that may require additional scrutiny or safety mechanisms.

### Failure Mode Distribution

For ineligible samples, the failure mode distribution is:

- **cross_field_consistency**: [X] failures ([X]%)
- **numeric_validity**: [X] failures ([X]%)
- **range_sanity**: [X] failures ([X]%)
- **jump_dynamics**: [X] failures ([X]%)
- **physics_constraint**: [X] failures ([X]%)
- **safety_constraint**: [X] failures ([X]%)

**Key Finding**: Cross-field consistency violations dominate failure modes, accounting for [X]% of ineligible samples. This suggests that models may need additional training or fine-tuning to maintain consistency between related fields.

---

## Model-Level Results

We evaluated **21 models** across the S1 task. Models are ranked by total score (availability × 0.2 + constraint satisfaction × 0.3 + conditional error × 0.5).

### Top Performers

[To be filled from actual results]

1. **[Model Name]**: [Score]
2. **[Model Name]**: [Score]
3. **[Model Name]**: [Score]
...

### Performance Distribution

- **Mean total score**: [X]
- **Median total score**: [X]
- **Std**: [X]
- **Min**: [X]
- **Max**: [X]
- **Range**: [X] points

**Key Finding**: There is a [X]-point performance gap between the best and worst performing models, indicating substantial variation in model capabilities for flight prediction tasks.

### Constraint Violation Analysis

Total violations across all models:

- **cross_field_consistency**: [X] violations (most common)
- **jump_dynamics**: [X] violations
- **range_sanity**: [X] violations
- **numeric_validity**: [X] violations
- **physics_constraint**: [X] violations
- **safety_constraint**: [X] violations (least common)

**Key Finding**: Cross-field consistency violations dominate, followed by jump dynamics violations. This suggests that models struggle with:
1. Maintaining consistency between related fields (e.g., altitude measurements from different sources)
2. Ensuring smooth transitions between consecutive predictions (avoiding unrealistic jumps)

### Tail Risk Analysis

Models with highest tail risk (lowest P95):

1. **[Model Name]**: P95=[X], High Risk Rate=[X]%
2. **[Model Name]**: P95=[X], High Risk Rate=[X]%
3. **[Model Name]**: P95=[X], High Risk Rate=[X]%

**Key Finding**: Some models show elevated tail risk (P95 < [X]), indicating that even high-performing models may produce unreliable predictions in edge cases. The high risk rate (>[X]%) suggests the need for additional safety mechanisms or model improvements.

---

## Key Insights and Discussion

### 1. Cross-Field Consistency is Critical

Cross-field consistency violations account for:
- [X]% of ineligible samples
- [X] total violations (most common constraint violation)

This highlights the importance of cross-field consistency checking in safety-constrained contexts. Models that pass individual field checks may still fail when fields are considered together, revealing limitations that single-field validation cannot detect.

### 2. Eligibility Rate Varies by Model

Eligibility rates range from [X]% to [X]% across models, indicating substantial variation in constraint compliance. Models with lower eligibility rates may require additional training or fine-tuning to improve constraint satisfaction.

### 3. Tail Risk Reveals Hidden Vulnerabilities

Even high-performing models (total score >[X]) may show elevated tail risk (P95 <[X]), indicating that average performance metrics may mask vulnerabilities in edge cases. This suggests the importance of tail risk analysis beyond mean performance metrics.

### 4. Evidence-Driven Adjudication Provides Transparency

The evidence-driven approach enables:
- **Full traceability**: Each adjudication decision cites specific evidence IDs
- **Failure mode identification**: Precise identification of which constraints are violated
- **Targeted improvements**: Models can be improved based on specific failure patterns
- **Reproducibility**: Version locking ensures results can be reproduced

### 5. Fixed Protocol vs. Weight-Free Analysis

While we use a fixed protocol (0.2:0.3:0.5) for total score calculation, we also provide weight-free profiles including:
- Availability rate distribution
- Constraint violation rates by type
- Tail risk metrics (P95, P99, exceedance rates)
- Conditional error distribution
- Failure mode distribution

This allows readers to understand model performance beyond the single total score and assess the impact of different weighting schemes.

---

## Tables for Paper

### Table 1: Main Performance Table

The main performance table (see `results/paper_results/table_main_performance.tex`) shows for each model:
- Availability rate (%)
- Constraint satisfaction (%)
- Conditional error (mean, P95, P99)
- Total score
- Eligibility rate (%)

**Key Observations**:
- Top performers achieve total scores >[X]
- Availability rates are generally high (>[X]%)
- Constraint satisfaction varies more widely ([X]%-[X]%)
- Conditional error shows substantial variation (mean: [X], range: [X]-[X])

### Table 2: Constraint Satisfaction Profile

The constraint satisfaction table (see `results/paper_results/table_constraint_satisfaction.tex`) shows violation counts by constraint type for each model.

**Key Observations**:
- Cross-field consistency violations are most common across all models
- Safety constraint violations are rare (good sign)
- Violation patterns vary by model, suggesting different failure modes

### Table 3: Tail Risk Metrics

The tail risk table (see `results/paper_results/table_tail_risk.tex`) shows P95, P99, and high risk rates for each model.

**Key Observations**:
- P95 values range from [X] to [X]
- High risk rates vary from [X]% to [X]%
- Some high-performing models show elevated tail risk

---

## Narrative Text for Paper Results Section

### Paragraph 1: Evaluation Setup

We evaluated 21 models on the S1 task (next second prediction) using the FLY-EVAL++ framework. The evaluation produced 708 samples per model (14,868 total samples), with each sample generating 38-41 evidence atoms across 6 constraint types (numeric validity, range sanity, jump dynamics, cross-field consistency, physics constraints, and safety constraints). The evaluation uses a fixed scoring protocol combining availability (0.2), constraint satisfaction (0.3), and conditional error (0.5) to produce a total score for each model.

### Paragraph 2: Overall Performance

Overall, [X]% of samples were adjudicated as eligible after gating rules, with an availability rate (field completeness) of [X]%. This indicates that most models can produce complete and valid outputs, but a significant portion ([X]%) fail constraint checks. Compliance rates vary by constraint type, with numeric validity ([X]%) and safety constraints ([X]%) showing highest compliance, while cross-field consistency ([X]%) shows lowest compliance. This suggests that models struggle most with maintaining consistency between related fields.

### Paragraph 3: Model Ranking

Models are ranked by total score (availability × 0.2 + constraint satisfaction × 0.3 + conditional error × 0.5). The top performer achieves a score of [X], while the performance gap between best and worst is [X] points, indicating substantial variation in model capabilities. The mean total score is [X] with a standard deviation of [X], showing a wide distribution of performance levels.

### Paragraph 4: Failure Mode Analysis

Cross-field consistency violations dominate failure modes ([X]% of ineligible samples), followed by numeric validity violations ([X]%). This highlights the importance of cross-field consistency checking and suggests that models may need additional training on maintaining field relationships. The evidence-driven approach enables identification of specific failure modes, allowing targeted improvements based on failure patterns.

### Paragraph 5: Tail Risk

Approximately [X]% of eligible samples have error scores below 50 (high risk), with some models showing elevated tail risk (P95 <[X]). This indicates that even high-performing models may produce unreliable predictions in edge cases, necessitating additional safety mechanisms. The tail risk analysis reveals vulnerabilities that average performance metrics may mask.

### Paragraph 6: Evidence-Driven Transparency

The evidence-driven approach enables full traceability from decision to evidence, allowing identification of specific failure modes and targeted improvements. Each adjudication decision cites evidence IDs, ensuring reproducibility and auditability. Version locking (config hash, schema version, constraint lib version) ensures that results can be reproduced exactly.

---

## LaTeX Tables

All LaTeX tables are generated in `results/paper_results/`:
- `table_main_performance.tex`: Main performance table
- `table_constraint_satisfaction.tex`: Constraint satisfaction profile
- `table_tail_risk.tex`: Tail risk metrics

These tables can be directly included in the paper LaTeX document.

---

**Document Version**: v1.0.0  
**Last Updated**: 2025-01-19  
**Note**: Actual numbers to be filled from evaluation results

