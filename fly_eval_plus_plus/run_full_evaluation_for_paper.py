"""
Run Full Evaluation for Paper

Runs evaluation for all models and generates paper-ready results.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fly_eval_plus_plus.main import FLYEvalPlusPlus
from fly_eval_plus_plus.data_loader import DataLoader
from fly_eval_plus_plus.core.data_structures import EvalConfig
import json
from datetime import datetime


def load_config() -> EvalConfig:
    """Load evaluation configuration"""
    # Load default config (same as run_evaluation.py)
    config = EvalConfig(version="1.0.0")
    
    # Load task specs, schema, constraint lib from default locations
    # (This should match the config used in run_evaluation.py)
    
    return config


def run_full_evaluation():
    """Run full evaluation for all models"""
    print("=" * 80)
    print("FLY-EVAL++ Full Evaluation for Paper")
    print("=" * 80)
    
    # Initialize
    loader = DataLoader()
    config = load_config()
    evaluator = FLYEvalPlusPlus(config)
    
    # Get all models for S1
    task_id = "S1"
    models = loader.get_all_models_for_task(task_id)
    
    print(f"\n找到 {len(models)} 个模型用于评估")
    print(f"任务: {task_id}")
    print(f"\n模型列表:")
    for i, model_name in enumerate(models[:20], 1):
        print(f"  {i}. {model_name}")
    if len(models) > 20:
        print(f"  ... 还有 {len(models) - 20} 个模型")
    
    # Load samples and reference data
    print(f"\n加载数据...")
    samples = loader.load_samples(task_id)
    reference_data = loader.load_reference_data(task_id)
    
    print(f"  样本数: {len(samples)}")
    print(f"  参考数据数: {len(reference_data)}")
    
    # Create reference data lookup
    ref_lookup = {}
    for ref in reference_data:
        sample_id = ref.get('sample_id') or ref.get('id')
        if sample_id:
            ref_lookup[sample_id] = ref
    
    # Update samples with gold data
    for sample in samples:
        sample_id = sample.sample_id
        if sample_id in ref_lookup:
            ref = ref_lookup[sample_id]
            sample.gold = {
                'available': True,
                'next_second': ref.get('next_second') or ref.get('T+1', {})
            }
        else:
            sample.gold = {'available': False}
    
    # Evaluate all models
    all_records = []
    
    print(f"\n开始评估...")
    print("=" * 80)
    
    for i, model_name in enumerate(models, 1):
        print(f"\n[{i}/{len(models)}] 评估模型: {model_name}")
        
        try:
            # Load model outputs
            model_outputs = loader.load_model_outputs(task_id, model_name)
            
            if not model_outputs:
                print(f"  ⚠️  警告: 未找到模型输出，跳过")
                continue
            
            print(f"  找到 {len(model_outputs)} 个输出")
            
            # Align samples and outputs
            aligned_samples = []
            aligned_outputs = []
            
            for sample in samples:
                # Find matching output
                matching_output = None
                for output in model_outputs:
                    if output.sample_id == sample.sample_id:
                        matching_output = output
                        break
                
                if matching_output:
                    aligned_samples.append(sample)
                    aligned_outputs.append(matching_output)
            
            print(f"  对齐后: {len(aligned_samples)} 个样本")
            
            if not aligned_samples:
                print(f"  ⚠️  警告: 无对齐样本，跳过")
                continue
            
            # Evaluate
            records = evaluator.evaluate_all_samples(
                aligned_samples,
                aligned_outputs
            )
            
            all_records.extend(records)
            print(f"  ✅ 完成: {len(records)} 个记录")
            
        except Exception as e:
            print(f"  ❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\n" + "=" * 80)
    print(f"评估完成!")
    print(f"  总记录数: {len(all_records)}")
    print(f"  模型数: {len(models)}")
    
    # Generate summaries
    print(f"\n生成汇总...")
    task_summaries = evaluator.generate_task_summary(all_records)
    model_profiles = evaluator.generate_model_profile(all_records)
    
    # Save results
    output_dir = Path("results/final_official_v1.0.0_full")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save records
    records_file = output_dir / "records_S1.json"
    with open(records_file, 'w', encoding='utf-8') as f:
        json.dump([r.__dict__ for r in all_records], f, indent=2, default=str)
    print(f"  ✅ 记录已保存: {records_file}")
    
    # Save summaries
    summaries_file = output_dir / "task_summaries.json"
    with open(summaries_file, 'w', encoding='utf-8') as f:
        json.dump({k: v.__dict__ for k, v in task_summaries.items()}, f, indent=2, default=str)
    print(f"  ✅ 任务汇总已保存: {summaries_file}")
    
    # Save model profiles
    profiles_file = output_dir / "model_profiles.json"
    with open(profiles_file, 'w', encoding='utf-8') as f:
        json.dump({k: v.__dict__ for k, v in model_profiles.items()}, f, indent=2, default=str)
    print(f"  ✅ 模型画像已保存: {profiles_file}")
    
    # Save version info
    version_info = {
        "evaluation_timestamp": datetime.now().isoformat(),
        "version_info": {
            "config_hash": all_records[0].trace.get('config_hash') if all_records else 'N/A',
            "schema_version": all_records[0].trace.get('schema_version') if all_records else 'N/A',
            "constraint_lib_version": all_records[0].trace.get('constraint_lib_version') if all_records else 'N/A',
            "evaluator_version": all_records[0].trace.get('evaluator_version') if all_records else '1.0.0'
        },
        "model_count": len(models),
        "total_records": len(all_records)
    }
    
    version_file = output_dir / "version_info.json"
    with open(version_file, 'w', encoding='utf-8') as f:
        json.dump(version_info, f, indent=2)
    print(f"  ✅ 版本信息已保存: {version_file}")
    
    print(f"\n✅ 所有结果已保存到: {output_dir}")
    
    return {
        "output_dir": str(output_dir),
        "records": all_records,
        "task_summaries": task_summaries,
        "model_profiles": model_profiles,
        "version_info": version_info
    }


if __name__ == "__main__":
    run_full_evaluation()

