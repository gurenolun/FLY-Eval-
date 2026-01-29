#!/usr/bin/env python3
"""
确定性评估系统（不使用大模型）
基于规则和确定性算子进行规模化评估S1/M1/M3任务的所有模型回复

使用方法:
    python run_deterministic_evaluation.py --task S1 --output_dir ./results/deterministic
    python run_deterministic_evaluation.py --task M1 --output_dir ./results/deterministic
    python run_deterministic_evaluation.py --task M3 --output_dir ./results/deterministic
    python run_deterministic_evaluation.py --all_tasks --output_dir ./results/deterministic
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from tqdm import tqdm
from datetime import datetime
import hashlib

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from fly_eval_plus_plus.main import FLYEvalPlusPlus
from fly_eval_plus_plus.core.data_structures import Sample, ModelOutput, ModelConfidence
from fly_eval_plus_plus.data_loader import DataLoader
from fly_eval_plus_plus.fusion.rule_based_fusion_aligned import RuleBasedFusionAligned


class DeterministicEvaluator:
    """
    确定性评估器（不使用LLM）
    基于规则和确定性算子进行评估
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化评估器
        
        Args:
            config_path: 配置文件路径（可选）
        """
        # 创建FLYEvalPlusPlus实例，但强制使用rule_based fusion
        self.evaluator = FLYEvalPlusPlus(config_path=config_path)
        
        # 强制使用rule_based fusion（不使用LLM，但与LLM Judge版本对齐）
        self.evaluator.fusion = RuleBasedFusionAligned(self.evaluator.config.fusion_protocol)
        
        # 数据加载器
        self.data_loader = DataLoader()
        
        print("✅ 确定性评估器初始化完成（不使用LLM）")
        print(f"   - 使用Fusion类型: RuleBasedFusion")
        print(f"   - Verifier数量: {len(self.evaluator.verifier_graph.verifiers)}")
    
    def evaluate_all_models(
        self,
        task_id: str,
        model_output_dir: str,
        reference_data_dir: str,
        confidence_data_dir: Optional[str] = None,
        output_dir: str = "./results/deterministic"
    ) -> Dict[str, Any]:
        """
        评估所有模型
        
        Args:
            task_id: 任务ID (S1/M1/M3)
            model_output_dir: 模型输出目录
            reference_data_dir: 参考数据目录
            confidence_data_dir: 置信度数据目录（可选）
            output_dir: 输出目录
            
        Returns:
            评估结果字典
        """
        print(f"\n{'='*80}")
        print(f"开始评估任务: {task_id}")
        print(f"{'='*80}")
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 加载数据
        print("\n📂 加载数据...")
        
        # 获取所有模型名称
        model_output_path = Path(model_output_dir)
        if not model_output_path.exists():
            print(f"   ❌ 模型输出目录不存在: {model_output_dir}")
            return None
        
        model_dirs = [d for d in model_output_path.iterdir() if d.is_dir()]
        model_names = [d.name for d in model_dirs]
        print(f"   - 找到 {len(model_names)} 个模型")
        
        # 加载置信度数据（可选，统一加载）
        model_confidence_dict = {}
        if confidence_data_dir:
            try:
                model_confidence_dict = self.data_loader.load_model_confidence()
                print(f"   - 置信度数据: {len(model_confidence_dict)}个模型")
            except Exception as e:
                print(f"   ⚠️  加载置信度数据失败: {e}")
        
        # 评估所有模型
        all_records = []
        model_summaries = {}
        
        for model_name in tqdm(model_names, desc=f"评估{task_id}任务", unit="模型"):
            print(f"\n📊 评估模型: {model_name}")
            
            # 使用DataLoader创建samples和model_outputs
            try:
                samples, model_outputs = self.data_loader.create_samples_and_outputs(
                    task_id=task_id,
                    model_name=model_name
                )
            except Exception as e:
                print(f"   ⚠️  加载模型数据失败: {e}")
                continue
            
            if not samples or not model_outputs:
                print(f"   ⚠️  模型 {model_name} 无数据")
                continue
            
            print(f"   - 样本数: {len(samples)}")
            
            # 加载置信度数据（可选）
            model_confidence = None
            if confidence_data_dir:
                try:
                    confidence_dict = self.data_loader.load_model_confidence()
                    if model_name in confidence_dict:
                        model_confidence = confidence_dict[model_name]
                except:
                    pass
            
            model_records = []
            model_scores = []
            
            # 评估每个样本
            for i, sample in enumerate(tqdm(samples, desc=f"  {model_name}", leave=False, unit="样本")):
                # 获取对应的模型输出
                if i >= len(model_outputs):
                    continue
                
                model_output = model_outputs[i]
                
                # 评估样本
                try:
                    record = self.evaluator.evaluate_sample(
                        sample=sample,
                        model_output=model_output,
                        model_confidence=model_confidence
                    )
                    model_records.append(record)
                    
                    # 收集分数
                    if record.optional_scores:
                        total_score = record.optional_scores.get('total_score', 0)
                        if total_score is not None:
                            model_scores.append(float(total_score))
                
                except Exception as e:
                    print(f"    ⚠️  样本 {sample.sample_id} 评估失败: {e}")
                    continue
            
            # 保存模型记录
            if model_records:
                all_records.extend(model_records)
                
                # 计算模型统计
                avg_score = sum(model_scores) / len(model_scores) if model_scores else 0
                
                # 统计eligible样本（agent_output是dict）
                eligible_count = 0
                for r in model_records:
                    if hasattr(r, 'agent_output'):
                        # Record对象，agent_output是dict
                        adjudication = r.agent_output.get('adjudication', 'ineligible')
                    else:
                        # 已经是dict
                        adjudication = r.get('agent_output', {}).get('adjudication', 'ineligible')
                    if adjudication == "eligible":
                        eligible_count += 1
                
                eligible_rate = eligible_count / len(model_records) if model_records else 0
                
                model_summaries[model_name] = {
                    "model_name": model_name,
                    "task_id": task_id,
                    "sample_count": len(model_records),
                    "avg_score": avg_score,
                    "eligible_count": eligible_count,
                    "eligible_rate": eligible_rate,
                    "scores": model_scores
                }
                
                print(f"   ✅ 完成: {len(model_records)}个样本, 平均分: {avg_score:.2f}, Eligible率: {eligible_rate:.2%}")
        
        # 生成任务摘要
        task_summary = self.evaluator.generate_task_summary(
            task_id=task_id,
            records=all_records
        )
        
        # 加载置信度数据（如果需要）
        model_confidence_dict = {}
        if confidence_data_dir:
            try:
                model_confidence_dict = self.data_loader.load_model_confidence()
            except:
                pass
        
        # 生成模型画像
        model_profiles = {}
        for model_name, summary in model_summaries.items():
            model_confidence = None
            if model_name in model_confidence_dict:
                model_confidence = model_confidence_dict[model_name]
            
            # 过滤该模型的记录（兼容Record对象和dict）
            model_records_filtered = []
            for r in all_records:
                if hasattr(r, 'model_name'):
                    if r.model_name == model_name:
                        model_records_filtered.append(r)
                else:
                    if r.get('model_name') == model_name:
                        model_records_filtered.append(r)
            
            profile = self.evaluator.generate_model_profile(
                records=model_records_filtered,
                model_confidence=model_confidence
            )
            model_profiles[model_name] = profile
        
        # 保存结果
        self._save_results(
            task_id=task_id,
            records=all_records,
            task_summary=task_summary,
            model_profiles=model_profiles,
            model_summaries=model_summaries,
            output_dir=output_dir
        )
        
        return {
            "task_id": task_id,
            "total_samples": len(samples),
            "total_models": len(model_summaries),
            "total_records": len(all_records),
            "model_summaries": model_summaries,
            "task_summary": task_summary,
            "model_profiles": model_profiles
        }
    
    def _save_results(
        self,
        task_id: str,
        records: List[Any],
        task_summary: Any,
        model_profiles: Dict[str, Any],
        model_summaries: Dict[str, Any],
        output_dir: str
    ):
        """保存评估结果"""
        print(f"\n💾 保存结果到: {output_dir}")
        
        # 保存记录（JSONL格式，增量保存）
        records_file = os.path.join(output_dir, f"records_{task_id}_deterministic.jsonl")
        with open(records_file, 'w', encoding='utf-8') as f:
            for record in records:
                # 转换为字典
                record_dict = self._record_to_dict(record)
                f.write(json.dumps(record_dict, ensure_ascii=False) + '\n')
        print(f"   ✅ 记录文件: {records_file} ({len(records)}条)")
        
        # 保存任务摘要
        task_summary_file = os.path.join(output_dir, f"task_summary_{task_id}_deterministic.json")
        task_summary_dict = self._task_summary_to_dict(task_summary)
        with open(task_summary_file, 'w', encoding='utf-8') as f:
            json.dump(task_summary_dict, f, indent=2, ensure_ascii=False)
        print(f"   ✅ 任务摘要: {task_summary_file}")
        
        # 保存模型画像
        model_profiles_file = os.path.join(output_dir, f"model_profiles_{task_id}_deterministic.json")
        with open(model_profiles_file, 'w', encoding='utf-8') as f:
            profiles_dict = {
                model_name: self._model_profile_to_dict(profile)
                for model_name, profile in model_profiles.items()
            }
            json.dump(profiles_dict, f, indent=2, ensure_ascii=False)
        print(f"   ✅ 模型画像: {model_profiles_file}")
        
        # 保存模型摘要（简化版）
        model_summaries_file = os.path.join(output_dir, f"model_summaries_{task_id}_deterministic.json")
        with open(model_summaries_file, 'w', encoding='utf-8') as f:
            json.dump(model_summaries, f, indent=2, ensure_ascii=False)
        print(f"   ✅ 模型摘要: {model_summaries_file}")
        
        # 生成指标报告
        self._generate_metrics_report(
            task_id=task_id,
            model_summaries=model_summaries,
            task_summary=task_summary,
            output_dir=output_dir
        )
    
    def _record_to_dict(self, record: Any) -> Dict[str, Any]:
        """将Record对象转换为字典"""
        # 如果已经有to_dict方法，直接使用
        if hasattr(record, 'to_dict'):
            return record.to_dict()
        
        # 如果已经是dict，直接返回
        if isinstance(record, dict):
            return record
        
        # 手动转换（兼容Record对象）
        protocol_result = record.protocol_result
        if isinstance(protocol_result, dict):
            protocol_dict = protocol_result
        else:
            # ProtocolResult对象
            parsing = protocol_result.parsing if hasattr(protocol_result, 'parsing') else {}
            field_completeness = protocol_result.field_completeness if hasattr(protocol_result, 'field_completeness') else {}
            protocol_dict = {
                "parsing": {
                    "success": parsing.success if hasattr(parsing, 'success') else parsing.get('success'),
                    "error": parsing.error if hasattr(parsing, 'error') else parsing.get('error')
                },
                "field_completeness": {
                    "completeness_rate": field_completeness.completeness_rate if hasattr(field_completeness, 'completeness_rate') else field_completeness.get('completeness_rate'),
                    "missing_fields": field_completeness.missing_fields if hasattr(field_completeness, 'missing_fields') else field_completeness.get('missing_fields', [])
                }
            }
        
        evidence_pack = record.evidence_pack if hasattr(record, 'evidence_pack') else {}
        if isinstance(evidence_pack, dict):
            evidence_atoms = evidence_pack.get('atoms', [])
            # 确保所有atoms都是字符串
            evidence_atoms = [str(atom) if not isinstance(atom, str) else atom for atom in evidence_atoms]
        else:
            evidence_atoms = [str(atom) for atom in evidence_pack.atoms] if hasattr(evidence_pack, 'atoms') else []
        
        agent_output = record.agent_output if hasattr(record, 'agent_output') else {}
        if isinstance(agent_output, dict):
            agent_dict = agent_output
        else:
            checklist = agent_output.checklist if hasattr(agent_output, 'checklist') else []
            agent_dict = {
                "checklist": [
                    {
                        "item_id": item.get("item_id") if isinstance(item, dict) else getattr(item, 'item_id', None),
                        "constraint_id": item.get("constraint_id") if isinstance(item, dict) else getattr(item, 'constraint_id', None),
                        "status": item.get("status") if isinstance(item, dict) else getattr(item, 'status', None),
                        "evidence_ids": item.get("evidence_ids", []) if isinstance(item, dict) else getattr(item, 'evidence_ids', [])
                    }
                    for item in checklist
                ],
                "adjudication": agent_output.adjudication if hasattr(agent_output, 'adjudication') else agent_output.get('adjudication', 'ineligible'),
                "attribution": agent_output.attribution if hasattr(agent_output, 'attribution') else agent_output.get('attribution', [])
            }
        
        trace = record.trace if hasattr(record, 'trace') else {}
        if isinstance(trace, dict):
            trace_dict = trace
        else:
            trace_dict = {
                "config_hash": getattr(trace, 'config_hash', None),
                "schema_version": getattr(trace, 'schema_version', None),
                "constraint_lib_version": getattr(trace, 'constraint_lib_version', None),
                "timestamp": getattr(trace, 'timestamp', None),
                "evaluator_version": getattr(trace, 'evaluator_version', None)
            }
        
        return {
            "sample_id": getattr(record, 'sample_id', None),
            "model_name": getattr(record, 'model_name', None),
            "task_id": getattr(record, 'task_id', None),
            "protocol_result": protocol_dict,
            "evidence_pack": {"atoms": evidence_atoms},
            "agent_output": agent_dict,
            "optional_scores": getattr(record, 'optional_scores', {}),
            "trace": trace_dict
        }
    
    def _task_summary_to_dict(self, task_summary: Any) -> Dict[str, Any]:
        """将TaskSummary对象转换为字典"""
        if isinstance(task_summary, dict):
            return task_summary
        
        if hasattr(task_summary, 'to_dict'):
            return task_summary.to_dict()
        
        # 手动转换
        return {
            "task_id": getattr(task_summary, 'task_id', None),
            "total_samples": getattr(task_summary, 'total_samples', 0),
            "eligible_samples": getattr(task_summary, 'eligible_samples', 0),
            "ineligible_samples": getattr(task_summary, 'ineligible_samples', 0),
            "compliance_rate": getattr(task_summary, 'compliance_rate', {}),
            "availability_rate": getattr(task_summary, 'availability_rate', 0.0),
            "eligibility_rate": getattr(task_summary, 'eligibility_rate', 0.0),
            "constraint_satisfaction_profile": getattr(task_summary, 'constraint_satisfaction_profile', {}),
            "failure_mode_distribution": getattr(task_summary, 'failure_mode_distribution', {}),
            "conditional_error_statistics": getattr(task_summary, 'conditional_error_statistics', {}),
            "tail_risks": getattr(task_summary, 'tail_risks', {})
        }
    
    def _model_profile_to_dict(self, model_profile: Any) -> Dict[str, Any]:
        """将ModelProfile对象转换为字典"""
        if isinstance(model_profile, dict):
            return model_profile
        
        if hasattr(model_profile, 'to_dict'):
            return model_profile.to_dict()
        
        # 手动转换（使用getattr安全访问）
        return {
            "model_name": getattr(model_profile, 'model_name', 'unknown'),
            "task_id": getattr(model_profile, 'task_id', None),
            "total_samples": getattr(model_profile, 'total_samples', 0),
            "eligible_samples": getattr(model_profile, 'eligible_samples', 0),
            "eligibility_rate": getattr(model_profile, 'eligibility_rate', 0.0),
            "availability_rate": getattr(model_profile, 'availability_rate', 0.0),
            "average_overall_score": getattr(model_profile, 'average_overall_score', 0.0),
            "constraint_satisfaction_profile": getattr(model_profile, 'constraint_satisfaction_profile', {}),
            "failure_mode_distribution": getattr(model_profile, 'failure_mode_distribution', {}),
            "conditional_error": getattr(model_profile, 'conditional_error', {}),
            "tail_risks": getattr(model_profile, 'tail_risks', {}),
            "model_confidence": getattr(model_profile, 'model_confidence', {})
        }
    
    def _generate_metrics_report(
        self,
        task_id: str,
        model_summaries: Dict[str, Any],
        task_summary: Any,
        output_dir: str
    ):
        """生成指标报告"""
        report_file = os.path.join(output_dir, f"metrics_report_{task_id}_deterministic.md")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# 确定性评估指标报告 - {task_id}\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**评估方法**: 确定性规则和算子（不使用LLM）\n\n")
            
            # 任务级别统计
            f.write("## 任务级别统计\n\n")
            # 处理task_summary可能是dict的情况
            if isinstance(task_summary, dict):
                total_samples = task_summary.get('total_samples', 0)
                availability_rate = task_summary.get('availability_rate', 0.0)
                eligibility_rate = task_summary.get('eligibility_rate', 0.0)
                compliance_rate = task_summary.get('compliance_rate', {})
            else:
                total_samples = getattr(task_summary, 'total_samples', 0)
                availability_rate = getattr(task_summary, 'availability_rate', 0.0)
                eligibility_rate = getattr(task_summary, 'eligibility_rate', 0.0)
                compliance_rate = getattr(task_summary, 'compliance_rate', {})
            
            f.write(f"- **总样本数**: {total_samples}\n")
            f.write(f"- **总模型数**: {len(model_summaries)}\n")
            if isinstance(compliance_rate, dict):
                f.write(f"- **合规率**: 见各约束类型\n")
            else:
                f.write(f"- **合规率**: {compliance_rate:.2%}\n")
            f.write(f"- **可用率**: {availability_rate:.2%}\n")
            f.write(f"- **Eligible率**: {eligibility_rate:.2%}\n\n")
            
            # 模型排名
            f.write("## 模型排名（按平均分）\n\n")
            sorted_models = sorted(
                model_summaries.items(),
                key=lambda x: x[1]['avg_score'],
                reverse=True
            )
            
            f.write("| 排名 | 模型名称 | 样本数 | 平均分 | Eligible率 |\n")
            f.write("|------|----------|--------|--------|------------|\n")
            
            for rank, (model_name, summary) in enumerate(sorted_models, 1):
                f.write(
                    f"| {rank} | {model_name} | {summary['sample_count']} | "
                    f"{summary['avg_score']:.2f} | {summary['eligible_rate']:.2%} |\n"
                )
            
            f.write("\n")
            
            # 详细指标
            f.write("## 详细指标\n\n")
            for model_name, summary in sorted_models:
                f.write(f"### {model_name}\n\n")
                f.write(f"- **样本数**: {summary['sample_count']}\n")
                f.write(f"- **平均分**: {summary['avg_score']:.2f}\n")
                f.write(f"- **Eligible率**: {summary['eligible_rate']:.2%}\n")
                f.write(f"- **分数范围**: {min(summary['scores']):.2f} - {max(summary['scores']):.2f}\n")
                f.write(f"- **分数中位数**: {sorted(summary['scores'])[len(summary['scores'])//2]:.2f}\n\n")
        
        print(f"   ✅ 指标报告: {report_file}")


def main():
    parser = argparse.ArgumentParser(description="确定性评估系统（不使用大模型）")
    parser.add_argument(
        "--task",
        type=str,
        choices=["S1", "M1", "M3"],
        help="任务ID (S1/M1/M3)"
    )
    parser.add_argument(
        "--all_tasks",
        action="store_true",
        help="评估所有任务"
    )
    parser.add_argument(
        "--model_output_dir",
        type=str,
        default="../data/model_results",
        help="模型输出目录"
    )
    parser.add_argument(
        "--reference_data_dir",
        type=str,
        default="../data/reference_data",
        help="参考数据目录"
    )
    parser.add_argument(
        "--confidence_data_dir",
        type=str,
        default=None,
        help="置信度数据目录（可选）"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./results/deterministic",
        help="输出目录"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="配置文件路径（可选）"
    )
    
    args = parser.parse_args()
    
    if not args.task and not args.all_tasks:
        parser.error("必须指定 --task 或 --all_tasks")
    
    # 创建评估器
    evaluator = DeterministicEvaluator(config_path=args.config)
    
    # 确定要评估的任务
    tasks = []
    if args.all_tasks:
        tasks = ["S1", "M1", "M3"]
    else:
        tasks = [args.task]
    
    # 评估每个任务
    all_results = {}
    for task_id in tasks:
        print(f"\n{'='*80}")
        print(f"开始评估任务: {task_id}")
        print(f"{'='*80}")
        
        # 根据任务确定数据路径（使用绝对路径）
        base_path = Path(__file__).parent.parent
        if task_id == "S1":
            task_model_dir = str(base_path / "data" / "model_results" / "S1_20251106_020205")
        elif task_id == "M1":
            # M1数据可能在外部路径
            task_model_dir = str(base_path / "data" / "model_results" / "M1" / "20251107_155714")
            if not os.path.exists(task_model_dir):
                # 尝试多个可能的路径
                possible_paths = [
                    "../../model_invocation/results/M1/20251107_155714",
                    "../../../model_invocation/results/M1/20251107_155714",
                    str(Path(__file__).parent.parent.parent / "model_invocation" / "results" / "M1" / "20251107_155714")
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        task_model_dir = path
                        break
        elif task_id == "M3":
            # M3数据可能在外部路径
            task_model_dir = str(base_path / "data" / "model_results" / "M3" / "20251108_155714")
            if not os.path.exists(task_model_dir):
                # 尝试多个可能的路径
                possible_paths = [
                    "../../model_invocation/results/M3/20251108_155714",
                    "../../../model_invocation/results/M3/20251108_155714",
                    str(Path(__file__).parent.parent.parent / "model_invocation" / "results" / "M3" / "20251108_155714")
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        task_model_dir = path
                        break
        else:
            print(f"⚠️  未知任务: {task_id}")
            continue
        
        # 参考数据路径
        reference_data_dir = str(base_path / "data" / "reference_data")
        
        # 评估
        result = evaluator.evaluate_all_models(
            task_id=task_id,
            model_output_dir=task_model_dir,
            reference_data_dir=reference_data_dir,
            confidence_data_dir=args.confidence_data_dir,
            output_dir=args.output_dir
        )
        
        all_results[task_id] = result
    
    # 生成综合报告
    print(f"\n{'='*80}")
    print("生成综合报告")
    print(f"{'='*80}")
    
    # 转换all_results中的TaskSummary对象为字典
    serializable_results = {}
    for task_id, result in all_results.items():
        if result is None:
            continue
        serializable_results[task_id] = {
            "task_id": result.get("task_id") if isinstance(result, dict) else getattr(result, "task_id", task_id),
            "total_samples": result.get("total_samples") if isinstance(result, dict) else getattr(result, "total_samples", 0),
            "total_models": result.get("total_models") if isinstance(result, dict) else len(result.get("model_summaries", {})) if isinstance(result, dict) else 0,
            "total_records": result.get("total_records") if isinstance(result, dict) else getattr(result, "total_records", 0),
            "model_summaries": result.get("model_summaries", {}) if isinstance(result, dict) else {},
            "task_summary": evaluator._task_summary_to_dict(result.get("task_summary")) if isinstance(result, dict) and result.get("task_summary") else {},
            "model_profiles": {k: evaluator._model_profile_to_dict(v) for k, v in result.get("model_profiles", {}).items()} if isinstance(result, dict) and result.get("model_profiles") else {}
        }
    
    summary_file = os.path.join(args.output_dir, "evaluation_summary_deterministic.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(serializable_results, f, indent=2, ensure_ascii=False)
    print(f"✅ 综合报告: {summary_file}")
    
    print(f"\n{'='*80}")
    print("✅ 所有评估完成！")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()

