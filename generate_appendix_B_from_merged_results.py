#!/usr/bin/env python3
"""
从merged_results生成附录B的45个额外模型的5维度评分表格
使用deterministic_v7_physics_fixed方法评估
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from fly_eval_plus_plus.main import FLYEvalPlusPlus
    from fly_eval_plus_plus.fusion.rule_based_fusion_aligned import RuleBasedFusionAligned
    from fly_eval_plus_plus.data_loader import DataLoader
    from fly_eval_plus_plus.core.data_structures import Sample, ModelOutput
except ImportError:
    print("⚠️  Cannot import evaluation modules. Need to run evaluation separately.")
    sys.exit(1)

# 21个SOTA模型列表（用于排除）
SOTA_MODELS = [
    'gemini-3-pro-preview', 'deepseek-r1-250528', 'gpt-5', 'o4-mini', 
    'kimi-k2-thinking', 'gemini-2.5-pro', 'llama-3.1-405b-instruct',
    'kimi-k2-250905', 'claude-sonnet-4-5-20250929', 'grok-4',
    'deepseek-v3.1', 'claude-3-7-sonnet-20250219', 'glm-4.6',
    'deepseek-v3.2-exp', 'deepseek-v3', 'gpt-4o', 'doubao-seed-1-6-251015',
    'qwen3-32b', 'qwen3-235b-a22b', 'qwen2.5-32b-instruct', 'qwen3-next-80b-a3b-instruct'
]

def extract_model_name_from_filename(filename):
    """从文件名提取标准化的模型名称"""
    # 移除_test_results_20250612_*.jsonl后缀
    name = filename.replace('_test_results_20250612_', '_').replace('.jsonl', '')
    
    # 处理特殊前缀和格式
    if name.startswith('LoRA_Qwen_'):
        name = name.replace('LoRA_Qwen_', 'LoRA-Qwen-')
    elif name.startswith('Pro_'):
        name = name.replace('Pro_', 'Pro-')
    elif name.startswith('THUDM_'):
        name = name.replace('THUDM_', 'THUDM-')
    elif name.startswith('Qwen_'):
        name = name.replace('Qwen_', 'Qwen-')
    elif name.startswith('deepseek-ai_'):
        name = name.replace('deepseek-ai_', 'deepseek-ai-')
    
    # 替换下划线为连字符
    name = name.replace('_', '-').lower()
    
    return name

def load_merged_results(results_dir):
    """加载merged_results目录下的所有模型数据"""
    model_data = {}
    all_files = [f for f in os.listdir(results_dir) if f.endswith('.jsonl')]
    
    for filename in all_files:
        model_name = extract_model_name_from_filename(filename)
        file_path = os.path.join(results_dir, filename)
        
        records = []
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))
            model_data[model_name] = records
        except Exception as e:
            print(f"Error reading {filename}: {e}")
    
    return model_data

def calculate_dimension_scores_from_records(records):
    """从records计算5个维度的平均分数"""
    dimension_scores = defaultdict(list)
    
    for record in records:
        if 'optional_scores' in record and record['optional_scores']:
            dim_scores = record['optional_scores'].get('dimension_scores', {})
            if dim_scores:
                for dim, score in dim_scores.items():
                    if isinstance(score, (int, float)):
                        dimension_scores[dim].append(score)
    
    # 计算平均值并转换为百分比
    avg_scores = {}
    dim_mapping = {
        'protocol_schema_compliance': 'Protocol',
        'field_validity_local_dynamics': 'Field',
        'physics_cross_field_consistency': 'Physics',
        'safety_constraint_satisfaction': 'Safety',
        'predictive_quality_reliability': 'Predictive'
    }
    
    for dim_key, dim_label in dim_mapping.items():
        scores = dimension_scores.get(dim_key, [])
        if scores:
            avg = sum(scores) / len(scores) * 100  # 转换为百分比
            avg_scores[dim_label] = avg
        else:
            avg_scores[dim_label] = 0.0
    
    # 计算总分（5个维度平均）
    total = sum(avg_scores.values()) / len(avg_scores) if avg_scores else 0.0
    
    return avg_scores, total

def main():
    results_dir = '/Users/aaron/Desktop/flight_prediction/ICML2026/data/model_results/merged_results_20250617_203957'
    
    print("Loading merged results...")
    model_data = load_merged_results(results_dir)
    
    # 识别额外模型
    additional_models = {k: v for k, v in model_data.items() if k not in SOTA_MODELS}
    print(f"\nTotal models: {len(model_data)}")
    print(f"Additional models: {len(additional_models)}")
    
    # 计算每个模型的5个维度分数
    model_scores = {}
    for model_name, records in additional_models.items():
        dim_scores, total = calculate_dimension_scores_from_records(records)
        model_scores[model_name] = {
            'dimensions': dim_scores,
            'total': total,
            'sample_count': len(records)
        }
    
    # 按总分排序
    sorted_models = sorted(model_scores.items(), key=lambda x: x[1]['total'], reverse=True)
    
    print(f"\n✅ Calculated scores for {len(sorted_models)} additional models")
    print("\nTop 5 models:")
    for i, (model, scores) in enumerate(sorted_models[:5], 1):
        print(f"{i}. {model}: Total={scores['total']:.2f}, "
              f"Proto={scores['dimensions'].get('Protocol', 0):.1f}, "
              f"Field={scores['dimensions'].get('Field', 0):.1f}, "
              f"Physics={scores['dimensions'].get('Physics', 0):.1f}, "
              f"Safety={scores['dimensions'].get('Safety', 0):.1f}, "
              f"Pred={scores['dimensions'].get('Predictive', 0):.1f}")
    
    # 生成LaTeX表格
    generate_latex_table(sorted_models)

def generate_latex_table(sorted_models):
    """生成LaTeX表格代码"""
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
        dims = scores['dimensions']
        proto = dims.get('Protocol', 0)
        field = dims.get('Field', 0)
        phys = dims.get('Physics', 0)
        safety = dims.get('Safety', 0)
        pred = dims.get('Predictive', 0)
        total = scores['total']
        
        # 格式化模型名称（转义下划线）
        model_display = model_name.replace('_', '\\_').replace('-', ' ')
        model_display = model_display.title()
        
        latex_lines.append(f"        {model_display:30s} & {proto:5.1f} & {field:5.1f} & {phys:5.1f} & {safety:5.1f} & {pred:5.1f} & {total:5.2f} \\\\")
    
    latex_lines.append("        \\bottomrule")
    latex_lines.append("      \\end{tabular}")
    latex_lines.append("    \\end{sc}")
    latex_lines.append("  \\end{tiny}")
    latex_lines.append("}%")
    latex_lines.append("\\vskip -0.1in")
    latex_lines.append("\\end{table}")
    
    # 保存到文件
    output_file = '/Users/aaron/Desktop/flight_prediction/ICML2026/appendix_B_table_generated.tex'
    with open(output_file, 'w') as f:
        f.write('\n'.join(latex_lines))
    
    print(f"\n✅ Generated LaTeX table: {output_file}")

if __name__ == '__main__':
    main()
