# LLM Judge 实现计划

## 已完成

### 1. Rubric定义 (`rubric/rubric_definition.py`)
- ✅ 5维度×4档定义
- ✅ Grade到Score的固定映射
- ✅ 单调性校验规则
- ✅ Evidence字段定义

### 2. LLMJudge类 (`agents/llm_judge.py`)
- ✅ Evidence-only输入（不含raw response）
- ✅ 单调性校验
- ✅ Evidence引用校验
- ✅ 确定性保证（temperature=0 + 缓存）
- ✅ Fallback机制
- ✅ LLM API调用框架（需要OpenAI API key）

### 3. LLMBasedFusion (`fusion/llm_based_fusion.py`)
- ✅ 使用LLM Judge输出计算分数
- ✅ 固定映射协议（Grade → Score）
- ✅ 向后兼容（保留legacy scores）

## 待完成

### 1. 集成到主评估流程
- [ ] 修改`main.py`：添加LLM Judge选项
- [ ] 修改`evaluate_sample`：使用LLMBasedFusion替代RuleBasedFusion
- [ ] 更新配置：添加LLM Judge配置选项

### 2. 实现LLM API调用
- [ ] 安装OpenAI库：`pip install openai`
- [ ] 设置API key：环境变量或配置文件
- [ ] 测试API调用：确保能正常调用

### 3. 消融实验
- [ ] Rule-only baseline：使用RuleBasedFusion
- [ ] LLM-judge (evidence-only)：使用LLMBasedFusion
- [ ] LLM-judge (含raw text)：对比实验（证明evidence-only有效）

### 4. 论文材料
- [ ] Rubric表格（5维度×4档）
- [ ] Judge Prompt模板
- [ ] 固定映射协议说明
- [ ] 消融实验结果

## 使用方法

### 配置LLM Judge

在`main.py`的`_create_default_config`中：

```python
fusion_protocol={
    "type": "llm_based",  # 改为llm_based
    "llm_judge": {
        "model": "gpt-4o",
        "temperature": 0,
        "api_key": os.getenv("OPENAI_API_KEY"),
        "max_retries": 3
    },
    "gating_rules": {
        "protocol_failure": {"max_allowed": 0, "severity": "critical"},
        "safety_constraint_violation": {"max_allowed": 0, "severity": "critical"},
        "key_field_missing": {"max_allowed": 0, "severity": "critical"}
    }
}
```

### 运行评估

```python
from fly_eval_plus_plus.main import FLYEvalPlusPlus

# 使用LLM Judge
evaluator = FLYEvalPlusPlus()
# 评估会自动使用LLMBasedFusion（如果配置了llm_based）
```

## 关键设计决策

### 1. Evidence-Only输入
- **原因**：防止prompt injection和风格偏好
- **实现**：LLM Judge只接收evidence summary，不接收raw response

### 2. 固定映射协议
- **原因**：避免手工权重争议
- **实现**：Grade → Score映射写在代码中，论文中说明

### 3. 单调性校验
- **原因**：确保LLM输出符合硬规则
- **实现**：后验校验，不通过则fallback

### 4. 确定性保证
- **原因**：可重现性
- **实现**：temperature=0 + 缓存 + trace

## 论文表述要点

1. **LLM作为裁决器**：LLM根据rubric和evidence输出等级，不是自由打分
2. **固定映射协议**：等级到分数的映射是公开规约，不是手工权重
3. **证据驱动**：所有判断必须引用evidence ID，可追溯
4. **约束保证**：单调性、确定性、bias control确保可靠性

