# FLY-EVAL++ 论文交付清单

**版本**: v1.0.0  
**日期**: 2025-01-19

---

## ✅ 1. 论文结果固化（必须做）

### 1.1 运行最终官方结果

**命令**:
```bash
cd ICML2026/fly_eval_plus_plus
python3 -m fly_eval_plus_plus.run_final_evaluation
```

**输出文件**:
- `results/final_official_v1.0.0/records_S1.json`
- `results/final_official_v1.0.0/records_M1.json`
- `results/final_official_v1.0.0/records_M3.json`
- `results/final_official_v1.0.0/task_summaries.json`
- `results/final_official_v1.0.0/model_profiles.json`
- `results/final_official_v1.0.0/version_info.json`

**状态**: ⚠️ 待运行（需要完整数据）

### 1.2 记录版本信息

**在论文中记录**:
- Config Hash: `[从version_info.json获取]`
- Schema Version: `[从version_info.json获取]`
- Constraint Lib Version: `[从version_info.json获取]`
- Evaluator Version: `1.0.0`

**位置**: Method或Appendix的Reproducibility部分

**状态**: ⚠️ 待运行后获取

### 1.3 导出论文主表/主图

**命令**:
```bash
python3 -m fly_eval_plus_plus.export_paper_tables \
    results/final_official_v1.0.0/model_profiles.json
```

**输出文件**:
- `results/paper_tables/main_performance_table.tex` (主表)
- `results/paper_tables/constraint_satisfaction_table.tex`
- `results/paper_tables/failure_mode_table.tex`
- `results/paper_tables/tail_risk_table.tex`

**表格内容**:
1. **主表**: Model, Availability Rate, Constraint Satisfaction, Conditional Error (Mean/P95/P99), Total Score
2. **约束满足表**: 各模型按约束类型的违规数
3. **失败模式表**: 各模型按失败模式的分布
4. **尾部风险表**: P95, P99, 高风险率

**状态**: ✅ 功能已实现（需要pandas）

---

## ✅ 2. 方法论写作材料（强烈建议尽快做）

### 2.1 对象定义

**文档**: `METHODOLOGY_PAPER.md` Section 2

**包含**:
- EvidenceAtom定义
- Sample定义
- ModelOutput定义
- Record定义
- ModelConfidence定义

**状态**: ✅ 已完成

### 2.2 Algorithm伪代码

**文档**: `METHODOLOGY_PAPER.md` Section 8

**包含**:
- Main Evaluation Algorithm
- Task Summary Generation Algorithm
- Model Profile Generation Algorithm

**状态**: ✅ 已完成

### 2.3 证据原子Schema

**文档**: `METHODOLOGY_PAPER.md` Section 2.1

**包含**:
- EvidenceAtom结构
- Severity级别定义
- Scope定义
- 命名规范（constraint.<family>.<rule>）

**状态**: ✅ 已完成

### 2.4 Failure Taxonomy

**文档**: `METHODOLOGY_PAPER.md` Section 6

**包含**:
- 6种失败模式
- Severity分类
- 失败模式到证据类型的映射

**状态**: ✅ 已完成

### 2.5 Trace可复现性说明

**文档**: `METHODOLOGY_PAPER.md` Section 7

**包含**:
- Version locking机制
- Config hash, schema version, constraint_lib version
- Reproducibility guarantee

**状态**: ✅ 已完成

### 2.6 Agent工作解释

**文档**: `METHODOLOGY_PAPER.md` Section 11

**要点**:
- Agent不是"主观打分器"
- Agent是"证据编排与裁决/归因"
- Rule-based版本是agent的一个instantiation
- 强调evidence attribution和traceability

**状态**: ✅ 已完成

---

## ✅ 3. 发布与可信度收尾（可选但加分）

### 3.1 扩充黄金测试用例

**文件**: `tests/test_verifiers.py`

**已添加**:
- ✅ 边界值测试（TestRangeSanityChecker.test_boundary_values）
- ✅ 极端值测试（TestSafetyConstraintChecker.test_extreme_speed_detection, test_extreme_altitude_detection）
- ✅ Prompt injection测试（TestRangeSanityChecker.test_prompt_injection_resilience）

**状态**: ✅ 已完成

### 3.2 README完善

**文件**: `README.md`

**已添加**:
- ✅ 快速开始部分
- ✅ 环境依赖
- ✅ 一键复现命令
- ✅ 数据需求清单
- ✅ 配置文件说明
- ✅ 使用示例（单样本、批量、最终评估、导出表格）

**状态**: ✅ 已完成

### 3.3 配置文件固定输出

**说明**: 系统使用默认配置（v1.0.0），配置信息记录在`Record.trace`中

**配置文件位置**: `main.py` 中的 `_create_default_config()`

**状态**: ✅ 已实现

---

## 📋 交付清单

### 必须完成（论文结果固化）

- [ ] 运行最终官方评估（所有任务、所有模型）
- [ ] 锁定输出文件为论文版本
- [ ] 记录版本信息到论文
- [ ] 导出论文主表/主图

### 强烈建议（方法论写作材料）

- [x] 对象定义文档
- [x] Algorithm伪代码
- [x] 证据原子Schema
- [x] Failure Taxonomy
- [x] Trace可复现性说明
- [x] Agent工作解释

### 可选但加分（发布与可信度）

- [x] 扩充黄金测试用例
- [x] README完善
- [x] 配置文件固定输出

---

## 🎯 下一步行动

1. **立即执行**: 运行最终官方评估，锁定论文版本结果
2. **尽快完成**: 将方法论材料整合到论文Method部分
3. **可选**: 完善测试用例，准备开源发布

---

**清单状态**: ✅ 方法论材料已完成，待运行最终评估

