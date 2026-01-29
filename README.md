# FLY-EVAL++: Comprehensive Flight Prediction Evaluation Framework

FLY-EVAL++ is a deterministic evaluation framework for assessing Large Language Models (LLMs) on flight trajectory prediction tasks. This framework evaluates models across five key dimensions: Protocol Compliance, Field Validity, Physics Consistency, Safety Constraints, and Predictive Quality.

## Overview

This repository contains the evaluation framework used in the ICML 2026 paper evaluating 66 LLMs on flight prediction tasks. The framework provides:

- **Deterministic Evaluation**: Rule-based assessment without LLM judge subjectivity
- **Multi-Dimensional Scoring**: 5-dimension evaluation (Protocol, Field, Physics, Safety, Predictive)
- **Scalable Pipeline**: Support for evaluating multiple models on large datasets
- **Comprehensive Reporting**: LaTeX table generation for paper integration

## Project Structure

```
.
├── fly_eval_plus_plus/          # Core evaluation framework
│   ├── main.py                  # Main evaluator class
│   ├── data_loader.py           # Data loading utilities
│   ├── run_deterministic_evaluation.py  # Deterministic evaluation runner
│   └── ...
├── run_46_models_evaluation.py  # Script to evaluate 45 additional models
├── generate_appendix_B_table.py # Generate LaTeX tables for appendix
└── README.md                    # This file
```

## Installation

```bash
# Clone the repository
git clone https://github.com/gurenolun/FLY-Eval-.git
cd FLY-Eval-

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Evaluating Models

To evaluate models using the deterministic evaluation method:

```bash
python run_46_models_evaluation.py
```

This script:
- Loads model outputs from `data/model_results/merged_results_20250617_203957/`
- Loads reference data (ground truth) from `data/reference_data/next_second_pairs.jsonl`
- Evaluates each model across 5 dimensions
- Saves results to `results/all_46_models_v7_physics_fixed/`

### Generating LaTeX Tables

To generate LaTeX tables for paper appendices:

```bash
python generate_appendix_B_table.py
```

This extracts scores from evaluation results and generates formatted LaTeX tables.

## Evaluation Dimensions

1. **Protocol Schema Compliance**: Validates JSON structure and required fields
2. **Field Validity & Local Dynamics**: Checks field value ranges and local consistency
3. **Physics/Cross-field Consistency**: Verifies physical constraints and cross-field relationships
4. **Safety Constraint Satisfaction**: Ensures safety-critical constraints are met
5. **Predictive Quality & Reliability**: Compares predictions against ground truth

## Data Format

### Model Output Format

Model outputs should be JSONL files with the following structure:

```json
{
  "id": "sample_id",
  "question": "prompt text",
  "response": "{\"field1\": \"value1\", ...}",
  "model": "model_name",
  "timestamp": "timestamp"
}
```

### Reference Data Format

Reference data (ground truth) should be JSONL files:

```json
{
  "id": "sample_id",
  "next_second": {
    "Latitude (WGS84 deg)": "value",
    ...
  }
}
```

## Results

Evaluation results are saved in JSONL format with detailed scores:

```json
{
  "sample_id": "sample_id",
  "model_name": "model_name",
  "optional_scores": {
    "dimension_scores": {
      "protocol_schema_compliance": 0.92,
      "field_validity_local_dynamics": 0.61,
      "physics_cross_field_consistency": 0.99,
      "safety_constraint_satisfaction": 0.63,
      "predictive_quality_reliability": 0.92
    },
    "total_score": 0.81
  }
}
```

## Citation

If you use this evaluation framework, please cite:

```bibtex
@article{fly-eval-2026,
  title={FLY-EVAL++: Comprehensive Evaluation of LLMs on Flight Prediction},
  author={...},
  journal={ICML},
  year={2026}
}
```

## License

[Specify your license here]

## Contact

[Your contact information]
