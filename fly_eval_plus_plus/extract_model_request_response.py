"""
提取完整的模型请求和回复数据

从原始模型输出文件中提取与评估记录对应的完整请求和回复。
"""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def find_model_output_file(model_name: str, task_id: str = "S1"):
    """
    查找模型输出文件
    
    Args:
        model_name: 模型名称
        task_id: 任务ID
    
    Returns:
        文件路径或None
    """
    possible_paths = [
        "../data/model_results/S1_20251106_020205",
        "../../model_invocation/results/S1/20251106_020205",
        "data/model_results/S1_20251106_020205",
        "../../../model_invocation/results/S1/20251106_020205"
    ]
    
    for base_path in possible_paths:
        if os.path.exists(base_path):
            model_dir = os.path.join(base_path, model_name)
            if os.path.exists(model_dir):
                # 查找JSONL文件
                jsonl_files = [f for f in os.listdir(model_dir) if f.endswith('.jsonl')]
                if jsonl_files:
                    return os.path.join(model_dir, jsonl_files[0])
    
    return None


def extract_sample_index(sample_id: str):
    """
    从sample_id中提取索引
    
    Args:
        sample_id: 样本ID，格式如 "S1_claude-3-7-sonnet-20250219_1"
    
    Returns:
        索引（从1开始）或None
    """
    parts = sample_id.split('_')
    if len(parts) >= 3:
        try:
            return int(parts[-1])
        except:
            pass
    return None


def load_model_request_response(records_file: str, num_samples: int = 10):
    """
    从评估记录和原始数据中提取完整的模型请求和回复
    
    Args:
        records_file: 评估记录文件路径
        num_samples: 要提取的样本数
    
    Returns:
        包含请求和回复的案例列表
    """
    # 读取评估记录
    records = []
    with open(records_file, 'r') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    
    print(f"读取了 {len(records)} 条评估记录")
    
    # 提取前num_samples条记录
    records = records[:num_samples]
    
    cases = []
    
    for record in records:
        sample_id = record.get('sample_id', '')
        model_name = record.get('model_name', '')
        task_id = record.get('task_id', 'S1')
        
        # 提取索引
        idx = extract_sample_index(sample_id)
        
        if idx is None:
            print(f"⚠️  无法从sample_id提取索引: {sample_id}")
            continue
        
        # 查找模型输出文件
        model_file = find_model_output_file(model_name, task_id)
        
        if model_file is None:
            print(f"⚠️  未找到模型输出文件: {model_name}")
            continue
        
        # 读取原始数据
        try:
            with open(model_file, 'r') as f:
                lines = f.readlines()
                if idx <= len(lines):
                    raw_data = json.loads(lines[idx - 1])  # 索引从1开始
                    
                    # 提取请求和回复
                    question = raw_data.get('question', '')
                    response = raw_data.get('response', '')
                    
                    # 从question中提取current_state（上一秒数据）
                    import re
                    current = {}
                    
                    # 找到"上一秒数据："后面的JSON
                    start_marker = "上一秒数据："
                    start_idx = question.find(start_marker)
                    if start_idx != -1:
                        json_start = question.find('{', start_idx)
                        if json_start != -1:
                            # 找到匹配的}
                            brace_count = 0
                            end_idx = json_start
                            for i in range(json_start, len(question)):
                                if question[i] == '{':
                                    brace_count += 1
                                elif question[i] == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        end_idx = i + 1
                                        break
                            
                            if end_idx > json_start:
                                json_str = question[json_start:end_idx]
                                try:
                                    current = json.loads(json_str)
                                except:
                                    pass
                    
                    # 如果没有提取到，尝试从raw_data中获取
                    if not current:
                        current = raw_data.get('current', {})
                    
                    # Ground truth - 从参考数据文件中加载
                    next_second = {}
                    ref_files = [
                        "data/reference_data/next_second_pairs.jsonl",
                        "../data/reference_data/next_second_pairs.jsonl",
                        "../../flight_prediction/next_second_pairs.jsonl"
                    ]
                    ref_file = None
                    for path in ref_files:
                        if os.path.exists(path):
                            ref_file = path
                            break
                    
                    if ref_file and idx:
                        try:
                            with open(ref_file, 'r') as f:
                                ref_lines = f.readlines()
                                if idx <= len(ref_lines):
                                    ref_data = json.loads(ref_lines[idx - 1])  # 索引从1开始
                                    next_second = ref_data.get('next_second', {})
                        except:
                            pass
                    
                    # 如果参考数据中没有，尝试从raw_data中获取
                    if not next_second:
                        next_second = raw_data.get('next_second', {})
                    
                    # 获取评估结果
                    llm_output = record.get('optional_scores', {}).get('llm_judge_output', {})
                    overall_grade = llm_output.get('overall_grade', 'N/A')
                    total_score = record.get('optional_scores', {}).get('total_score', 0)
                    grade_vector = llm_output.get('grade_vector', {})
                    
                    case = {
                        'sample_id': sample_id,
                        'model_name': model_name,
                        'index': idx,
                        'overall_grade': overall_grade,
                        'total_score': total_score,
                        'grade_vector': grade_vector,
                        'request': {
                            'question': question,
                            'current_state': current
                        },
                        'response': response,
                        'ground_truth': next_second,
                        'evaluation_result': {
                            'protocol_result': record.get('protocol_result', {}),
                            'adjudication': record.get('agent_output', {}).get('adjudication', 'unknown'),
                            'critical_findings': llm_output.get('critical_findings', [])
                        }
                    }
                    
                    cases.append(case)
                    print(f"✅ 提取样本 {idx}: {sample_id} ({overall_grade}, {total_score:.2f}分)")
                else:
                    print(f"⚠️  索引 {idx} 超出范围（文件共 {len(lines)} 行）")
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            continue
    
    return cases


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="提取完整的模型请求和回复")
    parser.add_argument("--records_file", type=str, 
                       default="results/final_official_v1.0.0_llm_judge/records_S1_incremental.jsonl",
                       help="评估记录文件路径")
    parser.add_argument("--num_samples", type=int, default=10, help="要提取的样本数")
    parser.add_argument("--output_file", type=str,
                       default="results/final_official_v1.0.0_llm_judge/model_request_response_cases.json",
                       help="输出文件路径")
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("提取完整的模型请求和回复")
    print("=" * 80)
    
    cases = load_model_request_response(args.records_file, args.num_samples)
    
    # 保存结果
    os.makedirs(os.path.dirname(args.output_file), exist_ok=True)
    with open(args.output_file, 'w', encoding='utf-8') as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 已保存 {len(cases)} 个案例到: {args.output_file}")
    print(f"\n案例统计:")
    from collections import Counter
    grade_dist = Counter(case['overall_grade'] for case in cases)
    print(f"  等级分布: {dict(grade_dist)}")

