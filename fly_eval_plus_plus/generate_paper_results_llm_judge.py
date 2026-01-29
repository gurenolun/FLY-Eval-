"""
Generate Paper Results from LLM Judge Evaluation

基于LLM Judge评估结果生成论文结果和表格。
"""

import json
import os
import statistics
from pathlib import Path
from typing import Dict, List, Any


def load_llm_judge_results(results_dir: str) -> Dict[str, Any]:
    """Load LLM Judge evaluation results"""
    results = {}
    
    # Load task summaries
    summaries_file = os.path.join(results_dir, 'task_summaries.json')
    if os.path.exists(summaries_file):
        with open(summaries_file, 'r', encoding='utf-8') as f:
            results['task_summaries'] = json.load(f)
    
    # Load model profiles
    profiles_file = os.path.join(results_dir, 'model_profiles.json')
    if os.path.exists(profiles_file):
        with open(profiles_file, 'r', encoding='utf-8') as f:
            results['model_profiles'] = json.load(f)
    
    # Load version info
    version_file = os.path.join(results_dir, 'version_info.json')
    if os.path.exists(version_file):
        with open(version_file, 'r', encoding='utf-8') as f:
            results['version_info'] = json.load(f)
    
    return results


def generate_llm_judge_results_narrative(results: Dict[str, Any]) -> str:
    """Generate narrative text for Results section (LLM Judge version)"""
    task_summaries = results.get('task_summaries', {})
    model_profiles = results.get('model_profiles', {})
    version_info = results.get('version_info', {})
    
    narrative = []
    narrative.append("# Results Section Narrative - LLM Judge Version\n")
    narrative.append("**Generated from FLY-EVAL++ LLM Judge Evaluation Results**\n")
    
    # Version information
    if version_info:
        vi = version_info.get('version_info', {})
        narrative.append("## Reproducibility Information\n")
        narrative.append(f"- **Fusion Type**: `{vi.get('fusion_type')}` (LLM-based)")
        narrative.append(f"- **LLM Judge Model**: `{vi.get('llm_judge_model')}`")
        narrative.append(f"- **Config Hash**: `{vi.get('config_hash', 'N/A')}`")
        narrative.append(f"- **Schema Version**: `{vi.get('schema_version', 'N/A')}`")
        narrative.append(f"- **Constraint Lib Version**: `{vi.get('constraint_lib_version', 'N/A')}`")
        narrative.append(f"- **Evaluation Timestamp**: `{version_info.get('evaluation_timestamp')}`\n")
    
    # Task-level results
    narrative.append("## Task-Level Results\n")
    for task_id, summary in task_summaries.items():
        narrative.append(f"### {task_id} Task\n")
        narrative.append(f"We evaluated {summary.get('total_samples')} samples for the {task_id} task using LLM Judge. ")
        narrative.append(f"Of these, {summary.get('eligible_samples')} ({summary.get('eligible_samples')/summary.get('total_samples')*100:.1f}%) were adjudicated as eligible after gating rules. ")
        narrative.append(f"The overall availability rate (field completeness) was {summary.get('availability_rate'):.2f}%.\n")
        
        # Compliance rates
        compliance = summary.get('compliance_rate', {})
        narrative.append("**Constraint Compliance Rates**:\n")
        for constraint_type, rate in sorted(compliance.items(), key=lambda x: x[1], reverse=True):
            narrative.append(f"- {constraint_type}: {rate:.2f}%\n")
    
    # Model-level results
    narrative.append("\n## Model-Level Results (LLM Judge Scoring)\n")
    narrative.append(f"We evaluated {len(model_profiles)} models using LLM Judge. Models are ranked by total score from LLM Judge grades.\n")
    
    # Top performers
    model_scores = []
    for model_name, profile in model_profiles.items():
        data_profile = profile.get('data_driven_profile', {})
        total_stats = data_profile.get('score_statistics', {}).get('total', {})
        mean_score = total_stats.get('mean')
        if mean_score:
            model_scores.append((model_name, mean_score))
    
    model_scores.sort(key=lambda x: x[1], reverse=True)
    
    narrative.append("### Top Performers (LLM Judge Scores)\n")
    narrative.append("Models ranked by LLM Judge total score (from grade vector: A=1.0, B=0.75, C=0.5, D=0.0):\n")
    for i, (model_name, score) in enumerate(model_scores[:10], 1):
        narrative.append(f"{i}. **{model_name}**: {score:.2f}\n")
    
    # Performance distribution
    narrative.append("\n### Performance Distribution\n")
    if model_scores:
        scores = [s for _, s in model_scores]
        narrative.append(f"- Mean total score: {statistics.mean(scores):.2f}")
        narrative.append(f"- Median total score: {statistics.median(scores):.2f}")
        narrative.append(f"- Std: {statistics.stdev(scores) if len(scores) > 1 else 0:.2f}")
        narrative.append(f"- Min: {min(scores):.2f}")
        narrative.append(f"- Max: {max(scores):.2f}\n")
    
    # LLM Judge specific insights
    narrative.append("\n## LLM Judge Methodology Insights\n")
    narrative.append("The LLM Judge evaluates each sample based on evidence atoms and outputs grades (A/B/C/D) for 5 dimensions:\n")
    narrative.append("1. Protocol/Schema Compliance\n")
    narrative.append("2. Field Validity & Local Dynamics\n")
    narrative.append("3. Physics/Cross-field Consistency\n")
    narrative.append("4. Safety Constraint Satisfaction\n")
    narrative.append("5. Predictive Quality & Reliability\n")
    narrative.append("\nGrades are mapped to scores using a fixed protocol (A=1.0, B=0.75, C=0.5, D=0.0), and the overall score is the arithmetic mean of dimension scores.\n")
    narrative.append("This approach ensures that scoring is driven by LLM judgment based on evidence, not manual weights.\n")
    
    return "\n".join(narrative)


def generate_llm_judge_latex_table(results: Dict[str, Any], output_dir: str):
    """Generate LaTeX table for LLM Judge results"""
    os.makedirs(output_dir, exist_ok=True)
    
    model_profiles = results.get('model_profiles', {})
    
    # Table: Main performance with LLM Judge grades
    table_lines = []
    table_lines.append("\\begin{table*}[!htbp]")
    table_lines.append("\\centering")
    table_lines.append("\\caption{Main Performance Table: LLM Judge Scores (Grade-based Evaluation)}")
    table_lines.append("\\label{tab:llm_judge_performance}")
    table_lines.append("\\resizebox{\\textwidth}{!}{%")
    table_lines.append("\\begin{tabular}{lccccc|c}")
    table_lines.append("\\toprule")
    table_lines.append("Model & Protocol & Field & Physics & Safety & Quality & Total \\\\")
    table_lines.append("& Grade & Grade & Grade & Grade & Grade & Score \\\\")
    table_lines.append("\\midrule")
    
    # Sort models by total score
    model_scores = []
    for model_name, profile in model_profiles.items():
        data_profile = profile.get('data_driven_profile', {})
        total_stats = data_profile.get('score_statistics', {}).get('total', {})
        mean_score = total_stats.get('mean')
        if mean_score:
            # Get average grades from records (would need to read records)
            model_scores.append((model_name, mean_score, profile))
    
    model_scores.sort(key=lambda x: x[1], reverse=True)
    
    # For now, show total scores (grades would need to be extracted from records)
    for model_name, score, profile in model_scores[:20]:
        model_display = model_name.replace('_', '-')[:30]
        table_lines.append(f"{model_display} & - & - & - & - & - & {score:.1f} \\\\")
    
    table_lines.append("\\bottomrule")
    table_lines.append("\\end{tabular}%")
    table_lines.append("}")
    table_lines.append("\\end{table*}")
    
    with open(os.path.join(output_dir, 'table_llm_judge_performance.tex'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(table_lines))
    
    print(f"✅ LLM Judge performance table exported to: {output_dir}/table_llm_judge_performance.tex")


def generate_paper_results_llm_judge(results_dir: str, output_dir: str = "results/paper_results_llm_judge"):
    """Generate complete Results section for paper (LLM Judge version)"""
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 80)
    print("Generating Paper Results Section (LLM Judge)")
    print("=" * 80)
    
    # Load results
    results = load_llm_judge_results(results_dir)
    
    # Generate narrative
    narrative = generate_llm_judge_results_narrative(results)
    narrative_file = os.path.join(output_dir, 'results_narrative_llm_judge.md')
    with open(narrative_file, 'w', encoding='utf-8') as f:
        f.write(narrative)
    print(f"✅ Results narrative exported to: {narrative_file}")
    
    # Generate tables
    generate_llm_judge_latex_table(results, output_dir)
    
    print("\n✅ Paper Results section generation complete!")
    print(f"   Output directory: {output_dir}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        results_dir = sys.argv[1]
    else:
        results_dir = "results/final_official_v1.0.0_llm_judge"
    
    generate_paper_results_llm_judge(results_dir)

