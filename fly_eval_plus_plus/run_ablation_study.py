"""
Ablation Study: Rule-only vs LLM-judge

Compares rule-based fusion vs LLM-based fusion.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fly_eval_plus_plus.main import FLYEvalPlusPlus
from fly_eval_plus_plus.data_loader import DataLoader
from fly_eval_plus_plus.core.data_structures import EvalConfig


def run_rule_based_evaluation(task_id: str = "S1", model_name: str = None, 
                              num_samples: int = 10) -> Dict[str, Any]:
    """Run rule-based evaluation"""
    print("=" * 80)
    print("Rule-Based Evaluation (Baseline)")
    print("=" * 80)
    
    # Create config with rule-based fusion
    config = EvalConfig(version="1.0.0")
    config.fusion_protocol = {
        "type": "rule_based",
        "gating_rules": {
            "protocol_failure": {"max_allowed": 0, "severity": "critical"},
            "safety_constraint_violation": {"max_allowed": 0, "severity": "critical"},
            "key_field_missing": {"max_allowed": 0, "severity": "critical"}
        },
        "scoring_rules": {
            "availability_weight": 0.2,
            "constraint_satisfaction_weight": 0.3,
            "conditional_error_weight": 0.5
        }
    }
    
    evaluator = FLYEvalPlusPlus(config_path=None)
    evaluator.config = config
    evaluator.fusion = evaluator._create_fusion(config.fusion_protocol)
    
    # Load data
    loader = DataLoader()
    samples, model_outputs = loader.create_samples_and_outputs(task_id, model_name)
    
    if not samples or not model_outputs:
        print(f"⚠️  No data found for {task_id} - {model_name}")
        return {}
    
    # Evaluate samples
    records = []
    for sample, model_output in zip(samples[:num_samples], model_outputs[:num_samples]):
        record = evaluator.evaluate_sample(sample, model_output)
        records.append(record)
    
    # Collect scores
    scores = []
    for record in records:
        scores_dict = record.optional_scores
        if scores_dict and "total_score" in scores_dict and scores_dict["total_score"] is not None:
            scores.append({
                "sample_id": record.sample_id,
                "total_score": scores_dict["total_score"],
                "availability": scores_dict.get("availability_score", 0),
                "constraint": scores_dict.get("constraint_satisfaction_score", 0),
                "error": scores_dict.get("conditional_error_score", 0)
            })
    
    return {
        "method": "rule_based",
        "num_samples": len(scores),
        "scores": scores,
        "mean_score": sum(s["total_score"] for s in scores) / len(scores) if scores else 0
    }


def run_llm_judge_evaluation(task_id: str = "S1", model_name: str = None,
                             num_samples: int = 10) -> Dict[str, Any]:
    """Run LLM-judge evaluation"""
    print("=" * 80)
    print("LLM-Judge Evaluation")
    print("=" * 80)
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  Warning: OPENAI_API_KEY not set. Cannot run LLM-judge evaluation.")
        return {}
    
    # Create config with LLM-based fusion
    config = EvalConfig(version="1.0.0")
    config.fusion_protocol = {
        "type": "llm_based",
        "gating_rules": {
            "protocol_failure": {"max_allowed": 0, "severity": "critical"},
            "safety_constraint_violation": {"max_allowed": 0, "severity": "critical"},
            "key_field_missing": {"max_allowed": 0, "severity": "critical"}
        },
        "llm_judge": {
            "model": "gpt-4o",
            "temperature": 0,
            "api_key": api_key,
            "max_retries": 3
        }
    }
    
    evaluator = FLYEvalPlusPlus(config_path=None)
    evaluator.config = config
    evaluator.fusion = evaluator._create_fusion(config.fusion_protocol)
    
    # Load data
    loader = DataLoader()
    samples, model_outputs = loader.create_samples_and_outputs(task_id, model_name)
    
    if not samples or not model_outputs:
        print(f"⚠️  No data found for {task_id} - {model_name}")
        return {}
    
    # Evaluate samples
    records = []
    for sample, model_output in zip(samples[:num_samples], model_outputs[:num_samples]):
        record = evaluator.evaluate_sample(sample, model_output)
        records.append(record)
    
    # Collect scores
    scores = []
    for record in records:
        scores_dict = record.optional_scores
        if scores_dict and "total_score" in scores_dict and scores_dict["total_score"] is not None:
            llm_output = scores_dict.get("llm_judge_output", {})
            scores.append({
                "sample_id": record.sample_id,
                "total_score": scores_dict["total_score"],
                "overall_grade": llm_output.get("overall_grade", "N/A"),
                "dimension_scores": llm_output.get("dimension_scores", {}),
                "availability": scores_dict.get("availability_score", 0),
                "constraint": scores_dict.get("constraint_satisfaction_score", 0),
                "error": scores_dict.get("conditional_error_score", 0)
            })
    
    return {
        "method": "llm_judge",
        "num_samples": len(scores),
        "scores": scores,
        "mean_score": sum(s["total_score"] for s in scores) / len(scores) if scores else 0
    }


def compare_results(rule_results: Dict[str, Any], llm_results: Dict[str, Any]) -> Dict[str, Any]:
    """Compare rule-based and LLM-judge results"""
    print("\n" + "=" * 80)
    print("Comparison: Rule-Based vs LLM-Judge")
    print("=" * 80)
    
    comparison = {
        "rule_based": {
            "mean_score": rule_results.get("mean_score", 0),
            "num_samples": rule_results.get("num_samples", 0)
        },
        "llm_judge": {
            "mean_score": llm_results.get("mean_score", 0),
            "num_samples": llm_results.get("num_samples", 0)
        },
        "difference": {
            "mean_score_diff": llm_results.get("mean_score", 0) - rule_results.get("mean_score", 0),
            "relative_diff": (llm_results.get("mean_score", 0) - rule_results.get("mean_score", 0)) / 
                           rule_results.get("mean_score", 1) * 100 if rule_results.get("mean_score", 0) > 0 else 0
        }
    }
    
    print(f"\nRule-Based:")
    print(f"  Mean Score: {comparison['rule_based']['mean_score']:.2f}")
    print(f"  Samples: {comparison['rule_based']['num_samples']}")
    
    print(f"\nLLM-Judge:")
    print(f"  Mean Score: {comparison['llm_judge']['mean_score']:.2f}")
    print(f"  Samples: {comparison['llm_judge']['num_samples']}")
    
    print(f"\nDifference:")
    print(f"  Absolute: {comparison['difference']['mean_score_diff']:.2f}")
    print(f"  Relative: {comparison['difference']['relative_diff']:.2f}%")
    
    return comparison


def run_ablation_study(task_id: str = "S1", model_name: str = None, num_samples: int = 10):
    """Run full ablation study"""
    print("=" * 80)
    print("Ablation Study: Rule-Only vs LLM-Judge")
    print("=" * 80)
    
    # Run rule-based evaluation
    rule_results = run_rule_based_evaluation(task_id, model_name, num_samples)
    
    # Run LLM-judge evaluation
    llm_results = run_llm_judge_evaluation(task_id, model_name, num_samples)
    
    # Compare results
    comparison = compare_results(rule_results, llm_results)
    
    # Save results
    output_dir = Path("results/ablation_study")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = {
        "rule_based": rule_results,
        "llm_judge": llm_results,
        "comparison": comparison
    }
    
    output_file = output_dir / "ablation_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n✅ Results saved to: {output_file}")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run ablation study")
    parser.add_argument("--task", type=str, default="S1", help="Task ID (S1, M1, M3)")
    parser.add_argument("--model", type=str, default=None, help="Model name (default: first available)")
    parser.add_argument("--num_samples", type=int, default=10, help="Number of samples to evaluate")
    
    args = parser.parse_args()
    
    run_ablation_study(args.task, args.model, args.num_samples)

