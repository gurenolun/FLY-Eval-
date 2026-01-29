"""
Export Paper Tables and Figures

Exports main tables/figures from model_profiles.json for paper:
- Availability rate
- Constraint satisfaction profile
- Conditional error (with P95/P99 and exceedance rates)
- Failure mode distribution
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("⚠️  pandas not installed. Install with: pip install pandas")


def load_model_profiles(profiles_file: str) -> Dict[str, Any]:
    """Load model profiles from JSON file"""
    with open(profiles_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def export_main_table(profiles: Dict[str, Any], output_file: str):
    """Export main performance table (requires pandas)"""
    if not HAS_PANDAS:
        print("⚠️  pandas required for table export. Install with: pip install pandas")
        return None
    """
    Export main performance table for paper
    
    Columns: Model, Availability Rate, Constraint Satisfaction, Conditional Error (Mean/P95/P99), Total Score
    """
    rows = []
    
    for model_name, profile in profiles.items():
        data_profile = profile.get('data_driven_profile', {})
        score_stats = data_profile.get('score_statistics', {})
        
        availability = score_stats.get('availability', {})
        constraint = score_stats.get('constraint_satisfaction', {})
        error = score_stats.get('conditional_error', {})
        total = score_stats.get('total', {})
        
        error_dist = data_profile.get('conditional_error_distribution', {})
        tail_risk = data_profile.get('tail_risk', {})
        
        rows.append({
            'Model': model_name,
            'Availability Rate (%)': availability.get('mean'),
            'Constraint Satisfaction (%)': constraint.get('mean'),
            'Conditional Error Mean (%)': error.get('mean'),
            'Conditional Error P95 (%)': error_dist.get('p95'),
            'Conditional Error P99 (%)': error_dist.get('p99'),
            'Total Score': total.get('mean'),
            'Eligibility Rate (%)': data_profile.get('eligibility_rate'),
            'High Risk Rate (%)': tail_risk.get('high_risk_rate')
        })
    
    df = pd.DataFrame(rows)
    df = df.sort_values('Total Score', ascending=False)
    
    # Export to CSV
    df.to_csv(output_file.replace('.tex', '.csv'), index=False)
    
    # Export to LaTeX
    latex_table = df.to_latex(
        index=False,
        float_format="%.2f",
        caption="Main Performance Table: Availability Rate, Constraint Satisfaction, Conditional Error, and Total Score",
        label="tab:main_performance"
    )
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(latex_table)
    
    print(f"✅ Main table exported to: {output_file}")
    return df


def export_constraint_satisfaction_table(profiles: Dict[str, Any], output_file: str):
    """Export constraint satisfaction table (requires pandas)"""
    if not HAS_PANDAS:
        return None
    """
    Export constraint satisfaction profile table
    
    Shows compliance rates by constraint type for each model
    """
    # Collect constraint violation data
    rows = []
    
    for model_name, profile in profiles.items():
        data_profile = profile.get('data_driven_profile', {})
        violations = data_profile.get('constraint_violations', {})
        
        row = {'Model': model_name}
        for constraint_type in ['numeric_validity', 'range_sanity', 'jump_dynamics', 
                               'cross_field_consistency', 'physics_constraint', 'safety_constraint']:
            row[constraint_type] = violations.get(constraint_type, 0)
        
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    # Export to CSV
    df.to_csv(output_file.replace('.tex', '.csv'), index=False)
    
    # Export to LaTeX
    latex_table = df.to_latex(
        index=False,
        caption="Constraint Satisfaction Profile: Violation Counts by Constraint Type",
        label="tab:constraint_satisfaction"
    )
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(latex_table)
    
    print(f"✅ Constraint satisfaction table exported to: {output_file}")
    return df


def export_failure_mode_table(profiles: Dict[str, Any], output_file: str):
    """Export failure mode table (requires pandas)"""
    if not HAS_PANDAS:
        return None
    """
    Export failure mode distribution table
    
    Shows failure modes for ineligible samples
    """
    rows = []
    
    for model_name, profile in profiles.items():
        data_profile = profile.get('data_driven_profile', {})
        failure_modes = data_profile.get('failure_modes', {})
        
        row = {'Model': model_name}
        for mode in ['numeric_validity', 'range_sanity', 'jump_dynamics', 
                     'cross_field_consistency', 'physics_constraint', 'safety_constraint', 'other']:
            row[mode] = failure_modes.get(mode, 0)
        
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    # Export to CSV
    df.to_csv(output_file.replace('.tex', '.csv'), index=False)
    
    # Export to LaTeX
    latex_table = df.to_latex(
        index=False,
        caption="Failure Mode Distribution: Failure Counts by Mode for Ineligible Samples",
        label="tab:failure_modes"
    )
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(latex_table)
    
    print(f"✅ Failure mode table exported to: {output_file}")
    return df


def export_tail_risk_table(profiles: Dict[str, Any], output_file: str):
    """Export tail risk table (requires pandas)"""
    if not HAS_PANDAS:
        return None
    """
    Export tail risk metrics table
    
    Shows P95, P99, and high risk rates
    """
    rows = []
    
    for model_name, profile in profiles.items():
        data_profile = profile.get('data_driven_profile', {})
        tail_risk = data_profile.get('tail_risk', {})
        error_dist = data_profile.get('conditional_error_distribution', {})
        
        rows.append({
            'Model': model_name,
            'P95': tail_risk.get('p95'),
            'P99': tail_risk.get('p99'),
            'High Risk Samples': tail_risk.get('high_risk_samples'),
            'High Risk Rate (%)': tail_risk.get('high_risk_rate'),
            'Error Mean': error_dist.get('mean'),
            'Error Std': error_dist.get('std')
        })
    
    df = pd.DataFrame(rows)
    df = df.sort_values('P95', ascending=False)
    
    # Export to CSV
    df.to_csv(output_file.replace('.tex', '.csv'), index=False)
    
    # Export to LaTeX
    latex_table = df.to_latex(
        index=False,
        float_format="%.2f",
        caption="Tail Risk Metrics: P95, P99, and High Risk Rates",
        label="tab:tail_risk"
    )
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(latex_table)
    
    print(f"✅ Tail risk table exported to: {output_file}")
    return df


def export_all_paper_tables(profiles_file: str, output_dir: str = "results/paper_tables"):
    """
    Export all paper tables from model_profiles.json
    
    Args:
        profiles_file: Path to model_profiles.json
        output_dir: Output directory for tables
    """
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 80)
    print("Exporting Paper Tables from Model Profiles")
    print("=" * 80)
    
    # Load profiles
    profiles = load_model_profiles(profiles_file)
    print(f"✅ Loaded {len(profiles)} model profiles")
    
    # Export tables
    main_table = export_main_table(
        profiles,
        os.path.join(output_dir, "main_performance_table.tex")
    )
    
    constraint_table = export_constraint_satisfaction_table(
        profiles,
        os.path.join(output_dir, "constraint_satisfaction_table.tex")
    )
    
    failure_table = export_failure_mode_table(
        profiles,
        os.path.join(output_dir, "failure_mode_table.tex")
    )
    
    tail_risk_table = export_tail_risk_table(
        profiles,
        os.path.join(output_dir, "tail_risk_table.tex")
    )
    
    print("\n✅ All paper tables exported!")
    print(f"   Output directory: {output_dir}")
    
    return {
        'main_table': main_table,
        'constraint_table': constraint_table,
        'failure_table': failure_table,
        'tail_risk_table': tail_risk_table
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        profiles_file = sys.argv[1]
    else:
        profiles_file = "results/final_official_v1.0.0/model_profiles.json"
    
    export_all_paper_tables(profiles_file)

