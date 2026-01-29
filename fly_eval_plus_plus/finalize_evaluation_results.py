"""
Finalize Evaluation Results

评估完成后，生成最终结果文件、统计报告和LaTeX表格。
"""

import json
import os
from pathlib import Path
from datetime import datetime


def finalize_evaluation_results(results_dir: str = "results/final_official_v1.0.0_llm_judge",
                                task_id: str = "S1"):
    """
    Finalize evaluation results after completion
    
    Args:
        results_dir: Results directory
        task_id: Task ID
    """
    print("=" * 80)
    print("FLY-EVAL++ 评估结果最终化")
    print("=" * 80)
    
    incremental_file = os.path.join(results_dir, f"records_{task_id}_incremental.jsonl")
    
    if not os.path.exists(incremental_file):
        print(f"❌ 增量文件不存在: {incremental_file}")
        return
    
    # Load all records from incremental file
    print("\n加载记录...")
    all_records = []
    with open(incremental_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                all_records.append(json.loads(line))
    
    print(f"  总记录数: {len(all_records)}")
    
    # Group by model
    model_records = {}
    for record in all_records:
        model_name = record.get('model_name', 'unknown')
        if model_name not in model_records:
            model_records[model_name] = []
        model_records[model_name].append(record)
    
    print(f"  模型数: {len(model_records)}")
    
    # Save complete records JSON
    records_file = os.path.join(results_dir, f"records_{task_id}.json")
    print(f"\n保存完整记录文件...")
    with open(records_file, 'w', encoding='utf-8') as f:
        json.dump(all_records, f, indent=2, default=str, ensure_ascii=False)
    print(f"  ✅ 已保存: {records_file}")
    
    # Generate final summary
    print(f"\n生成最终汇总...")
    
    # Import evaluator to generate summaries
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from fly_eval_plus_plus.main import FLYEvalPlusPlus
    from fly_eval_plus_plus.core.data_structures import Record, TaskSummary, ModelProfile
    from fly_eval_plus_plus.data_loader import DataLoader
    
    # Convert dict records to Record objects
    record_objects = []
    for rec_dict in all_records:
        # Convert evidence atoms
        evidence_pack = rec_dict.get('evidence_pack', {})
        # ... (simplified conversion, may need full implementation)
        record_objects.append(rec_dict)  # For now, keep as dict
    
    # Generate task summary (simplified)
    total_samples = len(all_records)
    eligible_samples = sum(1 for r in all_records if r.get('agent_output', {}).get('adjudication') == 'eligible')
    
    task_summary = {
        "task_id": task_id,
        "total_samples": total_samples,
        "eligible_samples": eligible_samples,
        "ineligible_samples": total_samples - eligible_samples,
        "eligibility_rate": eligible_samples / total_samples * 100 if total_samples > 0 else 0,
        "evaluation_timestamp": datetime.now().isoformat()
    }
    
    summaries_file = os.path.join(results_dir, "task_summaries.json")
    with open(summaries_file, 'w', encoding='utf-8') as f:
        json.dump({task_id: task_summary}, f, indent=2, default=str)
    print(f"  ✅ 已保存: {summaries_file}")
    
    # Generate model profiles
    model_profiles = {}
    for model_name, model_recs in model_records.items():
        # Calculate statistics
        total_scores = [r.get('optional_scores', {}).get('total_score', 0) for r in model_recs]
        avg_score = sum(total_scores) / len(total_scores) if total_scores else 0
        
        eligible_count = sum(1 for r in model_recs if r.get('agent_output', {}).get('adjudication') == 'eligible')
        
        model_profiles[model_name] = {
            "model_name": model_name,
            "total_samples": len(model_recs),
            "eligible_samples": eligible_count,
            "eligibility_rate": eligible_count / len(model_recs) * 100 if model_recs else 0,
            "average_score": avg_score,
            "score_statistics": {
                "mean": avg_score,
                "min": min(total_scores) if total_scores else 0,
                "max": max(total_scores) if total_scores else 0
            }
        }
    
    profiles_file = os.path.join(results_dir, "model_profiles.json")
    with open(profiles_file, 'w', encoding='utf-8') as f:
        json.dump(model_profiles, f, indent=2, default=str)
    print(f"  ✅ 已保存: {profiles_file}")
    
    # Generate completion report
    completion_report = {
        "evaluation_completed": True,
        "completion_timestamp": datetime.now().isoformat(),
        "task_id": task_id,
        "total_models": len(model_records),
        "total_samples": len(all_records),
        "models": list(model_records.keys())
    }
    
    completion_file = os.path.join(results_dir, "evaluation_completion.json")
    with open(completion_file, 'w', encoding='utf-8') as f:
        json.dump(completion_report, f, indent=2)
    print(f"  ✅ 已保存: {completion_file}")
    
    print("\n" + "=" * 80)
    print("✅ 评估结果最终化完成！")
    print("=" * 80)
    print(f"\n生成的文件:")
    print(f"  - {records_file}")
    print(f"  - {summaries_file}")
    print(f"  - {profiles_file}")
    print(f"  - {completion_file}")
    print(f"\n下一步: 生成LaTeX表格和论文结果")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="最终化评估结果")
    parser.add_argument("--task", type=str, default="S1", help="任务ID")
    parser.add_argument("--results_dir", type=str, default="results/final_official_v1.0.0_llm_judge", help="结果目录")
    
    args = parser.parse_args()
    
    finalize_evaluation_results(
        results_dir=args.results_dir,
        task_id=args.task
    )

