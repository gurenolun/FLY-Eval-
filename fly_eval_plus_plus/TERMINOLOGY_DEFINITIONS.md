# FLY-EVAL++ 术语定义

## 核心术语

### 1. **Availability (可用率)**
- **定义**: 字段完整性率 (Field Completeness Rate)
- **计算**: `(已提供字段数 / 必需字段数) × 100%`
- **范围**: 0-100%
- **说明**: 
  - 衡量模型输出是否包含所有必需字段
  - **与约束检查无关**，只检查字段是否存在
  - 即使有约束违规，只要字段都存在，availability也可以很高
  - **对应表格列**: "Availability Rate" 或 "Field Completeness"

### 2. **Eligible (合格样本)**
- **定义**: 通过gating规则，可用于条件化误差统计的样本
- **判断标准**: 
  - 通过gating规则（无critical constraint violations）
  - 有ground truth数据可用于误差计算
- **说明**:
  - **与availability不同**：eligible要求通过约束检查，availability只要求字段存在
  - 只有eligible样本才计算conditional error score
  - **对应表格列**: "Eligibility Rate" 或 "Eligible Samples"

### 3. **Constraint Satisfaction (约束满足率)**
- **定义**: 所有证据原子中通过检查的比例（按严重性加权）
- **计算**: `(通过的证据原子权重和 / 总证据原子权重和) × 100%`
- **权重**: Critical=3.0, Warning=1.0, Info=0.5
- **说明**:
  - 衡量模型输出满足约束的程度
  - 包括所有约束类型（numeric, range, jump, cross-field, physics, safety）
  - **对应表格列**: "Constraint Satisfaction"

### 4. **Conditional Error (条件化误差)**
- **定义**: 仅对eligible样本计算的误差分数
- **计算**: 基于MAE和RMSE，转换为0-100分数
- **说明**:
  - 只对eligible样本计算（通过gating且有ground truth）
  - 如果样本ineligible，conditional_error_score = constraint_satisfaction_score（作为代理）
  - **对应表格列**: "Conditional Error (Mean/P95/P99)"

### 5. **Total Score (总分)**
- **定义**: 加权总分
- **计算**: `Availability × 0.2 + Constraint Satisfaction × 0.3 + Conditional Error × 0.5`
- **说明**:
  - 对于ineligible样本，conditional_error使用constraint_satisfaction作为代理
  - **对应表格列**: "Total Score"

## 术语关系

```
样本 → 解析JSON → 字段完整性检查 → Availability Score
                ↓
            验证器检查 → Evidence Atoms
                ↓
            Gating规则 → Eligible/Ineligible
                ↓
         Eligible → 计算Conditional Error
         Ineligible → Conditional Error = Constraint Satisfaction
                ↓
         Constraint Satisfaction (所有样本)
                ↓
         Total Score = 0.2×Availability + 0.3×Constraint + 0.5×Error
```

## 关键区别

### Availability vs Eligible
- **Availability**: 字段完整性（字段是否存在）
- **Eligible**: 约束合规性（是否通过gating规则）

**示例**:
- 样本A: 所有字段都存在，但有critical constraint violation
  - Availability = 100%
  - Eligible = No
  - Constraint Satisfaction < 100%

- 样本B: 所有字段都存在，无critical constraint violation
  - Availability = 100%
  - Eligible = Yes
  - Constraint Satisfaction = 100%

### 为什么会出现"Availability高但Eligible率低"？
- **正常情况**：模型能输出完整字段（availability高），但经常违反约束（eligible率低）
- **原因**：gating规则要求无critical violations，而很多样本有critical violations
- **解释**：这说明模型能生成格式正确的输出，但在物理一致性、安全性等方面存在问题

## 表格列说明

### 主性能表格列
1. **Availability Rate**: 字段完整性率（所有样本）
2. **Constraint Satisfaction**: 约束满足率（所有样本）
3. **Conditional Error Mean**: 条件化误差均值（仅eligible样本）
4. **Conditional Error P95**: 条件化误差95分位数（仅eligible样本）
5. **Conditional Error P99**: 条件化误差99分位数（仅eligible样本）
6. **Total Score**: 总分（所有样本，ineligible样本的error用constraint satisfaction代理）
7. **Eligibility Rate**: Eligible样本比例（所有样本）

## 论文中的表述建议

### 正确表述
- "Availability rate (field completeness) was 99.58%, indicating that most models can produce outputs with all required fields."
- "Eligibility rate (samples passing gating rules) was 0.4%, indicating that most samples fail critical constraint checks."
- "While models can produce complete outputs (high availability), they often violate constraints (low eligibility)."

### 错误表述（避免）
- ❌ "Eligible rate and availability rate are the same"
- ❌ "High availability means high eligibility"
- ❌ "Availability measures constraint compliance"

