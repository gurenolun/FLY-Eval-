# FLY-EVAL++ Framework

**Evidence-Driven Evaluation Framework for Safety-Constrained Embodied Contexts**

**Version**: v1.0.0  
**Status**: ✅ Complete and ready for paper use

## 概述

FLY-EVAL++ 是一个适用于 safety-constrained embodied contexts 的评测方法论框架，将评测建模为"证据驱动的核验与裁决（evidence-traceable adjudication）"。

## 快速开始

### 环境依赖

```bash
# Python 3.8+
pip install numpy pandas
```

### 一键复现最终结果

```bash
cd ICML2026/fly_eval_plus_plus

# 运行最终官方评估
python3 -m fly_eval_plus_plus.run_final_evaluation

# 导出论文表格
python3 -m fly_eval_plus_plus.export_paper_tables \
    results/final_official_v1.0.0/model_profiles.json
```

### 数据需求清单

1. **模型输出数据**:
   - S1: `data/model_results/S1_20251106_020205/`
   - M1: `model_invocation/results/M1/20251107_155714/`
   - M3: `model_invocation/results/M3/20251108_155714/`

2. **参考数据**:
   - S1: `data/reference_data/next_second_pairs.jsonl`
   - M1/M3: `data/reference_data/flight_3window_samples.jsonl`

3. **模型置信度数据**:
   - S1: `model_invocation/results/S1_Sampled/20251211_232322/confidence_scores_v8.json`
   - M1: `model_invocation/results/M1_Sampled/20251207_215742_cleaned/confidence_scores_v8.json`
   - M3: `model_invocation/results/M3_Sampled/20251213_000254/confidence_scores_v8.json`

4. **约束配置**:
   - `validity_standard.py`: FIELD_LIMITS
   - `validity_change_standard.py`: JUMP_THRESHOLDS

### 配置文件

系统使用默认配置（v1.0.0），配置信息记录在 `Record.trace` 中：
- Config Hash: 用于检测配置变更
- Schema Version: 用于检测schema变更
- Constraint Lib Version: 用于检测约束库变更

配置文件位置：`main.py` 中的 `_create_default_config()`

## 核心设计原则

1. **证据先行**: 所有可客观计算的部分（格式/字段有效性/物理与安全约束/误差指标）一律由离线工具全量计算形成证据包
2. **LLM职责明确化**: LLM只做三件事——生成可执行checklist、组织工具核验流程、基于证据输出裁决与归因
3. **评分可选且可复现**: 若需要leaderboard总分，采用固定协议的聚合器（rule-based）
4. **置信度是模型级先验**: 模型级置信度不进入样本级裁决，而作为模型画像的独立维度

## 架构

### 1. Executable Spec Layer（可执行规约层）
- `core/data_structures.py`: 定义所有数据结构（EvalConfig, Sample, ModelOutput, ModelConfidence, Record等）
- `config/`: 配置文件

### 2. Verifier Graph Layer（验证器图层）
- `core/verifier_base.py`: Verifier基类和VerifierGraph
- `verifiers/`: 具体验证器实现
  - `numeric_validity_checker.py`: 数值有效性检查（✅ 已实现）
  - `range_sanity_checker.py`: 范围合理性检查（✅ 已实现）
  - `jump_dynamics_checker.py`: 突变动态检查（✅ 已实现）
  - `physics_constraint_checker.py`: 物理约束检查（⚠️ 待实现）
  - `safety_constraint_checker.py`: 安全约束检查（⚠️ 待实现）
  - `cross_field_consistency_checker.py`: 跨字段一致性检查（⚠️ 待实现）

### 3. Evaluator-Agent Layer（评估器Agent层）
- `agents/evaluator_agent.py`: LLM-based evaluator agent（⚠️ 待实现LLM调用）

### 4. Evidence Fusion Layer（证据融合层）
- `fusion/rule_based_fusion.py`: Rule-based聚合器（⚠️ 待实现评分逻辑）

### 5. Reliability Harness（可靠性保证）
- TODO: 实现judge可靠性保证（固定模型版本、temperature=0、结构化输出校验等）

## 已实现功能

### ✅ 完全实现
- 数值有效性检查（NaN/Inf/类型/缺失）
- 范围合理性检查（使用FIELD_LIMITS）
- 突变动态检查（使用JUMP_THRESHOLDS，支持角度字段）
- JSON解析和API错误检测
- 基础数据结构定义
- Verifier Graph框架

### ⚠️ 部分实现（函数已定义，逻辑待完善）
- Agent checklist生成
- Agent裁决和归因
- 证据融合和评分
- 任务级和模型级汇总

### ❌ 待实现
- 物理约束规则
- 安全约束规则
- 跨字段一致性规则
- LLM API调用
- 可靠性测试

## 使用示例

```python
from fly_eval_plus_plus import FLYEvalPlusPlus
from fly_eval_plus_plus.core.data_structures import Sample, ModelOutput

# 初始化评估器
evaluator = FLYEvalPlusPlus()

# 创建样本和模型输出
sample = Sample(
    sample_id="S1_001",
    task_id="S1",
    context={"question": "...", "current_state": {...}},
    gold={"next_second": {...}, "available": True}
)

model_output = ModelOutput(
    model_name="claude-3-7-sonnet",
    sample_id="S1_001",
    raw_response_text="...",
    timestamp="2025-01-19",
    task_id="S1"
)

# 评估样本
record = evaluator.evaluate_sample(sample, model_output)

# 查看结果
print(f"Adjudication: {record.agent_output['adjudication']}")
print(f"Evidence atoms: {len(record.evidence_pack['atoms'])}")
```

## 数据来源

- **模型输出**: `model_invocation/results/{S1,M1,M3}/{timestamp}/`
- **参考数据**: `ICML2026/data/reference_data/`
- **模型置信度**: `model_invocation/results/{S1,M1,M3}_Sampled/{timestamp}/confidence_scores_v8.json`
- **字段限制**: `validity_standard.py` (FIELD_LIMITS)
- **突变阈值**: `validity_change_standard.py` (JUMP_THRESHOLDS)

## 下一步开发

1. **完善Agent实现**: 实现LLM API调用和结构化输出
2. **实现物理约束**: 定义速度-高度一致性等规则
3. **实现安全约束**: 定义极端值检查和紧急模式
4. **实现跨字段一致性**: 定义GPS vs Baro高度等规则
5. **完善评分逻辑**: 实现rule-based fusion的完整评分
6. **添加可靠性测试**: 实现重复运行一致性测试等

## 文件结构

```
fly_eval_plus_plus/
├── __init__.py
├── main.py                    # 主入口
├── README.md
├── core/                      # 核心数据结构
│   ├── __init__.py
│   ├── data_structures.py     # 数据结构定义
│   └── verifier_base.py       # Verifier基类
├── verifiers/                 # 验证器实现
│   ├── __init__.py
│   ├── numeric_validity_checker.py
│   ├── range_sanity_checker.py
│   ├── jump_dynamics_checker.py
│   ├── physics_constraint_checker.py
│   ├── safety_constraint_checker.py
│   └── cross_field_consistency_checker.py
├── agents/                    # Agent层
│   ├── __init__.py
│   └── evaluator_agent.py
├── fusion/                    # 证据融合
│   ├── __init__.py
│   └── rule_based_fusion.py
├── utils/                     # 工具函数
│   ├── __init__.py
│   ├── json_parser.py
│   └── config_loader.py
└── config/                    # 配置文件
    └── __init__.py
```

