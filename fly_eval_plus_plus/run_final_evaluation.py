"""
Run Final Official Evaluation

Runs evaluation with v1.0.0 configuration and locks output files as paper version.
Records config_hash, schema_version, constraint_lib_version for paper.
"""

import json
import os
from datetime import datetime
from pathlib import Path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from run_evaluation import run_evaluation


def run_final_official_evaluation(
    task_ids=None,
    model_names=None,
    output_dir="results/final_official_v1.0.0",
    paper_version="v1.0.0"
):
    """
    Run final official evaluation for paper
    
    Args:
        task_ids: List of task IDs (default: ["S1", "M1", "M3"])
        model_names: List of model names (default: all models)
        output_dir: Output directory for final results
        paper_version: Paper version tag
    
    Returns:
        Dictionary with evaluation results and version info
    """
    if task_ids is None:
        task_ids = ["S1", "M1", "M3"]
    
    print("=" * 80)
    print("FLY-EVAL++ Final Official Evaluation")
    print(f"Paper Version: {paper_version}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)
    
    # Run evaluation
    results = run_evaluation(
        task_ids=task_ids,
        model_names=model_names,
        output_dir=output_dir
    )
    
    # Extract version info from first record
    version_info = {}
    if results['records']:
        for task_id in task_ids:
            task_records = results['records'].get(task_id, [])
            if task_records:
                first_record = task_records[0]
                trace = first_record.trace
                version_info = {
                    'config_version': trace.get('config_version'),
                    'config_hash': trace.get('config_hash'),
                    'schema_version': trace.get('schema_version'),
                    'constraint_lib_version': trace.get('constraint_lib_version'),
                    'evaluator_version': trace.get('evaluator_version'),
                    'timestamp': trace.get('timestamp')
                }
                break
    
    # Save version info
    version_file = os.path.join(output_dir, "version_info.json")
    with open(version_file, 'w', encoding='utf-8') as f:
        json.dump({
            'paper_version': paper_version,
            'evaluation_timestamp': datetime.now().isoformat(),
            'version_info': version_info,
            'task_ids': task_ids,
            'model_count': len(results.get('model_profiles', {}))
        }, f, indent=2)
    
    print(f"\n✅ Final evaluation complete!")
    print(f"   Output directory: {output_dir}")
    print(f"   Version info saved to: {version_file}")
    print(f"\n📋 Version Information for Paper:")
    print(f"   Config Hash: {version_info.get('config_hash')}")
    print(f"   Schema Version: {version_info.get('schema_version')}")
    print(f"   Constraint Lib Version: {version_info.get('constraint_lib_version')}")
    
    return {
        'results': results,
        'version_info': version_info,
        'output_dir': output_dir
    }


if __name__ == "__main__":
    # Run final official evaluation
    final_results = run_final_official_evaluation()
    print("\n✅ Final official evaluation locked for paper use")

