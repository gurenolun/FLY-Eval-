#!/usr/bin/env python3
"""
评估merged_results中的46个模型
使用与当前21个SOTA模型相同的评估流程
"""

import json
import os
import sys
from pathlib import Path
from tqdm import tqdm
from collections import defaultdict
import statistics

# 添加路径
sys.path.insert(0, str(Path(__file__).parent / "fly_eval_plus_plus"))

from fly_eval_plus_plus.data_loader import DataLoader
from fly_eval_plus_plus.run_deterministic_evaluation import DeterministicEvaluator
from fly_eval_plus_plus.core.data_structures import Sample, ModelOutput

def run_evaluation():
    """
    运行46个模型的评估
    """
    print("="*80)
    print("评估merged_results中的46个模型")
    print("="*80)
    
    # 配置
    MERGED_RESULTS_DIR = Path("data/model_results/merged_results_20250617_203957")
    OUTPUT_DIR = Path("results/all_46_models_v7_physics_fixed")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    TASK_ID = "S1"
    
    # 初始化评估器
    print(f"\n📊 初始化评估器（任务: {TASK_ID}）")
    det_evaluator = DeterministicEvaluator()
    evaluator = det_evaluator.evaluator  # 使用内部的FLYEvalPlusPlus实例
    
    # 初始化DataLoader
    data_loader = DataLoader()
    
    # 加载reference data (ground truth)
    print("\n📂 加载reference data...")
    reference_data = data_loader.load_reference_data(TASK_ID)
    print(f"   ✅ 加载了 {len(reference_data)} 条reference数据")
    
    # 获取所有模型文件
    model_files = sorted([f for f in MERGED_RESULTS_DIR.glob("*.jsonl") 
                         if f.name != "flight_questions_temp.jsonl"])
    
    print(f"   找到 {len(model_files)} 个模型文件")
    
    # 按模型评估
    all_records = []
    model_summaries = {}
    
    for i, model_file in enumerate(model_files, 1):
        model_name = model_file.stem.replace('_test_results_' + model_file.stem.split('_')[-1], '')
        print(f"\n📊 [{i}/{len(model_files)}] 评估模型: {model_name}")
        
        # 加载模型数据
        samples = []
        model_outputs = []
        
        sample_count = 0
        with open(model_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    
                    # 构建Sample（使用DataLoader的逻辑）
                    sample_id = record.get('id', f"{model_name}_{sample_count}")
                    question = record.get('question', '')
                    
                    # 提取current_state（简化版）
                    current_state = {}
                    try:
                        # 尝试从question中提取上一秒数据
                        import re
                        json_match = re.search(r'上一秒数据[：:]\s*\n?(\{.*?\})', question, re.DOTALL)
                        if json_match:
                            current_state = json.loads(json_match.group(1))
                    except:
                        pass
                    
                    # 获取gold (ground truth)
                    gold = {}
                    gold_available = False
                    if TASK_ID == "S1" and sample_count < len(reference_data):
                        ref_record = reference_data[sample_count]
                        gold = {
                            "next_second": ref_record.get('next_second', {}),
                            "available": True
                        }
                        gold_available = True
                    
                    sample = Sample(
                        sample_id=sample_id,
                        task_id=TASK_ID,
                        context={
                            "question": question,
                            "current_state": current_state,
                            "record_idx": sample_count
                        },
                        gold=gold if gold_available else {"available": False}
                    )
                    
                    # 解析response为JSON
                    response_text = record.get('response', '')
                    try:
                        parsed_data = json.loads(response_text)
                    except json.JSONDecodeError:
                        # 尝试从markdown提取
                        import re
                        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
                        if json_match:
                            try:
                                parsed_data = json.loads(json_match.group(1))
                            except:
                                parsed_data = {}
                        else:
                            parsed_data = {}
                    
                    model_output = ModelOutput(
                        model_name=record.get('model', model_name),
                        sample_id=sample_id,
                        raw_response_text=response_text,
                        timestamp=record.get('timestamp', ''),
                        task_id=TASK_ID
                    )
                    
                    samples.append(sample)
                    model_outputs.append(model_output)
                    sample_count += 1
                    
                except Exception as e:
                    print(f"   ⚠️  跳过样本: {e}")
                    continue
        
        print(f"   - 加载了 {len(samples)} 个样本")
        
        if len(samples) == 0:
            print(f"   ❌ 没有有效样本，跳过此模型")
            continue
        
        # 评估每个样本
        model_records = []
        model_scores = []
        dimension_scores_list = defaultdict(list)
        
        for sample, model_output in tqdm(zip(samples, model_outputs), 
                                         total=len(samples),
                                         desc=f"  {model_name}",
                                         leave=False,
                                         unit="样本"):
            try:
                record = evaluator.evaluate_sample(
                    sample=sample,
                    model_output=model_output,
                    model_confidence=None
                )
                model_records.append(record)
                
                # 收集分数
                if record.optional_scores:
                    dim_scores = record.optional_scores.get('dimension_scores', {})
                    total_score = record.optional_scores.get('total_score', 0)
                    
                    model_scores.append(total_score)
                    
                    # 收集各维度分数
                    for dim, score in dim_scores.items():
                        dimension_scores_list[dim].append(score * 100)  # 转为百分比
                
            except Exception as e:
                print(f"\n   ⚠️  评估样本 {sample.sample_id} 失败: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        all_records.extend(model_records)
        
        # 计算模型摘要
        if model_scores:
            avg_score = statistics.mean(model_scores)
            
            # 计算各维度平均分
            dim_avg = {}
            for dim, scores in dimension_scores_list.items():
                dim_avg[dim] = statistics.mean(scores)
            
            model_summaries[model_name] = {
                'avg_total_score': avg_score,
                'num_samples': len(model_scores),
                'num_errors': len(samples) - len(model_scores),
                'dimension_scores': dim_avg
            }
            
            print(f"   ✅ 平均总分: {avg_score:.2f} ({len(model_scores)}/{len(samples)} 样本成功)")
            print(f"      Protocol: {dim_avg.get('protocol_schema_compliance', 0):.1f}%, " +
                  f"Field: {dim_avg.get('field_validity_local_dynamics', 0):.1f}%, " +
                  f"Physics: {dim_avg.get('physics_cross_field_consistency', 0):.1f}%, " +
                  f"Safety: {dim_avg.get('safety_constraint_satisfaction', 0):.1f}%, " +
                  f"Pred: {dim_avg.get('predictive_quality_reliability', 0):.1f}%")
        else:
            print(f"   ❌ 没有成功评估的样本")
            model_summaries[model_name] = {
                'avg_total_score': 0,
                'num_samples': 0,
                'num_errors': len(samples),
                'dimension_scores': {}
            }
    
    # 保存结果
    print("\n" + "="*80)
    print("💾 保存评估结果")
    print("="*80)
    
    # 保存所有记录
    records_file = OUTPUT_DIR / f"records_{TASK_ID}_all_46_models.jsonl"
    with open(records_file, 'w') as f:
        for record in all_records:
            # 转换为dict
            rec_dict = {
                'sample_id': record.sample_id,
                'task_id': record.task_id,
                'model_name': record.model_name,
                'protocol_result': record.protocol_result.__dict__ if hasattr(record.protocol_result, '__dict__') else record.protocol_result,
                'evidence_pack': {
                    'atoms': [str(atom) for atom in record.evidence_pack.atoms],
                    'metadata': record.evidence_pack.metadata
                },
                'optional_scores': record.optional_scores,
                'agent_output': record.agent_output,
                'trace': record.trace
            }
            f.write(json.dumps(rec_dict, default=str) + '\n')
    
    print(f"✅ 保存记录: {records_file} ({len(all_records)} 条)")
    
    # 保存模型摘要
    summary_file = OUTPUT_DIR / "model_summaries.json"
    with open(summary_file, 'w') as f:
        json.dump(model_summaries, f, indent=2, ensure_ascii=False)
    print(f"✅ 保存摘要: {summary_file}")
    
    # 打印排行榜
    print("\n" + "="*80)
    print("🏆 Top 20 模型（按总分排序）")
    print("="*80)
    
    sorted_models = sorted(model_summaries.items(), 
                          key=lambda x: x[1]['avg_total_score'], 
                          reverse=True)
    
    print(f"\n{'排名':<4} {'模型':50s} {'总分':>8} {'Proto':>7} {'Field':>7} {'Phys':>7} {'Safety':>7} {'Pred':>7}")
    print("-" * 120)
    
    for i, (model, summary) in enumerate(sorted_models[:20], 1):
        dim_scores = summary.get('dimension_scores', {})
        print(f"{i:<4} {model:50s} {summary['avg_total_score']:7.2f}  " +
              f"{dim_scores.get('protocol_schema_compliance', 0):6.1f}% " +
              f"{dim_scores.get('field_validity_local_dynamics', 0):6.1f}% " +
              f"{dim_scores.get('physics_cross_field_consistency', 0):6.1f}% " +
              f"{dim_scores.get('safety_constraint_satisfaction', 0):6.1f}% " +
              f"{dim_scores.get('predictive_quality_reliability', 0):6.1f}%")
    
    print("\n" + "="*80)
    print(f"✅ 评估完成！")
    print(f"   总记录数: {len(all_records)}")
    print(f"   成功评估的模型数: {sum(1 for s in model_summaries.values() if s['num_samples'] > 0)}/{len(model_summaries)}")
    print("="*80)
    
    return all_records, model_summaries

if __name__ == "__main__":
    run_evaluation()
