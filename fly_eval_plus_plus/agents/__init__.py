"""
Evaluator Agent Layer

LLM-based evaluator agent that:
1. Generates executable checklist
2. Organizes tool verification workflow
3. Outputs adjudication and attribution based on evidence
"""

from .evaluator_agent import EvaluatorAgent

__all__ = ['EvaluatorAgent']

