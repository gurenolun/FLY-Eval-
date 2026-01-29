"""
FLY-EVAL++ Evaluation Runner

Runs evaluation for all models and tasks, generates reports.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from .main import FLYEvalPlusPlus
from .core.data_structures import Record, TaskSummary, ModelProfile
from .data_loader import DataLoader


def run_evaluation(task_ids: List[str] = None, model_names: List[str] = None, 
                  output_dir: str = "results") -> Dict[str, Any]:
    """
    Run evaluation for specified tasks and models
    
    Args:
        task_ids: List of task IDs to evaluate (default: ["S1", "M1", "M3"])
        model_names: List of model names to evaluate (default: all models)
        output_dir: Output directory for results
    
    Returns:
        Dictionary with evaluation results
    """
    if task_ids is None:
        task_ids = ["S1", "M1", "M3"]
    
    # Initialize evaluator
    evaluator = FLYEvalPlusPlus()
    data_loader = DataLoader()
    
    # Load model confidence
    model_confidence_dict = data_loader.load_model_confidence()
    
    # Get all models if not specified
    if model_names is None:
        # Get union of all models across tasks
        all_models = set()
        for task_id in task_ids:
            models = data_loader.get_all_models_for_task(task_id)
            all_models.update(models)
        model_names = sorted(list(all_models))
    
    # Results storage
    all_records: Dict[str, List[Record]] = {}  # task_id -> [records]
    all_profiles: Dict[str, ModelProfile] = {}  # model_name -> profile
    
    # Evaluate each task and model
    for task_id in task_ids:
        all_records[task_id] = []
        
        for model_name in model_names:
            print(f"\n{'='*80}")
            print(f"Evaluating: {task_id} - {model_name}")
            print(f"{'='*80}")
            
            # Load samples and model outputs
            samples, model_outputs = data_loader.create_samples_and_outputs(task_id, model_name)
            
            if not samples or not model_outputs:
                print(f"⚠️  No data found for {task_id} - {model_name}")
                continue
            
            # Get model confidence
            model_confidence = model_confidence_dict.get(model_name)
            
            # Evaluate all samples
            for sample, model_output in zip(samples, model_outputs):
                record = evaluator.evaluate_sample(sample, model_output, model_confidence)
                all_records[task_id].append(record)
            
            print(f"✅ Evaluated {len(samples)} samples for {model_name}")
    
    # Generate task summaries
    task_summaries = {}
    for task_id in task_ids:
        records = all_records.get(task_id, [])
        if records:
            task_summary = evaluator.generate_task_summary(records, task_id)
            task_summaries[task_id] = task_summary
    
    # Generate model profiles
    for model_name in model_names:
        # Collect all records for this model
        model_records = []
        for task_id in task_ids:
            task_records = all_records.get(task_id, [])
            model_records.extend([r for r in task_records if r.model_name == model_name])
        
        if model_records:
            model_confidence = model_confidence_dict.get(model_name)
            profile = evaluator.generate_model_profile(model_records, model_confidence)
            all_profiles[model_name] = profile
    
    # Save results
    os.makedirs(output_dir, exist_ok=True)
    
    # Save records (JSON)
    for task_id in task_ids:
        records = all_records.get(task_id, [])
        records_file = os.path.join(output_dir, f"records_{task_id}.json")
        with open(records_file, 'w', encoding='utf-8') as f:
            json.dump([_record_to_dict(r) for r in records], f, indent=2, default=str)
    
    # Save task summaries
    summaries_file = os.path.join(output_dir, "task_summaries.json")
    with open(summaries_file, 'w', encoding='utf-8') as f:
        json.dump({k: _task_summary_to_dict(v) for k, v in task_summaries.items()}, 
                 f, indent=2, default=str)
    
    # Save model profiles
    profiles_file = os.path.join(output_dir, "model_profiles.json")
    with open(profiles_file, 'w', encoding='utf-8') as f:
        json.dump({k: _model_profile_to_dict(v) for k, v in all_profiles.items()}, 
                 f, indent=2, default=str)
    
    return {
        "records": all_records,
        "task_summaries": task_summaries,
        "model_profiles": all_profiles
    }


def _record_to_dict(record: Record) -> Dict[str, Any]:
    """Convert Record to dict for JSON serialization"""
    return {
        "sample_id": record.sample_id,
        "model_name": record.model_name,
        "task_id": record.task_id,
        "protocol_result": record.protocol_result,
        "evidence_pack": {
            "atoms": [
                {
                    "id": atom.id,
                    "type": atom.type,
                    "field": atom.field,
                    "pass": atom.pass_,
                    "severity": atom.severity.value,
                    "scope": atom.scope.value,
                    "message": atom.message,
                    "meta": atom.meta
                }
                for atom in record.evidence_pack.get('atoms', [])
            ]
        },
        "agent_output": record.agent_output,
        "optional_scores": record.optional_scores,
        "trace": record.trace
    }


def _task_summary_to_dict(summary: TaskSummary) -> Dict[str, Any]:
    """Convert TaskSummary to dict"""
    return {
        "task_id": summary.task_id,
        "total_samples": summary.total_samples,
        "eligible_samples": summary.eligible_samples,
        "ineligible_samples": summary.ineligible_samples,
        "compliance_rate": summary.compliance_rate,
        "availability_rate": summary.availability_rate,
        "constraint_satisfaction": summary.constraint_satisfaction,
        "conditional_error": summary.conditional_error,
        "tail_risk": summary.tail_risk,
        "failure_modes": summary.failure_modes
    }


def _model_profile_to_dict(profile: ModelProfile) -> Dict[str, Any]:
    """Convert ModelProfile to dict"""
    return {
        "model_name": profile.model_name,
        "data_driven_profile": profile.data_driven_profile,
        "model_confidence_prior": profile.model_confidence_prior,
        "optional_total_score": profile.optional_total_score
    }


if __name__ == "__main__":
    # Example: Run evaluation for all tasks and models
    results = run_evaluation()
    print("\n✅ Evaluation complete!")
    print(f"   Tasks evaluated: {len(results['task_summaries'])}")
    print(f"   Models profiled: {len(results['model_profiles'])}")

