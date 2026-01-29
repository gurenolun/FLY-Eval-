# FLY-EVAL++ 评估机制说明

## 评估架构

### 被评估的模型（21个）
这些是**待评估的模型**，它们的回复结果已经存在：
- claude-3-7-sonnet-20250219
- claude-sonnet-4-5-20250929
- deepseek-v3
- gpt-4o
- ... 等21个模型

这些模型的回复结果存储在：
- `ICML2026/data/model_results/S1_20251106_020205/`
- `ICML2026/data/model_results/merged_results_20250617_203957/`

### 评估框架（FLY-EVAL++）

FLY-EVAL++是一个**基于规则的评估框架**，用于评估上述21个模型的回复结果。

#### 评估组件

1. **验证器图（Verifier Graph）**
   - 6个基于规则的验证器：
     - `NumericValidityChecker`: 检查数值有效性（NaN, Inf, 类型）
     - `RangeSanityChecker`: 检查范围合理性（使用FIELD_LIMITS）
     - `JumpDynamicsChecker`: 检查突变/跳跃（使用JUMP_THRESHOLDS）
     - `CrossFieldConsistencyChecker`: 检查跨字段一致性
     - `PhysicsConstraintChecker`: 检查物理约束
     - `SafetyConstraintChecker`: 检查安全约束
   - **特点**: 完全基于规则，不依赖LLM

2. **评估器代理（EvaluatorAgent）**
   - **当前实现**: Rule-based（规则-based），**不使用LLM**
   - **配置**: 虽然配置中有 `"model": "gpt-4o"`，但实际代码中：
     - `generate_checklist()`: 使用规则映射，不调用LLM
     - `organize_verification_workflow()`: 基于证据原子映射，不调用LLM
     - `adjudicate()`: 基于规则判断（检查critical failures），不调用LLM
   - **LLM调用**: `call_llm()` 方法存在但未实现（返回空字符串）

3. **融合器（RuleBasedFusion）**
   - 基于固定协议计算分数
   - 不使用LLM

#### 评估流程

```
21个模型的回复结果
    ↓
FLY-EVAL++框架
    ↓
1. JSON解析（提取字段）
    ↓
2. 验证器图执行（6个规则验证器）
    ├─ NumericValidityChecker (规则)
    ├─ RangeSanityChecker (规则 + FIELD_LIMITS)
    ├─ JumpDynamicsChecker (规则 + JUMP_THRESHOLDS)
    ├─ CrossFieldConsistencyChecker (规则)
    ├─ PhysicsConstraintChecker (规则)
    └─ SafetyConstraintChecker (规则)
    ↓
3. 生成证据原子（Evidence Atoms）
    ↓
4. EvaluatorAgent裁决（规则-based，不调用LLM）
    ├─ 检查critical failures
    ├─ 生成checklist（规则映射）
    └─ 裁决：eligible/ineligible
    ↓
5. RuleBasedFusion计算分数
    ├─ Availability Score (字段完整性)
    ├─ Constraint Satisfaction Score (约束满足率)
    └─ Conditional Error Score (条件化误差)
    ↓
6. 生成评估结果
    ├─ Records (样本级)
    ├─ Task Summaries (任务级)
    └─ Model Profiles (模型级)
```

## 关键点

### 1. 评估框架不使用LLM
- **当前实现**: 完全基于规则
- **原因**: 为了可重现性和可解释性
- **优势**: 
  - 结果可重现
  - 评估过程透明
  - 不依赖外部API

### 2. 评估框架的"模型"配置
- 配置中有 `"model": "gpt-4o"`，但**实际未使用**
- 这是为未来扩展预留的接口
- 当前所有评估都是规则-based

### 3. 评估框架的输入
- **输入**: 21个模型的回复结果（JSON格式）
- **处理**: 基于规则验证和评分
- **输出**: 评估记录、汇总、画像

## 全模型评估的含义

"全模型评估"指的是：
- **评估所有21个模型的回复结果**
- **使用相同的FLY-EVAL++框架**（基于规则的验证器）
- **生成所有模型的评估结果**

**不是**：
- ❌ 使用LLM评估21个模型
- ❌ 使用另一个模型来评估这21个模型

## 评估框架的"智能"来源

虽然评估框架不使用LLM，但它仍然具有"智能"：

1. **规则库**:
   - `FIELD_LIMITS`: 物理约束（速度、高度等范围）
   - `JUMP_THRESHOLDS`: 突变阈值（检测不合理的跳跃）

2. **验证器逻辑**:
   - 跨字段一致性检查（GPS Alt vs Baro Alt）
   - 物理约束检查（速度-高度一致性）
   - 安全约束检查（快速下降、极端值）

3. **证据驱动**:
   - 每个验证结果都生成证据原子
   - 可追溯、可解释

## 总结

- **被评估**: 21个模型的回复结果
- **评估框架**: FLY-EVAL++（基于规则的验证器）
- **评估方式**: 规则-based，不使用LLM
- **全模型评估**: 对所有21个模型运行相同的评估流程

