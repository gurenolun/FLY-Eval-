"""
Evaluator Agent

LLM-based evaluator agent that generates checklist, organizes verification,
and outputs adjudication and attribution based on evidence.
"""

from typing import List, Dict, Any, Optional
from ..core.data_structures import EvidenceAtom, Adjudication


class EvaluatorAgent:
    """
    Evaluator Agent
    
    LLM-based agent that:
    1. Generates executable checklist (decomposes "comprehensive judgment" into verifiable items)
    2. Organizes tool verification workflow (offline, full coverage)
    3. Outputs adjudication and attribution based on evidence (must cite evidence IDs)
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize evaluator agent
        
        Args:
            config: Agent configuration with model, temperature, system_prompt, output_schema
        """
        self.config = config
        self.model = config.get('model', 'gpt-4o')
        self.temperature = config.get('temperature', 0)
        self.system_prompt = config.get('system_prompt', '')
        self.output_schema = config.get('output_schema', {})
    
    def generate_checklist(self, task_spec: Dict[str, Any], verifier_capabilities: List[str]) -> List[Dict[str, Any]]:
        """
        Generate executable checklist (rule-based minimal version)
        
        Decomposes "comprehensive judgment" into verifiable items.
        Each item binds to constraint_id/evidence_id.
        
        For minimal version: generate rule-based checklist without LLM.
        
        Args:
            task_spec: Task specification
            verifier_capabilities: List of verifier capabilities
        
        Returns:
            List of checklist items, each with item_id, constraint_id, evidence_id, status
        """
        checklist = []
        
        # Rule-based checklist generation (minimal version)
        # Map verifier capabilities to checklist items
        
        capability_to_constraint = {
            "numeric_validity": "NUMERIC_VALIDITY",
            "range_sanity": "RANGE_SANITY",
            "jump_dynamics": "JUMP_DYNAMICS",
            "physics_constraints": "PHYSICS_CONSTRAINT",
            "safety_constraints": "SAFETY_CONSTRAINT",
            "cross_field_consistency": "CROSS_FIELD_CONSISTENCY"
        }
        
        for i, capability in enumerate(verifier_capabilities, 1):
            constraint_id = capability_to_constraint.get(capability, capability.upper())
            checklist.append({
                "item_id": f"CHECK_{i:03d}",
                "constraint_id": constraint_id,
                "evidence_id": None,  # Will be filled after verification
                "status": "unknown"  # Will be updated based on evidence
            })
        
        return checklist
    
    def organize_verification_workflow(self, checklist: List[Dict[str, Any]], evidence_atoms: List[EvidenceAtom]) -> Dict[str, Any]:
        """
        Organize tool verification workflow
        
        Offline, full coverage verification based on checklist.
        Updates checklist with evidence IDs and status.
        
        Args:
            checklist: Generated checklist
            evidence_atoms: Evidence atoms from verifiers
        
        Returns:
            Updated checklist with evidence IDs and status
        """
        # Map evidence atoms by type
        evidence_by_type = {}
        for atom in evidence_atoms:
            atom_type = atom.type
            if atom_type not in evidence_by_type:
                evidence_by_type[atom_type] = []
            evidence_by_type[atom_type].append(atom)
        
        # Update checklist with evidence IDs and status
        for item in checklist:
            constraint_id = item.get('constraint_id', '')
            
            # Map constraint_id to evidence type
            constraint_to_type = {
                "NUMERIC_VALIDITY": "numeric_validity",
                "RANGE_SANITY": "range_sanity",
                "JUMP_DYNAMICS": "jump_dynamics",
                "PHYSICS_CONSTRAINT": "physics_constraints",
                "SAFETY_CONSTRAINT": "safety_constraints",
                "CROSS_FIELD_CONSISTENCY": "cross_field_consistency"
            }
            
            evidence_type = constraint_to_type.get(constraint_id, constraint_id.lower())
            
            # Find evidence atoms for this constraint
            relevant_atoms = evidence_by_type.get(evidence_type, [])
            
            if relevant_atoms:
                # Get first evidence ID (or all IDs)
                evidence_ids = [atom.id for atom in relevant_atoms]
                item['evidence_id'] = evidence_ids[0] if evidence_ids else None
                item['evidence_ids'] = evidence_ids
                
                # Determine status: pass if all atoms pass, fail if any fails
                all_pass = all(atom.pass_ for atom in relevant_atoms)
                item['status'] = "pass" if all_pass else "fail"
            else:
                item['evidence_id'] = None
                item['evidence_ids'] = []
                item['status'] = "unknown"
        
        return {
            "checklist": checklist,
            "evidence_mapping": {item['item_id']: item['evidence_ids'] for item in checklist}
        }
    
    def adjudicate(self, evidence_atoms: List[EvidenceAtom], checklist: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Output adjudication and attribution based on evidence
        
        Rule-based minimal version: must cite evidence IDs.
        
        Args:
            evidence_atoms: All evidence atoms
            checklist: Generated checklist (with evidence IDs)
        
        Returns:
            Dict with 'adjudication' (eligible/ineligible) and 'attribution' (Top-K failure reasons with evidence IDs)
        """
        # Check for critical failures (gating rules)
        critical_failures = [e for e in evidence_atoms if e.severity.value == 'critical' and not e.pass_]
        
        # Check protocol failures
        protocol_failures = [e for e in evidence_atoms if e.type == 'numeric_validity' and not e.pass_]
        
        # Determine adjudication
        # Ineligible if: critical failures OR protocol failures
        adjudication = Adjudication.ELIGIBLE
        if critical_failures or protocol_failures:
            adjudication = Adjudication.INELIGIBLE
        
        # Generate attribution (Top-K failure reasons with evidence IDs)
        attribution = []
        
        # Collect all failures (critical first, then warning)
        all_failures = []
        all_failures.extend([e for e in evidence_atoms if e.severity.value == 'critical' and not e.pass_])
        all_failures.extend([e for e in evidence_atoms if e.severity.value == 'warning' and not e.pass_])
        
        # Group failures by type and field
        failure_groups = {}
        for failure in all_failures:
            key = f"{failure.type}:{failure.field or 'unknown'}"
            if key not in failure_groups:
                failure_groups[key] = []
            failure_groups[key].append(failure)
        
        # Generate Top-K attribution
        for i, (key, failures) in enumerate(list(failure_groups.items())[:5], 1):  # Top 5
            # Use first failure as representative
            representative = failures[0]
            evidence_ids = [f.id for f in failures]
            
            attribution.append({
                "reason": representative.message or f"{representative.type} violation in {representative.field or 'unknown field'}",
                "evidence_ids": evidence_ids,
                "severity": representative.severity.value,
                "rank": i,
                "count": len(failures)  # Number of violations of this type
            })
        
        return {
            "adjudication": adjudication.value,
            "attribution": attribution
        }
    
    def call_llm(self, prompt: str) -> str:
        """
        Call LLM API
        
        Args:
            prompt: Input prompt
        
        Returns:
            LLM response
        """
        # TODO: Implement LLM API call
        # For now, return empty string
        # Should use OpenAI API or similar with:
        # - model: self.model
        # - temperature: self.temperature
        # - system_prompt: self.system_prompt
        # - structured output: self.output_schema
        
        return ""

