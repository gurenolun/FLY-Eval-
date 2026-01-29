"""
Generate Progress Report for Running Evaluation

生成评估进度报告，包括已完成模型、统计信息等。
"""

import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path


def generate_progress_report(results_dir: str = "results/final_official_v1.0.0_llm_judge",
                             task_id: str = "S1",
                             total_models: int = 21,
                             samples_per_model: int = 100):
    """
    Generate progress report for running evaluation
    
    Args:
        results_dir: Results directory
        task_id: Task ID
        total_models: Total number of models
        samples_per_model: Samples per model
    """
    incremental_file = os.path.join(results_dir, f"records_{task_id}_incremental.jsonl")
    
    if not os.path.exists(incremental_file):
        print(f"⚠️  增量文件不存在: {incremental_file}")
        return
    
    # Load records
    records = []
    with open(incremental_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    
    # Group by model
    model_records = {}
    for record in records:
        model_name = record.get('model_name', 'unknown')
        if model_name not in model_records:
            model_records[model_name] = []
        model_records[model_name].append(record)
    
    # Generate report
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("FLY-EVAL++ 评估进度报告")
    report_lines.append("=" * 80)
    report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"任务: {task_id}")
    report_lines.append("")
    report_lines.append(f"总记录数: {len(records)}")
    report_lines.append(f"已完成模型数: {len(model_records)} / {total_models}")
    report_lines.append(f"模型完成进度: {len(model_records)/total_models*100:.1f}%")
    report_lines.append(f"样本完成数: {len(records)} / {total_models * samples_per_model}")
    report_lines.append(f"样本完成进度: {len(records)/(total_models * samples_per_model)*100:.1f}%")
    report_lines.append("")
    report_lines.append("=" * 80)
    report_lines.append("模型详情")
    report_lines.append("=" * 80)
    
    for model_name, model_recs in sorted(model_records.items()):
        report_lines.append(f"\n{model_name} ({len(model_recs)} 条记录):")
        
        # LLM Judge统计
        llm_outputs = []
        total_scores = []
        for rec in model_recs:
            scores = rec.get('optional_scores', {})
            if 'llm_judge_output' in scores:
                llm_outputs.append(scores['llm_judge_output'])
            if 'total_score' in scores:
                total_scores.append(scores['total_score'])
        
        if llm_outputs:
            # 等级分布
            grade_dist = Counter(llm['overall_grade'] for llm in llm_outputs)
            report_lines.append(f"  等级分布: {dict(grade_dist)}")
            
            # 平均分数
            avg_score = sum(total_scores) / len(total_scores) if total_scores else 0
            report_lines.append(f"  平均总分: {avg_score:.2f}")
            
            # Token统计
            total_tokens = 0
            total_prompt_tokens = 0
            total_completion_tokens = 0
            for llm in llm_outputs:
                api_meta = llm.get('judge_metadata', {}).get('api_request_response', {})
                usage = api_meta.get('response', {}).get('usage')
                if usage:
                    total_tokens += usage.get('total_tokens', 0)
                    total_prompt_tokens += usage.get('prompt_tokens', 0)
                    total_completion_tokens += usage.get('completion_tokens', 0)
            
            if total_tokens > 0:
                report_lines.append(f"  Token使用: prompt={total_prompt_tokens}, completion={total_completion_tokens}, total={total_tokens}")
                report_lines.append(f"  平均Token/样本: {total_tokens/len(llm_outputs):.0f}")
        
        # Eligibility统计
        eligible_count = sum(1 for rec in model_recs if rec.get('agent_output', {}).get('adjudication') == 'eligible')
        report_lines.append(f"  Eligible样本: {eligible_count}/{len(model_recs)} ({eligible_count/len(model_recs)*100:.1f}%)")
    
    report_lines.append("\n" + "=" * 80)
    
    # Check if evaluation is still running
    import subprocess
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        if 'run_full_evaluation_llm_judge.py' in result.stdout:
            report_lines.append("评估状态: ✅ 正在运行中")
        else:
            report_lines.append("评估状态: ⏸️  已停止")
    except:
        report_lines.append("评估状态: ❓ 无法确定")
    
    report_lines.append("=" * 80)
    
    # Save report
    report_file = os.path.join(results_dir, f"progress_report_{task_id}.md")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print('\n'.join(report_lines))
    print(f"\n✅ 进度报告已保存: {report_file}")
    
    return report_file


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="生成评估进度报告")
    parser.add_argument("--task", type=str, default="S1", help="任务ID")
    parser.add_argument("--total_models", type=int, default=21, help="总模型数")
    parser.add_argument("--samples_per_model", type=int, default=100, help="每模型样本数")
    parser.add_argument("--results_dir", type=str, default="results/final_official_v1.0.0_llm_judge", help="结果目录")
    
    args = parser.parse_args()
    
    generate_progress_report(
        results_dir=args.results_dir,
        task_id=args.task,
        total_models=args.total_models,
        samples_per_model=args.samples_per_model
    )

