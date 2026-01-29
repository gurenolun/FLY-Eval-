#!/usr/bin/env python3
"""
生成附录B的45个额外模型的5维度评分表格
从deterministic评估结果中提取分数
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict

# 21个SOTA模型列表（用于排除）
SOTA_MODELS = [
    'gemini-3-pro-preview', 'deepseek-r1-250528', 'gpt-5', 'o4-mini', 
    'kimi-k2-thinking', 'gemini-2.5-pro', 'llama-3.1-405b-instruct',
    'kimi-k2-250905', 'claude-sonnet-4-5-20250929', 'grok-4',
    'deepseek-v3.1', 'claude-3-7-sonnet-20250219', 'glm-4.6',
    'deepseek-v3.2-exp', 'deepseek-v3', 'gpt-4o', 'doubao-seed-1-6-251015',
    'qwen3-32b', 'qwen3-235b-a22b', 'qwen2.5-32b-instruct', 'qwen3-next-80b-a3b-instruct'
]

def extract_dimension_scores_from_records(records_file):
    """从records文件中提取所有模型的5个维度分数"""
    model_dimension_scores = defaultdict(lambda: defaultdict(list))
    
    if not os.path.exists(records_file):
        return {}
    
    print(f"Reading records from: {records_file}")
    with open(records_file, 'r') as f:
        for line_num, line in enumerate(f):
            if line.strip():
                try:
                    data = json.loads(line)
                    model_name = data.get('model_name', '')
                    
                    if 'optional_scores' in data and data['optional_scores']:
                        dim_scores = data['optional_scores'].get('dimension_scores', {})
                        if dim_scores:
                            for dim, score in dim_scores.items():
                                if isinstance(score, (int, float)):
                                    model_dimension_scores[model_name][dim].append(score)
                except Exception as e:
                    if line_num < 5:  # 只打印前几个错误
                        print(f"  Warning: Error parsing line {line_num}: {e}")
                    continue
    
    # 计算每个模型的平均分数
    model_avg_scores = {}
    dim_mapping = {
        'protocol_schema_compliance': 'Protocol',
        'field_validity_local_dynamics': 'Field',
        'physics_cross_field_consistency': 'Physics',
        'safety_constraint_satisfaction': 'Safety',
        'predictive_quality_reliability': 'Predictive'
    }
    
    for model_name, dim_scores in model_dimension_scores.items():
        avg_scores = {}
        for dim_key, dim_label in dim_mapping.items():
            scores = dim_scores.get(dim_key, [])
            if scores:
                avg = sum(scores) / len(scores) * 100  # 转换为百分比
                avg_scores[dim_label] = avg
            else:
                avg_scores[dim_label] = 0.0
        
        # 计算总分（5个维度平均）
        total = sum(avg_scores.values()) / len(avg_scores) if avg_scores else 0.0
        avg_scores['Total'] = total
        
        model_avg_scores[model_name] = avg_scores
    
    return model_avg_scores

def format_model_name_for_latex(model_name):
    """格式化模型名称用于LaTeX显示"""
    # 将模型名称转换为显示格式
    # 例如: "loRA-qwen-qwen2.5-32b-instruct" -> "LoRA-Qwen-Qwen2.5-32B"
    
    # 处理特殊前缀
    if model_name.startswith('lora-'):
        model_name = model_name.replace('lora-', 'LoRA-')
    elif model_name.startswith('pro-'):
        model_name = model_name.replace('pro-', 'Pro-')
    elif model_name.startswith('thudm-'):
        model_name = model_name.replace('thudm-', 'THUDM-')
    
    # 分割并格式化各部分
    parts = model_name.split('-')
    formatted_parts = []
    for part in parts:
        if part.isdigit():
            formatted_parts.append(part)
        elif len(part) <= 3:
            formatted_parts.append(part.upper())
        else:
            formatted_parts.append(part.capitalize())
    
    return '-'.join(formatted_parts)

def generate_latex_table(model_scores_dict, output_file):
    """生成LaTeX表格"""
    # 按总分排序
    sorted_models = sorted(model_scores_dict.items(), key=lambda x: x[1].get('Total', 0), reverse=True)
    
    latex_lines = []
    latex_lines.append("\\begin{table}[H]")
    latex_lines.append("\\centering")
    latex_lines.append("\\caption{Extended Model Evaluation: 45 Additional Models on S1 Task}")
    latex_lines.append("\\label{tab:extended_models}")
    latex_lines.append("\\vskip 0.1in")
    latex_lines.append("\\resizebox{\\columnwidth}{!}{%")
    latex_lines.append("  \\begin{tiny}")
    latex_lines.append("    \\setlength{\\tabcolsep}{2pt}")
    latex_lines.append("    \\begin{sc}")
    latex_lines.append("      \\begin{tabular}{lcccccc}")
    latex_lines.append("        \\toprule")
    latex_lines.append("        Model & Proto. & Field & Phys. & Safety & Pred. & Total \\\\")
    latex_lines.append("        \\midrule")
    
    for model_name, scores in sorted_models:
        proto = scores.get('Protocol', 0)
        field = scores.get('Field', 0)
        phys = scores.get('Physics', 0)
        safety = scores.get('Safety', 0)
        pred = scores.get('Predictive', 0)
        total = scores.get('Total', 0)
        
        # 格式化模型名称
        model_display = format_model_name_for_latex(model_name)
        # 转义下划线
        model_display = model_display.replace('_', '\\_')
        
        latex_lines.append(f"        {model_display:35s} & {proto:5.1f} & {field:5.1f} & {phys:5.1f} & {safety:5.1f} & {pred:5.1f} & {total:5.2f} \\\\")
    
    latex_lines.append("        \\bottomrule")
    latex_lines.append("      \\end{tabular}")
    latex_lines.append("    \\end{sc}")
    latex_lines.append("  \\end{tiny}")
    latex_lines.append("}%")
    latex_lines.append("\\vskip -0.1in")
    latex_lines.append("\\end{table}")
    
    with open(output_file, 'w') as f:
        f.write('\n'.join(latex_lines))
    
    print(f"\n✅ Generated LaTeX table: {output_file}")

def main():
    # 检查可能的评估结果文件
    possible_records_files = [
        '/Users/aaron/Desktop/flight_prediction/ICML2026/results/all_46_models_v7_physics_fixed/records_S1_deterministic.jsonl',
        '/Users/aaron/Desktop/flight_prediction/ICML2026/results/deterministic/records_S1_deterministic.jsonl',
    ]
    
    all_model_scores = {}
    
    for records_file in possible_records_files:
        if os.path.exists(records_file) and os.path.getsize(records_file) > 0:
            print(f"\n📊 Processing: {records_file}")
            model_scores = extract_dimension_scores_from_records(records_file)
            
            # 只保留额外模型（不在21个SOTA中）
            additional_scores = {k: v for k, v in model_scores.items() if k not in SOTA_MODELS}
            all_model_scores.update(additional_scores)
            
            print(f"   Found {len(additional_scores)} additional models with scores")
    
    if not all_model_scores:
        print("\n⚠️  No evaluation results found for additional models.")
        print("   Need to run evaluation first:")
        print("   python3 run_46_models_evaluation.py")
        return
    
    print(f"\n✅ Total additional models with scores: {len(all_model_scores)}")
    
    # 显示前5个模型
    sorted_models = sorted(all_model_scores.items(), key=lambda x: x[1].get('Total', 0), reverse=True)
    print("\nTop 5 additional models:")
    for i, (model, scores) in enumerate(sorted_models[:5], 1):
        print(f"{i}. {model}: Total={scores.get('Total', 0):.2f}, "
              f"Proto={scores.get('Protocol', 0):.1f}, "
              f"Field={scores.get('Field', 0):.1f}, "
              f"Physics={scores.get('Physics', 0):.1f}, "
              f"Safety={scores.get('Safety', 0):.1f}, "
              f"Pred={scores.get('Predictive', 0):.1f}")
    
    # 生成LaTeX表格
    output_file = '/Users/aaron/Desktop/flight_prediction/ICML2026/icml2026/content/appendix_B_table_generated.tex'
    generate_latex_table(all_model_scores, output_file)

if __name__ == '__main__':
    main()
