"""
Test LLM Judge with Real Data

使用真实数据测试LLM Judge，限制数量以确保能快速验证。
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fly_eval_plus_plus.main import FLYEvalPlusPlus
from fly_eval_plus_plus.data_loader import DataLoader
from fly_eval_plus_plus.core.data_structures import EvalConfig
import json

# API Key from run_multi_task_tests.py
# API Key from environment variable
# For security: Never hardcode API keys. Use environment variable OPENAI_API_KEY
# Set: export OPENAI_API_KEY="your-key"
API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY_FROM_RUN_MULTI_TASK")


def test_llm_judge_with_real_data(task_id: str = "S1", model_name: str = None, num_samples: int = 3):
    """
    使用真实数据测试LLM Judge
    
    Args:
        task_id: 任务ID (S1, M1, M3)
        model_name: 模型名称（默认：第一个可用模型）
        num_samples: 测试样本数（限制为3个以快速验证）
    """
    print("=" * 80)
    print("LLM Judge 真实数据测试")
    print("=" * 80)
    print(f"任务: {task_id}")
    print(f"测试样本数: {num_samples}")
    print(f"API Key: {API_KEY[:20]}...")
    print("=" * 80)
    
    # 检查API key
    if not API_KEY:
        print("❌ 错误: API Key未设置")
        return False
    
    # 创建配置（使用LLM Judge）
    config = EvalConfig(version="1.0.0")
    config.fusion_protocol = {
        "type": "llm_based",  # 使用LLM Judge
        "gating_rules": {
            "protocol_failure": {"max_allowed": 0, "severity": "critical"},
            "safety_constraint_violation": {"max_allowed": 0, "severity": "critical"},
            "key_field_missing": {"max_allowed": 0, "severity": "critical"}
        },
        "llm_judge": {
            "model": "gpt-4o",
            "temperature": 0,
            "api_key": API_KEY,
            "max_retries": 3
        }
    }
    
    # 初始化评估器
    print("\n初始化评估器...")
    evaluator = FLYEvalPlusPlus(config_path=None)
    evaluator.config = config
    evaluator.fusion = evaluator._create_fusion(config.fusion_protocol)
    
    # 加载数据
    print("加载数据...")
    loader = DataLoader()
    
    # 获取模型列表
    models = loader.get_all_models_for_task(task_id)
    if not models:
        print(f"❌ 错误: 任务 {task_id} 没有可用模型")
        return False
    
    # 选择模型
    if model_name is None:
        model_name = models[0]
    
    if model_name not in models:
        print(f"⚠️  警告: 模型 {model_name} 不在可用列表中，使用第一个模型: {models[0]}")
        model_name = models[0]
    
    print(f"使用模型: {model_name}")
    
    # 加载样本和模型输出
    samples, model_outputs = loader.create_samples_and_outputs(task_id, model_name)
    
    if not samples or not model_outputs:
        print(f"❌ 错误: 无法加载数据")
        return False
    
    print(f"加载了 {len(samples)} 个样本")
    
    # 限制样本数
    samples = samples[:num_samples]
    model_outputs = model_outputs[:num_samples]
    
    print(f"测试 {len(samples)} 个样本...")
    print("=" * 80)
    
    # 评估样本
    results = []
    for i, (sample, model_output) in enumerate(zip(samples, model_outputs), 1):
        print(f"\n[{i}/{len(samples)}] 评估样本: {sample.sample_id}")
        
        try:
            # 评估
            record = evaluator.evaluate_sample(sample, model_output)
            
            # 检查LLM Judge输出
            scores = record.optional_scores
            if scores and "llm_judge_output" in scores:
                llm_output = scores["llm_judge_output"]
                
                print(f"  ✅ LLM Judge输出:")
                print(f"     总体等级: {llm_output.get('overall_grade', 'N/A')}")
                print(f"     总分: {scores.get('total_score', 0):.2f}")
                print(f"     维度等级:")
                for dim, grade in llm_output.get('grade_vector', {}).items():
                    dim_score = llm_output.get('dimension_scores', {}).get(dim, 0)
                    print(f"       - {dim}: {grade} (score: {dim_score:.2f})")
                
                print(f"     关键发现: {len(llm_output.get('critical_findings', []))} 个")
                print(f"     检查清单: {len(llm_output.get('checklist', []))} 项")
                
                results.append({
                    "sample_id": sample.sample_id,
                    "success": True,
                    "llm_output": llm_output,
                    "total_score": scores.get('total_score', 0)
                })
            else:
                print(f"  ⚠️  警告: 未找到LLM Judge输出")
                if scores:
                    print(f"     可用keys: {list(scores.keys())}")
                results.append({
                    "sample_id": sample.sample_id,
                    "success": False,
                    "error": "No LLM Judge output"
                })
        
        except Exception as e:
            print(f"  ❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "sample_id": sample.sample_id,
                "success": False,
                "error": str(e)
            })
    
    # 统计结果
    print("\n" + "=" * 80)
    print("测试结果统计")
    print("=" * 80)
    
    success_count = sum(1 for r in results if r.get("success", False))
    print(f"成功: {success_count}/{len(results)}")
    print(f"失败: {len(results) - success_count}/{len(results)}")
    
    if success_count > 0:
        avg_score = sum(r.get("total_score", 0) for r in results if r.get("success")) / success_count
        print(f"平均总分: {avg_score:.2f}")
        
        # 统计等级分布
        grade_dist = {}
        for r in results:
            if r.get("success") and "llm_output" in r:
                overall_grade = r["llm_output"].get("overall_grade", "N/A")
                grade_dist[overall_grade] = grade_dist.get(overall_grade, 0) + 1
        
        print(f"\n等级分布:")
        for grade, count in sorted(grade_dist.items()):
            print(f"  {grade}: {count}")
    
    # 保存结果
    output_file = Path("results/llm_judge_test_results.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "task_id": task_id,
            "model_name": model_name,
            "num_samples": num_samples,
            "results": results,
            "summary": {
                "success_count": success_count,
                "total_count": len(results),
                "avg_score": avg_score if success_count > 0 else 0
            }
        }, f, indent=2, default=str)
    
    print(f"\n✅ 结果已保存到: {output_file}")
    
    return success_count > 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="测试LLM Judge（使用真实数据）")
    parser.add_argument("--task", type=str, default="S1", help="任务ID (S1, M1, M3)")
    parser.add_argument("--model", type=str, default=None, help="模型名称（默认：第一个可用）")
    parser.add_argument("--num_samples", type=int, default=3, help="测试样本数（默认：3）")
    
    args = parser.parse_args()
    
    success = test_llm_judge_with_real_data(
        task_id=args.task,
        model_name=args.model,
        num_samples=args.num_samples
    )
    
    if success:
        print("\n✅ LLM Judge测试成功！")
        sys.exit(0)
    else:
        print("\n❌ LLM Judge测试失败")
        sys.exit(1)

