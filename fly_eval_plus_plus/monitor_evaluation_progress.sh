#!/bin/bash
# Monitor evaluation progress

echo "=================================================================================="
echo "FLY-EVAL++ 评估进度监控"
echo "=================================================================================="
echo ""

# Check if evaluation is running
if ps aux | grep -v grep | grep -q "run_full_evaluation_llm_judge.py"; then
    echo "✅ 评估正在运行中"
    ps aux | grep -v grep | grep "run_full_evaluation_llm_judge.py" | head -1 | awk '{print "  进程ID: " $2 ", CPU: " $3 "%, MEM: " $4 "%"}'
else
    echo "⏸️  评估已停止"
fi

echo ""
echo "📊 当前进度:"
python3 fly_eval_plus_plus/generate_progress_report.py 2>/dev/null | tail -30

echo ""
echo "📁 结果文件:"
if [ -f "results/final_official_v1.0.0_llm_judge/records_S1_incremental.jsonl" ]; then
    RECORD_COUNT=$(wc -l < results/final_official_v1.0.0_llm_judge/records_S1_incremental.jsonl)
    FILE_SIZE=$(ls -lh results/final_official_v1.0.0_llm_judge/records_S1_incremental.jsonl | awk '{print $5}')
    echo "  - 增量文件: $RECORD_COUNT 条记录 ($FILE_SIZE)"
fi

if [ -f "results/final_official_v1.0.0_llm_judge/model_profiles.json" ]; then
    MODEL_COUNT=$(python3 -c "import json; f=open('results/final_official_v1.0.0_llm_judge/model_profiles.json'); print(len(json.load(f)))" 2>/dev/null)
    echo "  - 模型画像: $MODEL_COUNT 个模型"
fi

echo ""
echo "=================================================================================="

