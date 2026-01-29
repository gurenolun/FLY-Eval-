# 评估方法对比：确定性版本 vs LLM Judge版本

## 对比总结

经过检查，**两个版本的评估维度和方法不完全一致**。以下是详细对比：

---

## 1. 评估维度对比

### LLM Judge版本（5个维度）

1. **Protocol/Schema Compliance** (协议和模式合规性)
   - 基于：JSON解析、字段完整性、数值有效性
   - 等级：A/B/C/D

2. **Field Validity & Local Dynamics** (字段有效性和局部动力学)
   - 基于：范围合理性、突变检测
   - 等级：A/B/C/D

3. **Physics/Cross-field Consistency** (物理和跨字段一致性)
   - 基于：跨字段一致性、物理约束
   - 等级：A/B/C/D

4. **Safety Constraint Satisfaction** (安全约束满足)
   - 基于：安全约束检查
   - 等级：A/B/C/D

5. **Predictive Quality & Reliability** (预测质量和可靠性)
   - 基于：条件化误差（MAE/RMSE）、可靠性
   - 等级：A/B/C/D

### 确定性版本（原版 - 3个维度）

1. **Availability Score** (可用率)
   - 基于：字段完整性率
   - 分数：0-100

2. **Constraint Satisfaction Score** (约束满足度)
   - 基于：Evidence严重度加权
   - 分数：0-100

3. **Conditional Error Score** (条件化误差)
   - 基于：MAE/RMSE分段评分
   - 分数：0-100

### 确定性版本（对齐版 - 5个维度）✅

已创建 `rule_based_fusion_aligned.py`，使用与LLM Judge相同的5个维度：

1. **Protocol/Schema Compliance** ✅
2. **Field Validity & Local Dynamics** ✅
3. **Physics/Cross-field Consistency** ✅
4. **Safety Constraint Satisfaction** ✅
5. **Predictive Quality & Reliability** ✅

---

## 2. 评分方法对比

### LLM Judge版本

1. **LLM裁决**：使用LLM根据rubric和evidence输出等级
2. **等级映射**：A=1.0, B=0.75, C=0.5, D=0.0
3. **总分计算**：`mean(维度分数) × 100`
4. **推理过程**：LLM提供推理和证据引用

### 确定性版本（原版）

1. **直接计算**：基于evidence统计直接计算分数
2. **分段评分**：Availability、Constraint、Error分别计算
3. **总分计算**：`Availability×0.2 + Constraint×0.3 + Error×0.5`
4. **无推理**：纯数值计算

### 确定性版本（对齐版）✅

1. **规则映射**：基于rubric规则将evidence映射到等级
2. **等级映射**：A=1.0, B=0.75, C=0.5, D=0.0（与LLM Judge相同）
3. **总分计算**：`mean(维度分数) × 100`（与LLM Judge相同）
4. **确定性规则**：使用固定规则而非LLM推理

---

## 3. 验证器对比

### 两个版本都使用相同的6类验证器 ✅

1. **NumericValidityChecker** - 数值有效性
2. **RangeSanityChecker** - 范围合理性
3. **JumpDynamicsChecker** - 突变检测
4. **CrossFieldConsistencyChecker** - 跨字段一致性
5. **PhysicsConstraintChecker** - 物理约束
6. **SafetyConstraintChecker** - 安全约束

---

## 4. 关键差异

| 特性 | LLM Judge版本 | 确定性版本（原版） | 确定性版本（对齐版） |
|------|---------------|-------------------|---------------------|
| **维度数量** | 5个 | 3个 ❌ | 5个 ✅ |
| **评分方式** | 等级映射 | 直接计算 ❌ | 等级映射 ✅ |
| **总分计算** | mean(维度分数) | 加权求和 ❌ | mean(维度分数) ✅ |
| **使用LLM** | ✅ 是 | ❌ 否 | ❌ 否 |
| **可复现性** | 依赖LLM稳定性 | ✅ 100%可复现 | ✅ 100%可复现 |
| **评估速度** | 慢（API调用） | ✅ 快 | ✅ 快 |
| **成本** | 有API成本 | ✅ 无成本 | ✅ 无成本 |

---

## 5. 对齐方案

已创建 `rule_based_fusion_aligned.py`，使确定性版本与LLM Judge版本在以下方面保持一致：

### ✅ 维度对齐
- 使用相同的5个维度
- 每个维度使用相同的rubric定义

### ✅ 评分对齐
- 使用相同的等级映射（A/B/C/D → 1.0/0.75/0.5/0.0）
- 使用相同的总分计算方式（mean(维度分数) × 100）

### ✅ 规则对齐
- 基于相同的rubric规则进行等级判定
- 使用相同的evidence要求

### ❌ 推理差异（预期）
- LLM Judge版本：使用LLM进行推理和证据引用
- 确定性版本：使用固定规则进行判定（无推理文本）

---

## 6. 使用建议

### 如果需要与LLM Judge版本完全对齐：

使用 `rule_based_fusion_aligned.py`：

```python
from fly_eval_plus_plus.fusion.rule_based_fusion_aligned import RuleBasedFusionAligned

# 在 run_deterministic_evaluation.py 中已更新
evaluator.fusion = RuleBasedFusionAligned(config)
```

### 输出格式对比：

**LLM Judge版本输出**：
```json
{
  "grade_vector": {
    "protocol_schema_compliance": "A",
    "field_validity_local_dynamics": "A",
    "physics_cross_field_consistency": "D",
    "safety_constraint_satisfaction": "A",
    "predictive_quality_reliability": "B"
  },
  "dimension_scores": {
    "protocol_schema_compliance": 1.0,
    "field_validity_local_dynamics": 1.0,
    "physics_cross_field_consistency": 0.0,
    "safety_constraint_satisfaction": 1.0,
    "predictive_quality_reliability": 0.75
  },
  "overall_score": 75.0
}
```

**确定性版本（对齐版）输出**：
```json
{
  "grade_vector": {
    "protocol_schema_compliance": "A",
    "field_validity_local_dynamics": "A",
    "physics_cross_field_consistency": "D",
    "safety_constraint_satisfaction": "A",
    "predictive_quality_reliability": "B"
  },
  "dimension_scores": {
    "protocol_schema_compliance": 1.0,
    "field_validity_local_dynamics": 1.0,
    "physics_cross_field_consistency": 0.0,
    "safety_constraint_satisfaction": 1.0,
    "predictive_quality_reliability": 0.75
  },
  "overall_score": 75.0
}
```

**格式完全一致！** ✅

---

## 7. 总结

### 原版确定性评估系统
- ❌ 维度不一致（3个 vs 5个）
- ❌ 评分方法不一致
- ✅ 验证器一致

### 对齐版确定性评估系统
- ✅ 维度一致（5个）
- ✅ 评分方法一致（等级映射）
- ✅ 总分计算一致（mean）
- ✅ 验证器一致
- ❌ 推理过程不同（预期，因为不使用LLM）

**建议使用对齐版**，以确保两个版本的评估结果在维度、评分和格式上保持一致，便于对比和消融研究。

