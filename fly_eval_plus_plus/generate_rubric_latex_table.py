"""
Generate LaTeX Table for Rubric Definition

生成5维度×4档的Rubric LaTeX表格，用于论文。
"""

from rubric.rubric_definition import RUBRIC, Dimension, Grade


def generate_rubric_latex_table(output_file: str = "results/paper_results/rubric_table.tex"):
    """
    Generate LaTeX table for rubric definition
    
    Args:
        output_file: Output LaTeX file path
    """
    import os
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Dimension display names
    dim_names = {
        Dimension.PROTOCOL_SCHEMA: "Protocol/Schema Compliance",
        Dimension.FIELD_VALIDITY: "Field Validity \\& Local Dynamics",
        Dimension.PHYSICS_CONSISTENCY: "Physics/Cross-field Consistency",
        Dimension.SAFETY_CONSTRAINT: "Safety Constraint Satisfaction",
        Dimension.PREDICTIVE_QUALITY: "Predictive Quality \\& Reliability"
    }
    
    # Grade display names and scores
    grade_info = {
        Grade.A: ("A (Excellent)", "1.0"),
        Grade.B: ("B (Good)", "0.75"),
        Grade.C: ("C (Acceptable)", "0.5"),
        Grade.D: ("D (Poor/Failed)", "0.0")
    }
    
    lines = []
    lines.append("\\begin{table*}[!htbp]")
    lines.append("\\centering")
    lines.append("\\caption{FLY-EVAL++ Rubric Definition: 5-Dimensional Evaluation with 4-Grade Levels}")
    lines.append("\\label{tab:rubric_definition}")
    lines.append("\\resizebox{\\textwidth}{!}{%")
    lines.append("\\begin{tabular}{|p{3cm}|p{2.5cm}|p{9cm}|}")
    lines.append("\\hline")
    lines.append("\\textbf{Dimension} & \\textbf{Grade (Score)} & \\textbf{Condition Description} \\\\")
    lines.append("\\hline")
    lines.append("\\hline")
    
    # Generate table rows
    for dim in Dimension:
        dim_name = dim_names[dim]
        rubric_dim = RUBRIC[dim]
        
        # Generate rows for each grade
        for i, grade in enumerate([Grade.A, Grade.B, Grade.C, Grade.D]):
            grade_name, score = grade_info[grade]
            condition = rubric_dim[grade]["condition"]
            description = rubric_dim[grade].get("description", "")
            
            # Escape LaTeX special characters
            condition = condition.replace("&", "\\&").replace("%", "\\%").replace("_", "\\_")
            description = description.replace("&", "\\&").replace("%", "\\%").replace("_", "\\_")
            
            # Format: Dimension | Grade (Score) | Condition Description
            if i == 0:
                # First row: include dimension name with multirow
                row = f"\\multirow{{4}}{{*}}{{{dim_name}}} & {grade_name} ({score}) & {condition}"
            else:
                # Subsequent rows: no dimension name
                row = f" & {grade_name} ({score}) & {condition}"
            
            if description:
                row += f" ({description})"
            
            row += " \\\\"
            lines.append(row)
            
            if i < 3:
                lines.append("\\cline{2-3}")
        
        lines.append("\\hline")
    
    lines.append("\\end{tabular}%")
    lines.append("}")
    lines.append("\\end{table*}")
    
    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"✅ Rubric LaTeX table generated: {output_file}")
    return output_file


def generate_protocol_definition_latex(output_file: str = "results/paper_results/protocol_definition.tex"):
    """
    Generate LaTeX document for protocol definition
    
    Args:
        output_file: Output LaTeX file path
    """
    import os
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    lines = []
    lines.append("\\section{Fixed Mapping Protocol}")
    lines.append("")
    lines.append("The FLY-EVAL++ evaluation protocol uses a fixed mapping from grades to scores, eliminating manual weight tuning.")
    lines.append("")
    lines.append("\\subsection{Grade-to-Score Mapping}")
    lines.append("")
    lines.append("Each dimension receives a grade (A, B, C, or D) based on evidence atoms. Grades are mapped to scores using the following fixed protocol:")
    lines.append("")
    lines.append("\\begin{itemize}")
    lines.append("\\item \\textbf{A (Excellent)}: 1.0")
    lines.append("\\item \\textbf{B (Good)}: 0.75")
    lines.append("\\item \\textbf{C (Acceptable)}: 0.5")
    lines.append("\\item \\textbf{D (Poor/Failed)}: 0.0")
    lines.append("\\end{itemize}")
    lines.append("")
    lines.append("\\subsection{Aggregation Method}")
    lines.append("")
    lines.append("The overall score is computed as the arithmetic mean of the five dimension scores:")
    lines.append("")
    lines.append("\\begin{equation}")
    lines.append("\\text{Overall Score} = \\frac{1}{5} \\sum_{i=1}^{5} \\text{Score}_i")
    lines.append("\\end{equation}")
    lines.append("")
    lines.append("We choose arithmetic mean because:")
    lines.append("\\begin{itemize}")
    lines.append("\\item It treats all dimensions equally (no manual weights)")
    lines.append("\\item It is interpretable and transparent")
    lines.append("\\item It avoids arbitrary weight tuning that could be challenged by reviewers")
    lines.append("\\end{itemize}")
    lines.append("")
    lines.append("\\subsection{Monotonicity Constraints}")
    lines.append("")
    lines.append("The protocol enforces monotonicity constraints to ensure consistency:")
    lines.append("")
    lines.append("\\begin{itemize}")
    lines.append("\\item If protocol fails (parsing failed OR critical numeric validity), Protocol dimension cannot be A or B")
    lines.append("\\item If safety has critical violation, Safety dimension cannot be A or B")
    lines.append("\\item If error extremely poor and shows overconfidence, Quality dimension cannot be A")
    lines.append("\\end{itemize}")
    lines.append("")
    lines.append("These constraints are enforced as post-hoc checks. If violated, the LLM Judge output is rejected and a fallback grade (D) is assigned.")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"✅ Protocol definition LaTeX generated: {output_file}")
    return output_file


if __name__ == "__main__":
    import sys
    
    output_dir = "results/paper_results"
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
    
    generate_rubric_latex_table(f"{output_dir}/rubric_table.tex")
    generate_protocol_definition_latex(f"{output_dir}/protocol_definition.tex")

