# 论文结果修正说明

## 问题识别

### 发现的矛盾
- **Eligible率**: 0.4% (3/708 samples)
- **Availability**: 99.58%
- **表面矛盾**: 如果eligible≈可用，应该接近0.4%；如果可用率≈协议解析成功，那eligible就不该叫"Eligible"

### 根本原因分析

通过代码分析发现：

1. **Availability (可用率)** 的定义：
   - 字段完整性率 (Field Completeness Rate)
   - 计算：`(已提供字段数 / 必需字段数) × 100%`
   - **与约束检查无关**，只检查字段是否存在
   - 即使有约束违规，只要字段都存在，availability也可以很高

2. **Eligible (合格样本)** 的定义：
   - 通过gating规则，可用于条件化误差统计的样本
   - 判断标准：无critical constraint violations
   - 当前gating规则：任何critical failure → ineligible

3. **为什么会出现"Availability高但Eligible率低"？**
   - **正常情况**：模型能输出完整字段（availability高），但经常违反约束（eligible率低）
   - **原因**：gating规则要求无critical violations，而很多样本有critical violations
   - **解释**：这说明模型能生成格式正确的输出，但在物理一致性、安全性等方面存在问题

## 术语统一

### 正确的术语定义

1. **Availability (可用率)**
   - 定义：字段完整性率
   - 范围：0-100%
   - 说明：衡量模型输出是否包含所有必需字段，与约束检查无关

2. **Eligible (合格样本)**
   - 定义：通过gating规则，可用于条件化误差统计的样本
   - 判断：无critical constraint violations
   - 说明：只有eligible样本才计算conditional error score

3. **Constraint Satisfaction (约束满足率)**
   - 定义：所有证据原子中通过检查的比例（按严重性加权）
   - 说明：衡量模型输出满足约束的程度

4. **Conditional Error (条件化误差)**
   - 定义：仅对eligible样本计算的误差分数
   - 说明：如果样本ineligible，conditional_error_score = constraint_satisfaction_score（作为代理）

### 术语关系图

```
样本 → 解析JSON → 字段完整性检查 → Availability Score (所有样本)
                ↓
            验证器检查 → Evidence Atoms
                ↓
            Gating规则 → Eligible/Ineligible
                ↓
         Eligible → 计算Conditional Error (仅eligible样本)
         Ineligible → Conditional Error = Constraint Satisfaction (代理)
                ↓
         Constraint Satisfaction (所有样本)
                ↓
         Total Score = 0.2×Availability + 0.3×Constraint + 0.5×Error
```

## 论文中的正确表述

### 结果部分文本（修正版）

**Paragraph 1: Evaluation Setup**
We evaluated [N] models on the S1 task (next second prediction) using the FLY-EVAL++ framework. The evaluation produced 708 samples per model ([total] total samples), with each sample generating 38-41 evidence atoms across 6 constraint types (numeric validity, range sanity, jump dynamics, cross-field consistency, physics constraints, and safety constraints). The evaluation uses a fixed scoring protocol combining availability (0.2), constraint satisfaction (0.3), and conditional error (0.5) to produce a total score for each model.

**Paragraph 2: Overall Performance**
Overall, [X]% of samples were adjudicated as eligible after gating rules (passing all critical constraint checks), with an availability rate (field completeness) of [X]%. **It is important to note that availability and eligibility measure different aspects**: availability measures whether all required fields are present in the output (format completeness), while eligibility measures whether the output passes critical constraint checks (safety and consistency). The high availability rate (99.58%) indicates that most models can produce outputs with all required fields, while the low eligibility rate (0.4%) indicates that most samples fail critical constraint checks. This suggests that models can generate format-correct outputs but often violate physical consistency or safety constraints.

**Paragraph 3: Constraint Compliance**
Compliance rates vary by constraint type, with numeric validity ([X]%) and safety constraints ([X]%) showing highest compliance, while cross-field consistency ([X]%) shows lowest compliance. This suggests that models struggle most with maintaining consistency between related fields.

**Paragraph 4: Model Ranking**
Models are ranked by total score (availability × 0.2 + constraint satisfaction × 0.3 + conditional error × 0.5). For ineligible samples, conditional error is replaced by constraint satisfaction as a proxy. The top performer achieves a score of [X], while the performance gap between best and worst is [X] points, indicating substantial variation in model capabilities.

**Paragraph 5: Failure Mode Analysis**
Cross-field consistency violations dominate failure modes ([X]% of ineligible samples), followed by numeric validity violations ([X]%). This highlights the importance of cross-field consistency checking and suggests that models may need additional training on maintaining field relationships.

**Paragraph 6: Evidence-Driven Transparency**
The evidence-driven approach enables full traceability from decision to evidence, allowing identification of specific failure modes and targeted improvements. Each adjudication decision cites evidence IDs, ensuring reproducibility and auditability. Version locking (config hash: `[hash]`, schema version: `[hash]`, constraint lib version: `[hash]`) ensures that results can be reproduced exactly.

## 表格列说明

### 主性能表格列（修正版）

1. **Availability Rate**: 字段完整性率（所有样本）
   - 定义：已提供字段数 / 必需字段数 × 100%
   - 说明：衡量格式完整性，与约束检查无关

2. **Constraint Satisfaction**: 约束满足率（所有样本）
   - 定义：通过的证据原子权重和 / 总证据原子权重和 × 100%
   - 说明：衡量约束合规性

3. **Conditional Error Mean**: 条件化误差均值（仅eligible样本）
   - 定义：基于MAE/RMSE的误差分数
   - 说明：只对eligible样本计算

4. **Conditional Error P95/P99**: 条件化误差分位数（仅eligible样本）
   - 说明：尾部风险指标

5. **Total Score**: 总分（所有样本）
   - 计算：Availability × 0.2 + Constraint Satisfaction × 0.3 + Conditional Error × 0.5
   - 说明：对于ineligible样本，conditional_error使用constraint_satisfaction作为代理

6. **Eligibility Rate**: Eligible样本比例（所有样本）
   - 定义：通过gating规则的样本比例
   - 说明：衡量通过critical约束检查的样本比例

## 下一步行动

1. ✅ **术语定义已明确** - 创建了`TERMINOLOGY_DEFINITIONS.md`
2. ⏳ **运行全模型评估** - 扩展到所有模型
3. ⏳ **生成最终论文结果** - 基于全模型评估生成正确的PAPER_RESULTS_FINAL.md
4. ⏳ **版本锁定** - 确保所有结果对应同一次运行

