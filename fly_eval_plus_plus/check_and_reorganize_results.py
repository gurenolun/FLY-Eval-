#!/usr/bin/env python3
"""
检查并重新组织评估结果
按照"输出文件夹-任务类型S1M1M3-模型目录-模型结果"的格式整合结果
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from fly_eval_plus_plus.core.data_structures import TaskSummary, ModelProfile


def check_results_quality(records_file: str, task_summary_file: str, model_profiles_file: str):
    """检查结果质量"""
    print("=" * 80)
    print("检查结果质量")
    print("=" * 80)
    
    # 1. 检查记录文件
    print("\n1. 检查记录文件...")
    with open(records_file, 'r', encoding='utf-8') as f:
        records = [json.loads(line) for line in f]
    
    print(f"   ✅ 总记录数: {len(records)}")
    
    # 统计模型和样本
    models = set(r['model_name'] for r in records)
    print(f"   ✅ 模型数量: {len(models)}")
    print(f"   ✅ 模型列表: {sorted(models)[:5]}...")
    
    # 统计eligible样本
    eligible_count = sum(1 for r in records if r.get('agent_output', {}).get('adjudication') == 'eligible')
    print(f"   ✅ Eligible样本数: {eligible_count}")
    print(f"   ✅ Eligible率: {eligible_count / len(records) * 100:.2f}%")
    
    # 检查记录完整性
    required_keys = ['sample_id', 'model_name', 'task_id', 'protocol_result', 'evidence_pack', 'agent_output', 'optional_scores']
    incomplete_records = []
    for i, r in enumerate(records[:100]):  # 只检查前100条
        missing_keys = [k for k in required_keys if k not in r]
        if missing_keys:
            incomplete_records.append((i, missing_keys))
    
    if incomplete_records:
        print(f"   ⚠️  发现 {len(incomplete_records)} 条不完整记录（前100条中）")
        for idx, missing in incomplete_records[:5]:
            print(f"      记录 {idx}: 缺少 {missing}")
    else:
        print("   ✅ 记录完整性检查通过")
    
    # 2. 检查任务摘要
    print("\n2. 检查任务摘要...")
    if os.path.exists(task_summary_file):
        with open(task_summary_file, 'r', encoding='utf-8') as f:
            task_summary = json.load(f)
        
        print(f"   ✅ 总样本数: {task_summary.get('total_samples', 0)}")
        print(f"   ✅ Eligible样本数: {task_summary.get('eligible_samples', 0)}")
        print(f"   ✅ Eligible率: {task_summary.get('eligibility_rate', 0.0)}")
        
        # 检查eligibility_rate是否正确
        expected_rate = (task_summary.get('eligible_samples', 0) / task_summary.get('total_samples', 1)) * 100
        actual_rate = task_summary.get('eligibility_rate', 0.0)
        if abs(expected_rate - actual_rate) > 0.01:
            print(f"   ⚠️  Eligibility率计算错误！")
            print(f"      期望值: {expected_rate:.2f}%")
            print(f"      实际值: {actual_rate:.2f}%")
            return False
        else:
            print("   ✅ Eligibility率计算正确")
    else:
        print(f"   ❌ 任务摘要文件不存在: {task_summary_file}")
        return False
    
    # 3. 检查模型画像
    print("\n3. 检查模型画像...")
    if os.path.exists(model_profiles_file):
        try:
            with open(model_profiles_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    model_profiles = json.loads(content)
                else:
                    model_profiles = {}
        except (json.JSONDecodeError, ValueError) as e:
            print(f"   ⚠️  模型画像文件格式错误: {e}")
            model_profiles = {}
        
        if not model_profiles:
            print(f"   ⚠️  模型画像文件为空，将在重新组织时从记录生成")
        else:
            print(f"   ✅ 模型画像数量: {len(model_profiles)}")
            print(f"   ✅ 模型列表: {sorted(model_profiles.keys())[:5]}...")
    else:
        print(f"   ⚠️  模型画像文件不存在: {model_profiles_file}，将在重新组织时从记录生成")
    
    print("\n" + "=" * 80)
    print("✅ 结果质量检查完成")
    print("=" * 80)
    
    return True


def reorganize_results(
    base_output_dir: str,
    task_id: str,
    records_file: str,
    task_summary_file: str,
    model_profiles_file: str
):
    """
    重新组织结果文件
    
    按照"输出文件夹-任务类型-模型目录-模型结果"的格式组织
    """
    print("\n" + "=" * 80)
    print(f"重新组织结果 - {task_id}")
    print("=" * 80)
    
    # 创建新的目录结构
    # base_output_dir/task_id/model_name/
    new_base_dir = Path(base_output_dir) / task_id
    new_base_dir.mkdir(parents=True, exist_ok=True)
    
    # 加载所有记录
    print("\n📂 加载记录文件...")
    with open(records_file, 'r', encoding='utf-8') as f:
        records = [json.loads(line) for line in f]
    
    print(f"   ✅ 加载 {len(records)} 条记录")
    
    # 按模型分组
    records_by_model = defaultdict(list)
    for record in records:
        model_name = record['model_name']
        records_by_model[model_name].append(record)
    
    print(f"   ✅ 分组到 {len(records_by_model)} 个模型")
    
    # 加载任务摘要
    with open(task_summary_file, 'r', encoding='utf-8') as f:
        task_summary = json.load(f)
    
    # 尝试加载模型画像（可能为空）
    model_profiles = {}
    if os.path.exists(model_profiles_file):
        try:
            with open(model_profiles_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    model_profiles = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            print(f"   ⚠️  模型画像文件为空或格式错误，将从记录重新生成")
            model_profiles = {}
    
    # 如果模型画像为空，从记录重新生成
    if not model_profiles:
        print("\n📊 从记录重新生成模型画像...")
        from fly_eval_plus_plus.main import FLYEvalPlusPlus
        evaluator = FLYEvalPlusPlus()
        
        for model_name, model_records in records_by_model.items():
            # 将字典转换为Record对象（简化版，只保留必要字段）
            # 或者直接使用字典格式，修改generate_model_profile使其兼容
            try:
                # 尝试使用evaluator生成模型画像
                # 注意：这里需要修改generate_model_profile以支持字典格式
                # 暂时跳过，使用简化的统计信息
                eligible_count = sum(1 for r in model_records if r.get('agent_output', {}).get('adjudication') == 'eligible')
                total_scores = [r.get('optional_scores', {}).get('total_score', 0) for r in model_records if r.get('optional_scores', {}).get('total_score') is not None]
                avg_score = sum(total_scores) / len(total_scores) if total_scores else 0.0
                
                model_profiles[model_name] = {
                    "model_name": model_name,
                    "task_id": task_id,
                    "total_samples": len(model_records),
                    "eligible_samples": eligible_count,
                    "eligibility_rate": (eligible_count / len(model_records) * 100) if model_records else 0.0,
                    "average_overall_score": avg_score
                }
            except Exception as e:
                print(f"   ⚠️  生成模型画像失败 ({model_name}): {e}")
                model_profiles[model_name] = {
                    "model_name": model_name,
                    "task_id": task_id,
                    "total_samples": len(model_records),
                    "eligible_samples": 0,
                    "eligibility_rate": 0.0,
                    "average_overall_score": 0.0
                }
    
    # 为每个模型创建目录并保存结果
    print("\n💾 保存模型结果...")
    for model_name, model_records in records_by_model.items():
        # 创建模型目录（清理模型名称中的特殊字符）
        safe_model_name = model_name.replace('/', '_').replace('\\', '_')
        model_dir = new_base_dir / safe_model_name
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存该模型的记录（JSONL格式）
        records_file_model = model_dir / "records.jsonl"
        with open(records_file_model, 'w', encoding='utf-8') as f:
            for record in model_records:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        # 保存该模型的记录（JSON格式，便于查看）
        records_file_model_json = model_dir / "records.json"
        with open(records_file_model_json, 'w', encoding='utf-8') as f:
            json.dump(model_records, f, indent=2, ensure_ascii=False)
        
        # 保存该模型的画像（如果存在）
        if model_name in model_profiles:
            profile_file = model_dir / "model_profile.json"
            with open(profile_file, 'w', encoding='utf-8') as f:
                json.dump(model_profiles[model_name], f, indent=2, ensure_ascii=False)
        
        # 计算模型统计信息
        eligible_count = sum(1 for r in model_records if r.get('agent_output', {}).get('adjudication') == 'eligible')
        total_scores = [r.get('optional_scores', {}).get('total_score', 0) for r in model_records if r.get('optional_scores', {}).get('total_score') is not None]
        avg_score = sum(total_scores) / len(total_scores) if total_scores else 0.0
        
        model_summary = {
            "model_name": model_name,
            "task_id": task_id,
            "total_samples": len(model_records),
            "eligible_samples": eligible_count,
            "eligibility_rate": (eligible_count / len(model_records) * 100) if model_records else 0.0,
            "average_score": avg_score,
            "score_range": [min(total_scores), max(total_scores)] if total_scores else [0, 0]
        }
        
        summary_file = model_dir / "model_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(model_summary, f, indent=2, ensure_ascii=False)
        
        print(f"   ✅ {model_name}: {len(model_records)}条记录, 平均分{avg_score:.2f}, Eligible率{model_summary['eligibility_rate']:.2f}%")
    
    # 保存任务级别的汇总文件
    print("\n💾 保存任务级别汇总...")
    task_summary_file_new = new_base_dir / "task_summary.json"
    with open(task_summary_file_new, 'w', encoding='utf-8') as f:
        json.dump(task_summary, f, indent=2, ensure_ascii=False)
    
    # 保存所有模型画像
    model_profiles_file_new = new_base_dir / "model_profiles.json"
    with open(model_profiles_file_new, 'w', encoding='utf-8') as f:
        json.dump(model_profiles, f, indent=2, ensure_ascii=False)
    
    # 生成汇总报告
    report_file = new_base_dir / "evaluation_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# 评估结果报告 - {task_id}\n\n")
        f.write(f"**生成时间**: {Path(__file__).stat().st_mtime}\n\n")
        f.write(f"## 任务级别统计\n\n")
        f.write(f"- **总样本数**: {task_summary.get('total_samples', 0)}\n")
        f.write(f"- **总模型数**: {len(records_by_model)}\n")
        f.write(f"- **Eligible样本数**: {task_summary.get('eligible_samples', 0)}\n")
        f.write(f"- **Eligible率**: {task_summary.get('eligibility_rate', 0.0):.2f}%\n")
        f.write(f"- **可用率**: {task_summary.get('availability_rate', 0.0):.2f}%\n\n")
        
        f.write(f"## 模型排名（按平均分）\n\n")
        model_summaries = []
        for model_name, model_records in records_by_model.items():
            total_scores = [r.get('optional_scores', {}).get('total_score', 0) for r in model_records if r.get('optional_scores', {}).get('total_score') is not None]
            avg_score = sum(total_scores) / len(total_scores) if total_scores else 0.0
            eligible_count = sum(1 for r in model_records if r.get('agent_output', {}).get('adjudication') == 'eligible')
            model_summaries.append({
                'model_name': model_name,
                'avg_score': avg_score,
                'eligible_count': eligible_count,
                'total_samples': len(model_records)
            })
        
        model_summaries.sort(key=lambda x: x['avg_score'], reverse=True)
        
        f.write("| 排名 | 模型名称 | 样本数 | 平均分 | Eligible数 | Eligible率 |\n")
        f.write("|------|----------|--------|--------|------------|------------|\n")
        for rank, summary in enumerate(model_summaries, 1):
            eligible_rate = (summary['eligible_count'] / summary['total_samples'] * 100) if summary['total_samples'] > 0 else 0.0
            f.write(f"| {rank} | {summary['model_name']} | {summary['total_samples']} | "
                   f"{summary['avg_score']:.2f} | {summary['eligible_count']} | {eligible_rate:.2f}% |\n")
    
    print(f"\n✅ 结果已重新组织到: {new_base_dir}")
    print(f"   目录结构:")
    print(f"   {new_base_dir}/")
    print(f"   ├── task_summary.json")
    print(f"   ├── model_profiles.json")
    print(f"   ├── evaluation_report.md")
    print(f"   └── [model_name]/")
    print(f"       ├── records.jsonl")
    print(f"       ├── records.json")
    print(f"       ├── model_profile.json")
    print(f"       └── model_summary.json")


def fix_task_summary(records_file: str, task_summary_file: str):
    """修复任务摘要中的eligibility_rate计算错误"""
    print("\n" + "=" * 80)
    print("修复任务摘要")
    print("=" * 80)
    
    # 加载记录
    with open(records_file, 'r', encoding='utf-8') as f:
        records = [json.loads(line) for line in f]
    
    # 重新计算eligibility_rate
    total_samples = len(records)
    eligible_samples = sum(1 for r in records if r.get('agent_output', {}).get('adjudication') == 'eligible')
    eligibility_rate = (eligible_samples / total_samples * 100) if total_samples > 0 else 0.0
    
    # 加载现有任务摘要
    with open(task_summary_file, 'r', encoding='utf-8') as f:
        task_summary = json.load(f)
    
    # 更新eligibility_rate
    task_summary['eligibility_rate'] = eligibility_rate
    task_summary['total_samples'] = total_samples
    task_summary['eligible_samples'] = eligible_samples
    task_summary['ineligible_samples'] = total_samples - eligible_samples
    
    # 保存修复后的任务摘要
    with open(task_summary_file, 'w', encoding='utf-8') as f:
        json.dump(task_summary, f, indent=2, ensure_ascii=False)
    
    print(f"   ✅ 修复完成:")
    print(f"      - 总样本数: {total_samples}")
    print(f"      - Eligible样本数: {eligible_samples}")
    print(f"      - Eligible率: {eligibility_rate:.2f}%")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="检查并重新组织评估结果")
    parser.add_argument("--task", type=str, required=True, choices=["S1", "M1", "M3"], help="任务ID")
    parser.add_argument("--results_dir", type=str, default="./results/deterministic", help="结果目录")
    parser.add_argument("--check_only", action="store_true", help="仅检查，不重新组织")
    parser.add_argument("--fix_only", action="store_true", help="仅修复，不重新组织")
    
    args = parser.parse_args()
    
    task_id = args.task
    results_dir = Path(args.results_dir)
    
    # 文件路径
    records_file = results_dir / f"records_{task_id}_deterministic.jsonl"
    task_summary_file = results_dir / f"task_summary_{task_id}_deterministic.json"
    model_profiles_file = results_dir / f"model_profiles_{task_id}_deterministic.json"
    
    # 检查文件是否存在
    if not records_file.exists():
        print(f"❌ 记录文件不存在: {records_file}")
        return
    
    if not task_summary_file.exists():
        print(f"❌ 任务摘要文件不存在: {task_summary_file}")
        return
    
    if not model_profiles_file.exists():
        print(f"❌ 模型画像文件不存在: {model_profiles_file}")
        return
    
    # 检查结果质量
    quality_ok = check_results_quality(
        str(records_file),
        str(task_summary_file),
        str(model_profiles_file)
    )
    
    if args.check_only:
        return
    
    # 修复任务摘要
    if not quality_ok or args.fix_only:
        fix_task_summary(str(records_file), str(task_summary_file))
        if args.fix_only:
            return
    
    # 重新组织结果
    reorganize_results(
        str(results_dir),
        task_id,
        str(records_file),
        str(task_summary_file),
        str(model_profiles_file)
    )


if __name__ == "__main__":
    main()
