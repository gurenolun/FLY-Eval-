"""
Run Full Evaluation with LLM Judge

运行全模型评估，使用LLM Judge进行评分。
限制每个模型的样本数以快速验证。
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fly_eval_plus_plus.main import FLYEvalPlusPlus
from fly_eval_plus_plus.data_loader import DataLoader
from fly_eval_plus_plus.core.data_structures import EvalConfig

# API Key from environment variable or config
# For security: Never hardcode API keys. Use environment variable OPENAI_API_KEY
# or pass via config. For evaluation, set: export OPENAI_API_KEY="your-key"
API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY_FROM_RUN_MULTI_TASK")


def run_full_evaluation_llm_judge(task_id: str = "S1", 
                                   model_names: list = None,
                                   samples_per_model: int = 10,
                                   output_dir: str = "results/final_official_v1.0.0_llm_judge"):
    """
    运行全模型评估（使用LLM Judge）
    
    Args:
        task_id: 任务ID (S1, M1, M3)
        model_names: 模型列表（默认：所有可用模型）
        samples_per_model: 每个模型评估的样本数（限制以快速验证）
        output_dir: 输出目录
    """
    print("=" * 80)
    print("FLY-EVAL++ 全模型评估（LLM Judge）")
    print("=" * 80)
    print(f"任务: {task_id}")
    print(f"每个模型样本数: {samples_per_model}")
    print(f"输出目录: {output_dir}")
    print("=" * 80)
    
    # 创建配置（使用LLM Judge）
    config = EvalConfig(version="1.0.0")
    
    # Get API key from environment or use provided one
    api_key = API_KEY or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY environment variable.")
    
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
            "api_key": api_key,  # From environment variable
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
    if model_names is None:
        model_names = loader.get_all_models_for_task(task_id)
    
    print(f"\n找到 {len(model_names)} 个模型")
    print(f"前5个模型: {model_names[:5]}")
    
    # 评估所有模型
    all_records = []
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 增量保存文件路径
    records_file = os.path.join(output_dir, f"records_{task_id}.json")
    incremental_file = os.path.join(output_dir, f"records_{task_id}_incremental.jsonl")
    
    # 如果已有增量文件，加载已有记录
    existing_records = []
    if os.path.exists(incremental_file):
        print(f"\n发现已有增量文件，加载已有记录...")
        with open(incremental_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    existing_records.append(json.loads(line))
        print(f"  已加载 {len(existing_records)} 条记录")
    
    # 计算总进度
    total_samples = len(model_names) * samples_per_model
    completed_samples = len(existing_records)
    
    print(f"\n开始评估...")
    print(f"总进度: {completed_samples}/{total_samples} ({completed_samples/total_samples*100:.1f}%)")
    print("=" * 80)
    
    # 创建总体进度条
    pbar_total = tqdm(total=total_samples, initial=completed_samples, desc="总体进度", unit="样本")
    
    for i, model_name in enumerate(model_names, 1):
        print(f"\n[{i}/{len(model_names)}] 评估模型: {model_name}")
        
        try:
            # 加载样本和模型输出
            samples, model_outputs = loader.create_samples_and_outputs(task_id, model_name)
            
            if not samples or not model_outputs:
                print(f"  ⚠️  警告: 未找到数据，跳过")
                continue
            
            print(f"  找到 {len(samples)} 个样本")
            
            # 限制样本数
            samples = samples[:samples_per_model]
            model_outputs = model_outputs[:samples_per_model]
            
            print(f"  评估 {len(samples)} 个样本...")
            
            # 评估样本（带进度条）
            model_records = []
            pbar_model = tqdm(total=len(samples), desc=f"  {model_name[:20]:<20}", unit="样本", leave=False)
            
            for j, (sample, model_output) in enumerate(zip(samples, model_outputs), 1):
                try:
                    record = evaluator.evaluate_sample(sample, model_output)
                    model_records.append(record)
                    
                    # 立即保存到增量文件（JSONL格式，每行一条记录）
                    record_dict = record.__dict__
                    with open(incremental_file, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(record_dict, default=str, ensure_ascii=False) + '\n')
                    
                    # 更新进度条
                    pbar_model.update(1)
                    pbar_total.update(1)
                    
                    # 显示详细信息（每5个样本或最后一个）
                    if j % 5 == 0 or j == len(samples):
                        scores = record.optional_scores
                        if scores and "llm_judge_output" in scores:
                            llm_output = scores["llm_judge_output"]
                            overall_grade = llm_output.get("overall_grade", "N/A")
                            total_score = scores.get("total_score", 0)
                            pbar_model.set_postfix({"等级": overall_grade, "总分": f"{total_score:.1f}"})
                
                except Exception as e:
                    print(f"    ⚠️  样本 {j} 评估失败: {e}")
                    pbar_model.update(1)
                    pbar_total.update(1)
                    continue
            
            pbar_model.close()
            all_records.extend(model_records)
            print(f"  ✅ 完成: {len(model_records)} 个记录")
            
        except Exception as e:
            print(f"  ❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    pbar_total.close()
    
    print(f"\n" + "=" * 80)
    print(f"评估完成!")
    print(f"  总记录数: {len(all_records)}")
    print(f"  模型数: {len(model_names)}")
    
    # 生成汇总
    print(f"\n生成汇总...")
    task_summaries = evaluator.generate_task_summary(all_records, task_id)
    
    # 加载模型置信度（可选）
    model_confidence_dict = loader.load_model_confidence()
    
    # 生成模型画像（按模型分组）
    model_profiles = {}
    for model_name in model_names:
        model_records = [r for r in all_records if r.model_name == model_name]
        if model_records:
            model_confidence = model_confidence_dict.get(model_name)
            profile = evaluator.generate_model_profile(model_records, model_confidence)
            model_profiles[model_name] = profile
    
    # 保存完整records（JSON格式，便于读取）
    # 如果已有增量文件，从增量文件重新加载所有记录
    if os.path.exists(incremental_file):
        all_records_from_file = []
        with open(incremental_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    all_records_from_file.append(json.loads(line))
        all_records = all_records_from_file
    
    # 保存完整records（JSON格式）
    records_file = os.path.join(output_dir, f"records_{task_id}.json")
    with open(records_file, 'w', encoding='utf-8') as f:
        json.dump(all_records, f, indent=2, default=str, ensure_ascii=False)
    print(f"  ✅ 记录已保存: {records_file} ({len(all_records)} 条记录)")
    print(f"  ✅ 增量文件: {incremental_file}")
    
    # 保存summaries
    summaries_file = os.path.join(output_dir, "task_summaries.json")
    with open(summaries_file, 'w', encoding='utf-8') as f:
        # task_summaries is a single TaskSummary object, not a dict
        summaries_dict = {task_id: task_summaries.__dict__}
        json.dump(summaries_dict, f, indent=2, default=str)
    print(f"  ✅ 任务汇总已保存: {summaries_file}")
    
    # 保存model profiles
    profiles_file = os.path.join(output_dir, "model_profiles.json")
    with open(profiles_file, 'w', encoding='utf-8') as f:
        profiles_dict = {k: v.__dict__ for k, v in model_profiles.items()}
        json.dump(profiles_dict, f, indent=2, default=str)
    print(f"  ✅ 模型画像已保存: {profiles_file}")
    
    # 保存版本信息
    version_info = {
        "evaluation_timestamp": datetime.now().isoformat(),
        "version_info": {
            "config_hash": all_records[0].trace.get('config_hash') if all_records else 'N/A',
            "schema_version": all_records[0].trace.get('schema_version') if all_records else 'N/A',
            "constraint_lib_version": all_records[0].trace.get('constraint_lib_version') if all_records else 'N/A',
            "evaluator_version": all_records[0].trace.get('evaluator_version') if all_records else '1.0.0',
            "fusion_type": "llm_based",
            "llm_judge_model": "gpt-4o"
        },
        "model_count": len(model_names),
        "total_records": len(all_records),
        "samples_per_model": samples_per_model
    }
    
    version_file = os.path.join(output_dir, "version_info.json")
    with open(version_file, 'w', encoding='utf-8') as f:
        json.dump(version_info, f, indent=2)
    print(f"  ✅ 版本信息已保存: {version_file}")
    
    print(f"\n✅ 所有结果已保存到: {output_dir}")
    
    return {
        "output_dir": output_dir,
        "records": all_records,
        "task_summaries": task_summaries,
        "model_profiles": model_profiles,
        "version_info": version_info
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="运行全模型评估（LLM Judge）")
    parser.add_argument("--task", type=str, default="S1", help="任务ID (S1, M1, M3)")
    parser.add_argument("--models", type=str, nargs='+', default=None, help="模型列表（默认：所有可用模型）")
    parser.add_argument("--samples_per_model", type=int, default=10, help="每个模型评估的样本数（默认：10）")
    parser.add_argument("--output_dir", type=str, default="results/final_official_v1.0.0_llm_judge", help="输出目录")
    
    args = parser.parse_args()
    
    run_full_evaluation_llm_judge(
        task_id=args.task,
        model_names=args.models,
        samples_per_model=args.samples_per_model,
        output_dir=args.output_dir
    )

