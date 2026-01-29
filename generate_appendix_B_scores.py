#!/usr/bin/env python3
"""
生成附录B的45个额外模型的5维度评分表格
使用deterministic_v7_physics_fixed方法
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

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
    """从文件名提取模型名称"""
    # 移除_test_results_20250612_*.jsonl后缀
    name = filename.replace('_test_results_20250612_', '_').replace('.jsonl', '')
    
    # 处理特殊前缀
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
    
    # 替换下划线为连字符（除了Pro-和LoRA-等前缀后的）
    parts = name.split('_')
    if len(parts) > 1:
        # 保持前缀格式
        if parts[0].startswith('Pro-') or parts[0].startswith('LoRA-'):
            name = parts[0] + '-' + '-'.join(parts[1:])
        else:
            name = '-'.join(parts)
    
    return name.lower()

def load_model_results(results_dir):
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

def main():
    # 读取merged_results数据
    results_dir = '/Users/aaron/Desktop/flight_prediction/ICML2026/data/model_results/merged_results_20250617_203957'
    print("Loading model results...")
    model_data = load_model_results(results_dir)
    
    # 识别额外模型（不在21个SOTA中）
    additional_models = {k: v for k, v in model_data.items() if k not in SOTA_MODELS}
    print(f"\nTotal models: {len(model_data)}")
    print(f"Additional models (not in 21 SOTA): {len(additional_models)}")
    
    # 这里需要运行deterministic评估来计算5个维度分数
    # 由于需要完整的评估流程，我先输出模型列表
    print("\nAdditional models found:")
    for i, model_name in enumerate(sorted(additional_models.keys())[:10], 1):
        count = len(additional_models[model_name])
        print(f"{i}. {model_name}: {count} samples")
    
    print("\n⚠️  Note: Need to run deterministic evaluation to calculate 5-dimension scores")
    print("   This requires ground truth data and evaluation pipeline")

if __name__ == '__main__':
    main()
