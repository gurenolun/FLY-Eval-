#!/usr/bin/env python3
"""
生成包含所有5个维度指标的LaTeX表格
基于确定性评估结果
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

def load_results(task_id: str, results_dir: str) -> Dict[str, Any]:
    """加载评估结果"""
    results_path = Path(results_dir)
    task_dir = results_path / task_id
    
    # 如果task_id目录不存在，尝试查找task_summary_{task_id}_deterministic.json
    if not task_dir.exists():
        task_summary_file_alt = results_path / f"task_summary_{task_id}_deterministic.json"
        if task_summary_file_alt.exists():
            # 使用原始文件结构
            task_dir = results_path
    
    # 加载任务摘要
    task_summary_file = task_dir / "task_summary.json"
    if not task_summary_file.exists():
        # 尝试查找task_summary_{task_id}_deterministic.json
        task_summary_file = results_path / f"task_summary_{task_id}_deterministic.json"
        if not task_summary_file.exists():
            return None
    
    with open(task_summary_file, 'r', encoding='utf-8') as f:
        task_summary = json.load(f)
    
    # 加载所有模型的记录
    model_profiles = {}
    model_profiles_file = task_dir / "model_profiles.json"
    if not model_profiles_file.exists():
        # 尝试查找model_profiles_{task_id}_deterministic.json
        model_profiles_file = results_path / f"model_profiles_{task_id}_deterministic.json"
    
    if model_profiles_file.exists():
        with open(model_profiles_file, 'r', encoding='utf-8') as f:
            model_profiles = json.load(f)
    
    # 从每个模型的目录加载详细记录
    model_records = {}
    # 首先尝试从task_id目录下的模型子目录加载
    if (task_dir / task_id).exists():
        task_model_dir = task_dir / task_id
    else:
        task_model_dir = task_dir
    
    for model_dir in task_model_dir.iterdir():
        if not model_dir.is_dir():
            continue
        
        model_name = model_dir.name
        records_file = model_dir / "records.jsonl"
        
        if records_file.exists():
            records = []
            with open(records_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))
            model_records[model_name] = records
    
    # 如果从模型目录加载失败，尝试从records_{task_id}_deterministic.jsonl加载
    if not model_records:
        records_file = results_path / f"records_{task_id}_deterministic.jsonl"
        if records_file.exists():
            # 按模型分组
            records_by_model = defaultdict(list)
            with open(records_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        model_name = record.get('model_name')
                        if model_name:
                            records_by_model[model_name].append(record)
            model_records = dict(records_by_model)
    
    return {
        'task_summary': task_summary,
        'model_profiles': model_profiles,
        'model_records': model_records
    }

def calculate_model_metrics(model_records: List[Dict], task_id: str) -> Dict[str, Any]:
    """计算模型指标"""
    if not model_records:
        return {}
    
    # 统计维度分数
    dimension_scores = defaultdict(list)
    total_scores = []
    eligible_count = 0
    total_count = len(model_records)
    
    # Availability rate统计
    availability_scores = []
    
    # MAE和RMSE（仅eligible样本）
    mae_scores = []
    rmse_scores = []
    
    for record in model_records:
        # 统计eligible
        if record.get('agent_output', {}).get('adjudication') == 'eligible':
            eligible_count += 1
        
        # 提取availability rate
        protocol_result = record.get('protocol_result', {})
        field_completeness = protocol_result.get('field_completeness', {})
        completeness_rate = field_completeness.get('completeness_rate', 0.0)
        if completeness_rate is not None:
            # completeness_rate已经是百分比（0-100），直接使用
            availability_scores.append(completeness_rate)
        
        # 提取维度分数（从所有记录，不仅仅是eligible）
        optional_scores = record.get('optional_scores', {})
        if optional_scores:
            # 维度分数（scaled to 0-100）
            dim_scores_scaled = optional_scores.get('dimension_scores_scaled', {})
            if dim_scores_scaled:
                for dim, score in dim_scores_scaled.items():
                    if score is not None:
                        dimension_scores[dim].append(score)
            else:
                # 如果没有scaled版本，尝试从dimension_scores计算（0-1范围）
                dim_scores = optional_scores.get('dimension_scores', {})
                if dim_scores:
                    for dim, score in dim_scores.items():
                        if score is not None:
                            dimension_scores[dim].append(score * 100.0)  # 转换为0-100
            
            # 总分
            total_score = optional_scores.get('total_score', 0)
            if total_score is not None:
                total_scores.append(total_score)
            
            # MAE和RMSE分数（从所有样本提取，不仅仅是eligible）
            # 因为predictive_quality_score是从所有样本计算的
            mae_score = optional_scores.get('mae_score', None)
            rmse_score = optional_scores.get('rmse_score', None)
            # 检查值是否存在（0可能是有效值，但None表示没有计算）
            if mae_score is not None:
                mae_scores.append(mae_score)
            if rmse_score is not None:
                rmse_scores.append(rmse_score)
                
                # 尝试从trace或其他地方获取原始nMAE和nRMSE值
                # 如果没有，我们使用分数值（但标注为分数）
                # 注意：原始值可能需要从model_profiles中获取
    
    # 计算平均值
    metrics = {
        'total_samples': total_count,
        'eligible_samples': eligible_count,
        'eligibility_rate': (eligible_count / total_count * 100) if total_count > 0 else 0.0,
        'average_total_score': sum(total_scores) / len(total_scores) if total_scores else 0.0,
        'average_availability_rate': sum(availability_scores) / len(availability_scores) if availability_scores else 0.0,
    }
    
    # 各维度平均分（维度名称映射）
    dim_name_map = {
        'protocol_schema_compliance': 'protocol_score',
        'field_validity_local_dynamics': 'field_score',
        'physics_cross_field_consistency': 'physics_score',
        'safety_constraint_satisfaction': 'safety_score',
        'predictive_quality_reliability': 'predictive_score'
    }
    
    for dim, scores in dimension_scores.items():
        if scores:
            avg_score = sum(scores) / len(scores)
            # 使用简短的名称
            short_name = dim_name_map.get(dim, dim.replace('_', '_'))
            metrics[f'avg_{short_name}'] = avg_score
        else:
            short_name = dim_name_map.get(dim, dim.replace('_', '_'))
            metrics[f'avg_{short_name}'] = 0.0
    
    # MAE和RMSE平均分（仅eligible样本）
    if mae_scores:
        metrics['avg_mae_score'] = sum(mae_scores) / len(mae_scores)
    else:
        metrics['avg_mae_score'] = 0.0
    
    if rmse_scores:
        metrics['avg_rmse_score'] = sum(rmse_scores) / len(rmse_scores)
    else:
        metrics['avg_rmse_score'] = 0.0
    
    return metrics

def generate_latex_table(results_dir: str, output_file: str):
    """生成LaTeX表格"""
    
    # 加载所有任务的结果
    tasks = ['S1', 'M1', 'M3']
    all_task_results = {}
    
    for task_id in tasks:
        result = load_results(task_id, results_dir)
        if result:
            all_task_results[task_id] = result
        else:
            print(f"⚠️  任务 {task_id} 的结果不存在，跳过")
    
    if not all_task_results:
        print("❌ 没有找到任何评估结果")
        return
    
    # 收集所有模型名称
    all_models = set()
    for task_result in all_task_results.values():
        all_models.update(task_result['model_profiles'].keys())
    
    all_models = sorted(all_models)
    
    # 计算每个模型在每个任务上的指标
    model_metrics = {}
    for model_name in all_models:
        model_metrics[model_name] = {}
        for task_id in tasks:
            if task_id in all_task_results:
                task_result = all_task_results[task_id]
                if model_name in task_result['model_records']:
                    records = task_result['model_records'][model_name]
                    metrics = calculate_model_metrics(records, task_id)
                    model_metrics[model_name][task_id] = metrics
                else:
                    model_metrics[model_name][task_id] = None
    
    # 生成LaTeX表格
    latex_lines = []
    latex_lines.append("\\begin{table*}[!htbp]")
    latex_lines.append("    \\centering")
    latex_lines.append("    \\footnotesize  % 使用footnotesize字体（比small更小）")
    latex_lines.append("    \\caption{FLY-EVAL++ Comprehensive Model Performance Analysis}")
    latex_lines.append("    \\label{tab:fly_eval_comprehensive}")
    latex_lines.append("    We utilize \\resultone{green} (1st), \\resulttwo{cyan}~(2nd), and \\resultthird{yellow} (3rd) backgrounds to distinguish the top three results within different metrics. This table presents comprehensive evaluation results across 5 dimensions: Protocol/Schema Compliance, Field Validity \\& Local Dynamics, Physics/Cross-field Consistency, Safety Constraint Satisfaction, and Predictive Quality \\& Reliability. The overall score is the arithmetic mean of all 5 dimension scores.")
    latex_lines.append("    \\fbox{%")
    
    # 表头（移除eligible和available，扩展5个维度，预测值显示nMAE和nRMSE子栏）
    latex_lines.append("    \\begin{tabular}{@{}l|ccccc|cc|c@{}}")
    latex_lines.append("    % \\toprule")
    latex_lines.append("    \\multirow{3}{*}{\\textbf{Model}} & \\multicolumn{5}{c|}{\\textbf{5-Dimension Scores}} & \\multicolumn{2}{c|}{\\textbf{Predictive Quality}} & \\multirow{3}{*}{\\textbf{Total}} \\\\")
    latex_lines.append("    \\cmidrule(lr){2-6} \\cmidrule(lr){7-8}")
    latex_lines.append("    & \\textbf{Proto.} & \\textbf{Field} & \\textbf{Phys.} & \\textbf{Safety} & \\textbf{Pred.} & \\textbf{nMAE} & \\textbf{nRMSE} & \\\\")
    latex_lines.append("    & \\textbf{Score} & \\textbf{Score} & \\textbf{Score} & \\textbf{Score} & \\textbf{Score} & \\textbf{Score} & \\textbf{Score} & \\\\")
    latex_lines.append("    \\midrule")
    
    # 为每个任务生成表格行
    for task_id in tasks:
        if task_id not in all_task_results:
            continue
        
        latex_lines.append(f"    \\multicolumn{{8}}{{l}}{{\\textit{{{task_id} Task}}}} \\\\")
        
        # 按总分排序模型
        task_models = []
        for model_name in all_models:
            if model_name in model_metrics and task_id in model_metrics[model_name]:
                metrics = model_metrics[model_name][task_id]
                if metrics:
                    task_models.append((model_name, metrics.get('average_total_score', 0)))
        
        task_models.sort(key=lambda x: x[1], reverse=True)
        
        # 获取前三名用于高亮
        top3_scores = [x[1] for x in task_models[:3]] if len(task_models) >= 3 else []
        
        for rank, (model_name, total_score) in enumerate(task_models, 1):
            metrics = model_metrics[model_name][task_id]
            
            # 格式化模型名称
            model_display = model_name.replace('_', '-').replace('claude-3-7-sonnet-20250219', 'claude-3-7').replace('claude-sonnet-4-5-20250929', 'claude-sonnet-4-5')
            
            # 提取指标（移除eligible和available）
            proto_score = metrics.get('avg_protocol_score', metrics.get('avg_protocol_schema_compliance', 0.0))
            field_score = metrics.get('avg_field_score', metrics.get('avg_field_validity_local_dynamics', 0.0))
            phys_score = metrics.get('avg_physics_score', metrics.get('avg_physics_cross_field_consistency', 0.0))
            safety_score = metrics.get('avg_safety_score', metrics.get('avg_safety_constraint_satisfaction', 0.0))
            pred_score = metrics.get('avg_predictive_score', metrics.get('avg_predictive_quality_reliability', 0.0))
            
            # nMAE和nRMSE分数（仅eligible样本的平均值）
            mae_score_avg = metrics.get('avg_mae_score', 0.0)
            rmse_score_avg = metrics.get('avg_rmse_score', 0.0)
            
            total = metrics.get('average_total_score', 0.0)
            
            # 高亮前三名
            highlight_start = ""
            highlight_end = ""
            if rank <= 3 and total_score in top3_scores:
                if rank == 1:
                    highlight_start = "\\resultone{"
                    highlight_end = "}"
                elif rank == 2:
                    highlight_start = "\\resulttwo{"
                    highlight_end = "}"
                elif rank == 3:
                    highlight_start = "\\resultthird{"
                    highlight_end = "}"
            
            # 生成行（格式化数字，移除eligible和available列）
            row = f"    {model_display} & {proto_score:.1f} & {field_score:.1f} & {phys_score:.1f} & {safety_score:.1f} & {pred_score:.1f} & {mae_score_avg:.1f} & {rmse_score_avg:.1f} & {highlight_start}{total:.2f}{highlight_end} \\\\"
            latex_lines.append(row)
        
        latex_lines.append("    \\hline")
    
    latex_lines.append("    \\end{tabular}")
    latex_lines.append("    }")
    latex_lines.append("\\end{table*}")
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(latex_lines))
    
    print(f"✅ LaTeX表格已生成: {output_file}")
    print(f"   包含 {len(all_models)} 个模型，{len(all_task_results)} 个任务")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="生成包含所有维度指标的LaTeX表格")
    parser.add_argument("--results_dir", type=str, default="./results/deterministic", help="结果目录")
    parser.add_argument("--output", type=str, default="./results/deterministic/comprehensive_table.tex", help="输出文件")
    
    args = parser.parse_args()
    
    generate_latex_table(args.results_dir, args.output)

if __name__ == "__main__":
    main()
