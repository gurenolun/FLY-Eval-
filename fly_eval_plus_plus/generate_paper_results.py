"""
Generate Paper Results Section

Generates narrative and results for paper Results section from evaluation outputs.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any


def load_evaluation_results(results_dir: str) -> Dict[str, Any]:
    """Load all evaluation results"""
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


def generate_results_narrative(results: Dict[str, Any]) -> str:
    """
    Generate narrative text for Results section
    
    Returns:
        Markdown formatted narrative
    """
    task_summaries = results.get('task_summaries', {})
    model_profiles = results.get('model_profiles', {})
    version_info = results.get('version_info', {})
    
    narrative = []
    narrative.append("# Results Section Narrative\n")
    narrative.append("**Generated from FLY-EVAL++ v1.0.0 Evaluation Results**\n")
    
    # Version information
    if version_info:
        vi = version_info.get('version_info', {})
        narrative.append("## Reproducibility Information\n")
        narrative.append(f"- **Config Hash**: `{vi.get('config_hash')}`")
        narrative.append(f"- **Schema Version**: `{vi.get('schema_version')}`")
        narrative.append(f"- **Constraint Lib Version**: `{vi.get('constraint_lib_version')}`")
        narrative.append(f"- **Evaluator Version**: `{vi.get('evaluator_version')}`")
        narrative.append(f"- **Evaluation Timestamp**: `{version_info.get('evaluation_timestamp')}`\n")
    
    # Task-level results
    narrative.append("## Task-Level Results\n")
    for task_id, summary in task_summaries.items():
        narrative.append(f"### {task_id} Task\n")
        narrative.append(f"We evaluated {summary.get('total_samples')} samples for the {task_id} task. ")
        narrative.append(f"Of these, {summary.get('eligible_samples')} ({summary.get('eligible_samples')/summary.get('total_samples')*100:.1f}%) were adjudicated as eligible after gating rules. ")
        narrative.append(f"The overall availability rate (field completeness) was {summary.get('availability_rate'):.2f}%.\n")
        
        # Compliance rates
        compliance = summary.get('compliance_rate', {})
        narrative.append("**Constraint Compliance Rates**:\n")
        for constraint_type, rate in sorted(compliance.items(), key=lambda x: x[1], reverse=True):
            narrative.append(f"- {constraint_type}: {rate:.2f}%\n")
        
        # Conditional error
        error = summary.get('conditional_error', {})
        if error.get('count', 0) > 0:
            narrative.append(f"\n**Conditional Error Statistics** (eligible samples only):\n")
            narrative.append(f"- Mean: {error.get('mean'):.2f}")
            narrative.append(f"- Median: {error.get('median'):.2f}")
            narrative.append(f"- Std: {error.get('std'):.2f}")
            narrative.append(f"- P95: {error.get('p95'):.2f}")
            narrative.append(f"- P99: {error.get('p99'):.2f}\n")
        
        # Tail risk
        tail = summary.get('tail_risk', {})
        if tail:
            narrative.append("**Tail Risk Metrics**:\n")
            narrative.append(f"- P95: {tail.get('p95'):.2f}")
            narrative.append(f"- P99: {tail.get('p99'):.2f}")
            exceedance = tail.get('exceedance_rates', {})
            if exceedance:
                narrative.append(f"- Exceedance rates: {exceedance}\n")
        
        # Failure modes
        failure_modes = summary.get('failure_modes', {})
        if failure_modes:
            narrative.append("**Failure Mode Distribution**:\n")
            for mode, count in sorted(failure_modes.items(), key=lambda x: x[1], reverse=True):
                narrative.append(f"- {mode}: {count} failures\n")
    
    # Model-level results
    narrative.append("\n## Model-Level Results\n")
    narrative.append(f"We evaluated {len(model_profiles)} models across all tasks.\n")
    
    # Top performers
    model_scores = []
    for model_name, profile in model_profiles.items():
        data_profile = profile.get('data_driven_profile', {})
        total_stats = data_profile.get('score_statistics', {}).get('total', {})
        mean_score = total_stats.get('mean')
        if mean_score:
            model_scores.append((model_name, mean_score))
    
    model_scores.sort(key=lambda x: x[1], reverse=True)
    
    narrative.append("### Top Performers\n")
    narrative.append("Models ranked by total score (availability × 0.2 + constraint satisfaction × 0.3 + conditional error × 0.5):\n")
    for i, (model_name, score) in enumerate(model_scores[:10], 1):
        narrative.append(f"{i}. **{model_name}**: {score:.2f}\n")
    
    # Performance distribution
    narrative.append("\n### Performance Distribution\n")
    if model_scores:
        scores = [s for _, s in model_scores]
        import statistics
        narrative.append(f"- Mean total score: {statistics.mean(scores):.2f}")
        narrative.append(f"- Median total score: {statistics.median(scores):.2f}")
        narrative.append(f"- Std: {statistics.stdev(scores) if len(scores) > 1 else 0:.2f}")
        narrative.append(f"- Min: {min(scores):.2f}")
        narrative.append(f"- Max: {max(scores):.2f}\n")
    
    # Constraint violation analysis
    narrative.append("\n### Constraint Violation Analysis\n")
    all_violations = {}
    for model_name, profile in model_profiles.items():
        data_profile = profile.get('data_driven_profile', {})
        violations = data_profile.get('constraint_violations', {})
        for constraint_type, count in violations.items():
            all_violations[constraint_type] = all_violations.get(constraint_type, 0) + count
    
    narrative.append("Total violations across all models:\n")
    for constraint_type, count in sorted(all_violations.items(), key=lambda x: x[1], reverse=True):
        narrative.append(f"- {constraint_type}: {count} violations\n")
    
    # Tail risk analysis
    narrative.append("\n### Tail Risk Analysis\n")
    tail_risks = []
    for model_name, profile in model_profiles.items():
        data_profile = profile.get('data_driven_profile', {})
        tail_risk = data_profile.get('tail_risk', {})
        if tail_risk.get('p95'):
            tail_risks.append((model_name, tail_risk))
    
    if tail_risks:
        narrative.append("Models with highest tail risk (lowest P95):\n")
        tail_risks.sort(key=lambda x: x[1].get('p95', 100))
        for i, (model_name, tr) in enumerate(tail_risks[:5], 1):
            narrative.append(f"{i}. **{model_name}**: P95={tr.get('p95'):.2f}, High Risk Rate={tr.get('high_risk_rate', 0):.2f}%\n")
    
    return "\n".join(narrative)


def generate_results_tables(results: Dict[str, Any], output_dir: str):
    """
    Generate LaTeX tables for Results section
    
    Args:
        results: Evaluation results dictionary
        output_dir: Output directory for tables
    """
    os.makedirs(output_dir, exist_ok=True)
    
    model_profiles = results.get('model_profiles', {})
    task_summaries = results.get('task_summaries', {})
    
    # Table 1: Main performance table
    table1_lines = []
    table1_lines.append("\\begin{table*}[!htbp]")
    table1_lines.append("\\centering")
    table1_lines.append("\\caption{Main Performance Table: Availability Rate, Constraint Satisfaction, Conditional Error, and Total Score}")
    table1_lines.append("\\label{tab:main_performance}")
    table1_lines.append("\\resizebox{\\textwidth}{!}{%")
    table1_lines.append("\\begin{tabular}{lccccccc}")
    table1_lines.append("\\toprule")
    table1_lines.append("Model & Avail. & Constraint & Error & Error & Error & Total & Elig. \\\\")
    table1_lines.append("& Rate & Satisf. & Mean & P95 & P99 & Score & Rate \\\\")
    table1_lines.append("\\midrule")
    
    # Sort models by total score
    model_scores = []
    for model_name, profile in model_profiles.items():
        data_profile = profile.get('data_driven_profile', {})
        total_stats = data_profile.get('score_statistics', {}).get('total', {})
        mean_score = total_stats.get('mean')
        if mean_score:
            model_scores.append((model_name, profile, mean_score))
    
    model_scores.sort(key=lambda x: x[2], reverse=True)
    
    for model_name, profile, score in model_scores:
        data_profile = profile.get('data_driven_profile', {})
        avail_stats = data_profile.get('score_statistics', {}).get('availability', {})
        constraint_stats = data_profile.get('score_statistics', {}).get('constraint_satisfaction', {})
        error_stats = data_profile.get('score_statistics', {}).get('conditional_error', {})
        error_dist = data_profile.get('conditional_error_distribution', {})
        
        # Format model name (simplified)
        model_display = model_name.replace('_', '-')[:30]
        
        avail_mean = avail_stats.get('mean', 0) or 0
        constraint_mean = constraint_stats.get('mean', 0) or 0
        error_mean = error_stats.get('mean', 0) or 0
        error_p95 = error_dist.get('p95', 0) or 0
        error_p99 = error_dist.get('p99', 0) or 0
        elig_rate = data_profile.get('eligibility_rate', 0) or 0
        
        table1_lines.append(f"{model_display} & {avail_mean:.1f} & {constraint_mean:.1f} & {error_mean:.1f} & {error_p95:.1f} & {error_p99:.1f} & {score:.1f} & {elig_rate:.1f} \\\\")
    
    table1_lines.append("\\bottomrule")
    table1_lines.append("\\end{tabular}%")
    table1_lines.append("}")
    table1_lines.append("\\end{table*}")
    
    with open(os.path.join(output_dir, 'table_main_performance.tex'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(table1_lines))
    
    print(f"✅ Main performance table exported to: {output_dir}/table_main_performance.tex")
    
    # Table 2: Constraint satisfaction by type
    table2_lines = []
    table2_lines.append("\\begin{table}[!htbp]")
    table2_lines.append("\\centering")
    table2_lines.append("\\caption{Constraint Satisfaction Profile: Violation Counts by Constraint Type}")
    table2_lines.append("\\label{tab:constraint_satisfaction}")
    table2_lines.append("\\begin{tabular}{lcccccc}")
    table2_lines.append("\\toprule")
    table2_lines.append("Model & Numeric & Range & Jump & Cross-Field & Physics & Safety \\\\")
    table2_lines.append("\\midrule")
    
    constraint_types = ['numeric_validity', 'range_sanity', 'jump_dynamics', 
                       'cross_field_consistency', 'physics_constraint', 'safety_constraint']
    
    for model_name, profile, _ in model_scores[:15]:  # Top 15 models
        data_profile = profile.get('data_driven_profile', {})
        violations = data_profile.get('constraint_violations', {})
        
        model_display = model_name.replace('_', '-')[:25]
        row = [model_display]
        for ct in constraint_types:
            row.append(str(violations.get(ct, 0)))
        table2_lines.append(" & ".join(row) + " \\\\")
    
    table2_lines.append("\\bottomrule")
    table2_lines.append("\\end{tabular}")
    table2_lines.append("\\end{table}")
    
    with open(os.path.join(output_dir, 'table_constraint_satisfaction.tex'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(table2_lines))
    
    print(f"✅ Constraint satisfaction table exported to: {output_dir}/table_constraint_satisfaction.tex")
    
    # Table 3: Tail risk
    table3_lines = []
    table3_lines.append("\\begin{table}[!htbp]")
    table3_lines.append("\\centering")
    table3_lines.append("\\caption{Tail Risk Metrics: P95, P99, and High Risk Rates}")
    table3_lines.append("\\label{tab:tail_risk}")
    table3_lines.append("\\begin{tabular}{lccccc}")
    table3_lines.append("\\toprule")
    table3_lines.append("Model & P95 & P99 & High Risk & High Risk & Error \\\\")
    table3_lines.append("& & & Samples & Rate (\\%) & Mean \\\\")
    table3_lines.append("\\midrule")
    
    tail_risks = []
    for model_name, profile, _ in model_scores:
        data_profile = profile.get('data_driven_profile', {})
        tail_risk = data_profile.get('tail_risk', {})
        error_dist = data_profile.get('conditional_error_distribution', {})
        if tail_risk.get('p95'):
            tail_risks.append((model_name, profile, tail_risk, error_dist))
    
    tail_risks.sort(key=lambda x: x[2].get('p95', 100))
    
    for model_name, profile, tail_risk, error_dist in tail_risks[:15]:
        model_display = model_name.replace('_', '-')[:25]
        p95 = tail_risk.get('p95', 0) or 0
        p99 = tail_risk.get('p99', 0) or 0
        high_risk_samples = tail_risk.get('high_risk_samples', 0) or 0
        high_risk_rate = tail_risk.get('high_risk_rate', 0) or 0
        error_mean = error_dist.get('mean', 0) or 0
        
        table3_lines.append(f"{model_display} & {p95:.1f} & {p99:.1f} & {high_risk_samples} & {high_risk_rate:.1f} & {error_mean:.1f} \\\\")
    
    table3_lines.append("\\bottomrule")
    table3_lines.append("\\end{tabular}")
    table3_lines.append("\\end{table}")
    
    with open(os.path.join(output_dir, 'table_tail_risk.tex'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(table3_lines))
    
    print(f"✅ Tail risk table exported to: {output_dir}/table_tail_risk.tex")


def generate_paper_results_section(results_dir: str, output_dir: str = "results/paper_results"):
    """
    Generate complete Results section for paper
    
    Args:
        results_dir: Directory containing evaluation results
        output_dir: Output directory for paper materials
    """
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 80)
    print("Generating Paper Results Section")
    print("=" * 80)
    
    # Load results
    results = load_evaluation_results(results_dir)
    
    # Generate narrative
    narrative = generate_results_narrative(results)
    narrative_file = os.path.join(output_dir, 'results_narrative.md')
    with open(narrative_file, 'w', encoding='utf-8') as f:
        f.write(narrative)
    print(f"✅ Results narrative exported to: {narrative_file}")
    
    # Generate tables
    generate_results_tables(results, output_dir)
    
    # Generate summary statistics
    summary_file = os.path.join(output_dir, 'summary_statistics.json')
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            'model_count': len(results.get('model_profiles', {})),
            'task_count': len(results.get('task_summaries', {})),
            'version_info': results.get('version_info', {})
        }, f, indent=2)
    print(f"✅ Summary statistics exported to: {summary_file}")
    
    print("\n✅ Paper Results section generation complete!")
    print(f"   Output directory: {output_dir}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        results_dir = sys.argv[1]
    else:
        results_dir = "results/final_official_v1.0.0_S1"
    
    generate_paper_results_section(results_dir)

