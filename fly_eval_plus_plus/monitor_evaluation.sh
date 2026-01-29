#!/bin/bash
# Monitor evaluation progress

LOG_FILE="results/full_evaluation_s1.log"
RESULTS_DIR="results/final_official_v1.0.0_llm_judge"

echo "=================================================================================="
echo "FLY-EVAL++ 全模型评估监控"
echo "=================================================================================="
echo ""
echo "日志文件: $LOG_FILE"
echo "结果目录: $RESULTS_DIR"
echo ""

# Check if log file exists
if [ ! -f "$LOG_FILE" ]; then
    echo "⚠️  日志文件不存在，评估可能尚未开始"
    exit 1
fi

# Show last 20 lines
echo "最新日志（最后20行）:"
echo "--------------------------------------------------------------------------------"
tail -20 "$LOG_FILE"
echo "--------------------------------------------------------------------------------"
echo ""

# Count completed models
if [ -f "$RESULTS_DIR/model_profiles.json" ]; then
    echo "✅ 评估结果文件已生成"
    echo ""
    echo "已完成模型数:"
    python3 << 'PYTHON_SCRIPT'
import json
import os

results_dir = 'results/final_official_v1.0.0_llm_judge'
profiles_file = os.path.join(results_dir, 'model_profiles.json')
if os.path.exists(profiles_file):
    with open(profiles_file, 'r') as f:
        profiles = json.load(f)
    print(f"  {len(profiles)} 个模型")
    print("\n模型列表:")
    for model_name in sorted(profiles.keys()):
        print(f"  - {model_name}")
else:
    print("  0 个模型（结果文件不存在）")
PYTHON_SCRIPT
else
    echo "⏳ 评估结果文件尚未生成"
fi

echo ""
echo "=================================================================================="

