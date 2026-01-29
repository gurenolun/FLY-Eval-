"""
Test Evaluation on Ground Truth

在Ground Truth数据上运行评估，验证评估标准的合理性。
如果Ground Truth表现很好，说明标准合理；如果Ground Truth也表现不好，说明标准可能过严。
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fly_eval_plus_plus.main import FLYEvalPlusPlus
from fly_eval_plus_plus.core.data_structures import EvalConfig, Sample, ModelOutput
from fly_eval_plus_plus.data_loader import DataLoader

# API Key from environment variable
API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY_FROM_RUN_MULTI_TASK")


def load_ground_truth_samples(task_id: str = "S1", num_samples: int = 10):
    """
    Load ground truth samples
    
    Args:
        task_id: Task ID (S1, M1, M3)
        num_samples: Number of samples to load
    
    Returns:
        List of (Sample, ModelOutput) tuples where ModelOutput contains ground truth
    """
    loader = DataLoader()
    
    # Load reference data
    reference_data = loader.load_reference_data(task_id)
    if not reference_data:
        print("❌ 无法加载参考数据")
        return []
    
    print(f"✅ 加载了 {len(reference_data)} 条参考数据")
    
    # Limit samples
    reference_data = reference_data[:num_samples]
    
    # Create Sample and ModelOutput objects
    samples = []
    model_outputs = []
    
    for i, ref_record in enumerate(reference_data):
        sample_id = ref_record.get('id', f"S1_ground_truth_{i:03d}")
        
        # Create Sample
        sample = Sample(
            sample_id=sample_id,
            task_id=task_id,
            context={
                "question": ref_record.get('question', ''),
                "current_state": ref_record.get('current_state', {}),
                "record_idx": i
            },
            gold={
                "next_second": ref_record.get('next_second', {}),
                "available": True
            }
        )
        
        # Create ModelOutput with ground truth as "response"
        # Convert ground truth dict to JSON string
        gt_json = json.dumps(ref_record.get('next_second', {}), ensure_ascii=False)
        
        model_output = ModelOutput(
            model_name="ground_truth",
            sample_id=sample_id,
            raw_response_text=gt_json,
            timestamp=datetime.now().isoformat(),
            task_id=task_id
        )
        
        samples.append(sample)
        model_outputs.append(model_output)
    
    return samples, model_outputs


def evaluate_ground_truth(task_id: str = "S1", num_samples: int = 10):
    """
    Evaluate ground truth data
    
    Args:
        task_id: Task ID
        num_samples: Number of samples to evaluate
    """
    print("=" * 80)
    print("Ground Truth评估测试")
    print("=" * 80)
    print(f"任务: {task_id}")
    print(f"样本数: {num_samples}")
    print("=" * 80)
    
    # Load ground truth samples
    print("\n加载Ground Truth数据...")
    samples, model_outputs = load_ground_truth_samples(task_id, num_samples)
    
    if not samples:
        print("❌ 无法加载Ground Truth数据")
        return
    
    print(f"✅ 加载了 {len(samples)} 个Ground Truth样本")
    
    # Create config (use LLM Judge)
    config = EvalConfig(version="1.0.0")
    
    api_key = API_KEY or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY environment variable.")
    
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
    
    # Initialize evaluator
    print("\n初始化评估器...")
    evaluator = FLYEvalPlusPlus(config_path=None)
    evaluator.config = config
    evaluator.fusion = evaluator._create_fusion(config.fusion_protocol)
    
    # Evaluate samples
    print(f"\n评估 {len(samples)} 个Ground Truth样本...")
    print("=" * 80)
    
    records = []
    for i, (sample, model_output) in enumerate(zip(samples, model_outputs), 1):
        print(f"\n[{i}/{len(samples)}] 评估样本: {sample.sample_id}")
        try:
            record = evaluator.evaluate_sample(sample, model_output)
            records.append(record)
            
            # Show results
            scores = record.optional_scores
            if scores and "llm_judge_output" in scores:
                llm_output = scores["llm_judge_output"]
                overall_grade = llm_output.get("overall_grade", "N/A")
                total_score = scores.get("total_score", 0)
                print(f"  等级: {overall_grade}, 总分: {total_score:.2f}")
                
                # Show dimension grades
                grade_vector = llm_output.get("grade_vector", {})
                print(f"  维度等级:")
                for dim, grade in grade_vector.items():
                    print(f"    - {dim}: {grade}")
                
                # Show eligibility
                adjudication = record.agent_output.get("adjudication", "unknown")
                print(f"  Eligibility: {adjudication}")
        except Exception as e:
            print(f"  ⚠️  评估失败: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Generate summary
    print("\n" + "=" * 80)
    print("Ground Truth评估结果汇总")
    print("=" * 80)
    
    if records:
        # LLM Judge统计
        llm_outputs = []
        total_scores = []
        eligible_count = 0
        
        for r in records:
            scores = r.optional_scores
            if "llm_judge_output" in scores:
                llm_outputs.append(scores["llm_judge_output"])
            if "total_score" in scores:
                total_scores.append(scores["total_score"])
            if r.agent_output.get("adjudication") == "eligible":
                eligible_count += 1
        
        print(f"\n总样本数: {len(records)}")
        print(f"有LLM Judge输出: {len(llm_outputs)}")
        
        if llm_outputs:
            from collections import Counter
            
            # 等级分布
            grade_dist = Counter(llm["overall_grade"] for llm in llm_outputs)
            print(f"\n总体等级分布: {dict(grade_dist)}")
            
            # 维度等级分布
            dim_grades = {}
            for llm in llm_outputs:
                for dim, grade in llm.get("grade_vector", {}).items():
                    if dim not in dim_grades:
                        dim_grades[dim] = []
                    dim_grades[dim].append(grade)
            
            print(f"\n各维度等级分布:")
            for dim, grades in sorted(dim_grades.items()):
                dist = Counter(grades)
                print(f"  {dim}: {dict(dist)}")
            
            # 分数统计
            if total_scores:
                print(f"\n分数统计:")
                print(f"  平均分: {sum(total_scores)/len(total_scores):.2f}")
                print(f"  最高分: {max(total_scores):.2f}")
                print(f"  最低分: {min(total_scores):.2f}")
            
            # Eligibility
            print(f"\nEligibility:")
            print(f"  Eligible样本: {eligible_count}/{len(records)} ({eligible_count/len(records)*100:.1f}%)")
        
        # Save results
        output_dir = "results/ground_truth_evaluation"
        os.makedirs(output_dir, exist_ok=True)
        
        records_file = os.path.join(output_dir, "records_ground_truth.json")
        with open(records_file, 'w', encoding='utf-8') as f:
            json.dump([r.__dict__ for r in records], f, indent=2, default=str, ensure_ascii=False)
        print(f"\n✅ 结果已保存: {records_file}")
        
        # Analysis
        print("\n" + "=" * 80)
        print("标准合理性分析")
        print("=" * 80)
        
        if llm_outputs:
            # Check if ground truth gets high grades
            a_count = sum(1 for llm in llm_outputs if llm.get("overall_grade") == "A")
            b_count = sum(1 for llm in llm_outputs if llm.get("overall_grade") == "B")
            high_grade_rate = (a_count + b_count) / len(llm_outputs) * 100
            
            print(f"\nGround Truth表现:")
            print(f"  A等级: {a_count}/{len(llm_outputs)} ({a_count/len(llm_outputs)*100:.1f}%)")
            print(f"  B等级: {b_count}/{len(llm_outputs)} ({b_count/len(llm_outputs)*100:.1f}%)")
            print(f"  A/B等级合计: {a_count+b_count}/{len(llm_outputs)} ({high_grade_rate:.1f}%)")
            print(f"  Eligibility率: {eligible_count}/{len(records)} ({eligible_count/len(records)*100:.1f}%)")
            
            print(f"\n标准合理性判断:")
            if high_grade_rate >= 80:
                print(f"  ✅ 标准合理: Ground Truth有{high_grade_rate:.1f}%达到A/B等级")
                print(f"     说明评估标准是合理的，能够正确识别高质量输出")
            elif high_grade_rate >= 50:
                print(f"  ⚠️  标准可能偏严: Ground Truth只有{high_grade_rate:.1f}%达到A/B等级")
                print(f"     建议检查评估标准是否过严")
            else:
                print(f"  ❌ 标准可能过严: Ground Truth只有{high_grade_rate:.1f}%达到A/B等级")
                print(f"     建议放宽评估标准或检查是否有bug")
            
            if eligible_count / len(records) >= 0.8:
                print(f"  ✅ Eligibility标准合理: Ground Truth有{eligible_count/len(records)*100:.1f}%通过gating")
            elif eligible_count / len(records) >= 0.5:
                print(f"  ⚠️  Eligibility标准可能偏严: Ground Truth只有{eligible_count/len(records)*100:.1f}%通过gating")
            else:
                print(f"  ❌ Eligibility标准可能过严: Ground Truth只有{eligible_count/len(records)*100:.1f}%通过gating")
                print(f"     建议检查gating规则是否过严")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="在Ground Truth上测试评估标准")
    parser.add_argument("--task", type=str, default="S1", help="任务ID")
    parser.add_argument("--num_samples", type=int, default=10, help="样本数（默认：10）")
    
    args = parser.parse_args()
    
    evaluate_ground_truth(
        task_id=args.task,
        num_samples=args.num_samples
    )

