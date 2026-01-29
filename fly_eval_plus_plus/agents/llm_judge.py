"""
LLM Judge for FLY-EVAL++

LLM-based evaluator that outputs grades based on rubric and evidence.
Implements evidence-only, monotonicity checks, and deterministic output.
"""

import json
import hashlib
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from ..core.data_structures import EvidenceAtom
from ..rubric.rubric_definition import (
    RUBRIC, GRADE_SCORE_MAP, aggregate_grade_scores,
    MONOTONICITY_CHECKS, get_rubric_text, get_evidence_atom_fields, get_verifier_families,
    Grade, Dimension
)


@dataclass
class JudgeOutput:
    """LLM Judge output structure"""
    grade_vector: Dict[str, str]  # dimension -> grade (A/B/C/D)
    overall_grade: str  # Overall grade (A/B/C/D)
    critical_findings: List[Dict[str, Any]]  # Top-K critical violations with evidence_id
    checklist: List[Dict[str, Any]]  # Key verification items with evidence_id
    evidence_citations: List[str]  # All evidence IDs cited
    reasoning: Dict[str, str]  # Structured reasoning: dimension -> brief explanation with evidence citations
    judge_metadata: Dict[str, Any]  # Model version, prompt hash, etc.


class LLMJudge:
    """
    LLM Judge for FLY-EVAL++
    
    Takes evidence atoms and outputs grades based on rubric.
    Implements evidence-only, monotonicity checks, and deterministic output.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LLM Judge
        
        Args:
            config: Judge configuration with model, temperature, API settings
        """
        self.config = config
        self.model = config.get('model', 'gpt-4o')
        self.temperature = config.get('temperature', 0)  # Must be 0 for determinism
        self.api_key = config.get('api_key')
        self.max_retries = config.get('max_retries', 3)
        
        # Cache for deterministic output
        self._cache: Dict[str, JudgeOutput] = {}
        
        # Load rubric
        self.rubric_text = get_rubric_text()
        self.verifier_families = get_verifier_families()
        self.evidence_fields = get_evidence_atom_fields()
    
    def _build_evidence_summary(self, evidence_atoms: List[EvidenceAtom], 
                               protocol_result: Dict[str, Any],
                               conditional_error: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Build evidence summary for LLM (evidence-only, no raw response)
        
        Args:
            evidence_atoms: All evidence atoms
            protocol_result: Protocol result (parsing, field completeness)
            conditional_error: Conditional error scores if available
        
        Returns:
            Evidence summary dictionary
        """
        # Group evidence by type
        evidence_by_type = {}
        for atom in evidence_atoms:
            atom_type = atom.type
            if atom_type not in evidence_by_type:
                evidence_by_type[atom_type] = {
                    "atoms": [],
                    "critical_count": 0,
                    "warning_count": 0,
                    "info_count": 0,
                    "pass_count": 0,
                    "fail_count": 0
                }
            
            evidence_by_type[atom_type]["atoms"].append({
                "id": atom.id,
                "field": atom.field,
                "pass": atom.pass_,
                "severity": atom.severity.value,
                "message": atom.message,
                "meta": atom.meta
            })
            
            if atom.severity.value == 'critical':
                evidence_by_type[atom_type]["critical_count"] += 1
            elif atom.severity.value == 'warning':
                evidence_by_type[atom_type]["warning_count"] += 1
            else:
                evidence_by_type[atom_type]["info_count"] += 1
            
            if atom.pass_:
                evidence_by_type[atom_type]["pass_count"] += 1
            else:
                evidence_by_type[atom_type]["fail_count"] += 1
        
        # Build summary
        summary = {
            "parsing": {
                "success": protocol_result.get("parsing", {}).get("success", False),
                "error": protocol_result.get("parsing", {}).get("error")
            },
            "field_completeness": {
                "rate": protocol_result.get("field_completeness", {}).get("completeness_rate", 0.0),
                "missing_fields": protocol_result.get("field_completeness", {}).get("missing_fields", [])
            },
            "evidence_by_type": evidence_by_type
        }
        
        # Add conditional error if available
        if conditional_error:
            summary["conditional_error"] = conditional_error
        
        return summary
    
    def _build_prompt(self, task_spec: Dict[str, Any], evidence_summary: Dict[str, Any]) -> str:
        """
        Build prompt for LLM Judge (evidence-only, no raw response)
        
        Args:
            task_spec: Task specification
            evidence_summary: Evidence summary
        
        Returns:
            Prompt string
        """
        prompt_parts = []
        
        # System instruction
        prompt_parts.append("You are an evaluator agent for flight prediction models.")
        prompt_parts.append("Your task is to evaluate model outputs based on evidence atoms and a rubric.")
        prompt_parts.append("You must ONLY use the provided evidence atoms - do not make subjective judgments.")
        prompt_parts.append("")
        
        # Rubric
        prompt_parts.append("## Evaluation Rubric")
        prompt_parts.append(self.rubric_text)
        prompt_parts.append("")
        
        # Task specification
        prompt_parts.append("## Task Specification")
        prompt_parts.append(json.dumps(task_spec, indent=2))
        prompt_parts.append("")
        
        # Evidence summary
        prompt_parts.append("## Evidence Summary")
        prompt_parts.append("The following evidence atoms were collected by automated verifiers:")
        prompt_parts.append(json.dumps(evidence_summary, indent=2))
        prompt_parts.append("")
        
        # Available verifiers
        prompt_parts.append("## Available Verifiers")
        for verifier in self.verifier_families:
            prompt_parts.append(f"- {verifier}")
        prompt_parts.append("")
        
        # Output schema
        prompt_parts.append("## Required Output Format")
        prompt_parts.append("You must output a JSON object with the following structure:")
        prompt_parts.append(json.dumps({
            "grade_vector": {
                "protocol_schema_compliance": "A|B|C|D",
                "field_validity_local_dynamics": "A|B|C|D",
                "physics_cross_field_consistency": "A|B|C|D",
                "safety_constraint_satisfaction": "A|B|C|D",
                "predictive_quality_reliability": "A|B|C|D"
            },
            "overall_grade": "A|B|C|D",
            "critical_findings": [
                {
                    "reason": "Description of critical violation",
                    "evidence_ids": ["EVID_001", "EVID_002"],
                    "dimension": "protocol_schema_compliance|field_validity_local_dynamics|...",
                    "severity": "critical"
                }
            ],
            "checklist": [
                {
                    "item_id": "CHECK_001",
                    "constraint_id": "NUMERIC_VALIDITY|RANGE_SANITY|...",
                    "evidence_ids": ["EVID_001"],
                    "status": "pass|fail",
                    "description": "Brief description"
                }
            ],
            "reasoning": {
                "protocol_schema_compliance": "Brief explanation with evidence citations",
                "field_validity_local_dynamics": "Brief explanation with evidence citations",
                "physics_cross_field_consistency": "Brief explanation with evidence citations",
                "safety_constraint_satisfaction": "Brief explanation with evidence citations",
                "predictive_quality_reliability": "Brief explanation with evidence citations"
            }
        }, indent=2))
        prompt_parts.append("")
        
        # Constraints
        prompt_parts.append("## Constraints")
        prompt_parts.append("1. You MUST cite evidence IDs for all findings. Do not make claims without evidence.")
        prompt_parts.append("2. Follow monotonicity rules:")
        prompt_parts.append("   - If protocol fails (parsing failed OR critical numeric validity), Protocol dimension cannot be A or B")
        prompt_parts.append("   - If safety has critical violation, Safety dimension cannot be A or B")
        prompt_parts.append("   - If error extremely poor and shows overconfidence, Quality dimension cannot be A")
        prompt_parts.append("3. Overall grade should be the mean of dimension grades (rounded to nearest).")
        prompt_parts.append("")
        
        prompt_parts.append("Now evaluate the evidence and output your judgment in the required JSON format.")
        
        return "\n".join(prompt_parts)
    
    def _call_llm_api(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        """
        Call LLM API
        
        Args:
            prompt: Input prompt
        
        Returns:
            Tuple of (LLM response text, full API request/response metadata)
        """
        try:
            import openai
            
            # Check if API key is set
            if not self.api_key:
                # Try to get from environment
                self.api_key = os.getenv("OPENAI_API_KEY")
            
            if not self.api_key:
                raise ValueError("OpenAI API key not provided")
            
            # Use custom API base (from run_multi_task_tests.py)
            # API_BASE = "https://xiaohumini.site"
            api_base = os.getenv("OPENAI_API_BASE", "https://xiaohumini.site/v1")
            
            # Call OpenAI API with custom base
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=api_base
            )
            
            # Prepare request
            messages = [
                {"role": "system", "content": "You are an evaluator agent for flight prediction models. You must output valid JSON only."},
                {"role": "user", "content": prompt}
            ]
            
            request_params = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,  # Must be 0 for determinism
                "response_format": {"type": "json_object"}  # Force JSON output
            }
            
            # Make API call
            response = client.chat.completions.create(**request_params)
            
            # Extract response content
            response_text = response.choices[0].message.content
            
            # Build full request/response metadata
            api_metadata = {
                "request": {
                    "model": self.model,
                    "messages": messages,
                    "temperature": self.temperature,
                    "api_base": api_base
                },
                "response": {
                    "content": response_text,
                    "model": response.model if hasattr(response, 'model') else self.model,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens if hasattr(response, 'usage') and response.usage else None,
                        "completion_tokens": response.usage.completion_tokens if hasattr(response, 'usage') and response.usage else None,
                        "total_tokens": response.usage.total_tokens if hasattr(response, 'usage') and response.usage else None
                    } if hasattr(response, 'usage') and response.usage else None
                }
            }
            
            return response_text, api_metadata
            
        except ImportError:
            raise ImportError("OpenAI library not installed. Install with: pip install openai")
        except Exception as e:
            raise Exception(f"LLM API call failed: {e}")
    
    def _parse_llm_output(self, llm_response: str) -> Dict[str, Any]:
        """
        Parse LLM output and validate structure
        
        Args:
            llm_response: LLM response string
        
        Returns:
            Parsed output dictionary
        """
        try:
            output = json.loads(llm_response)
            
            # Validate required fields
            required_fields = ["grade_vector", "overall_grade", "critical_findings", "checklist", "reasoning"]
            for field in required_fields:
                if field not in output:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate reasoning structure (should be Dict[str, str] for each dimension)
            if isinstance(output["reasoning"], str):
                # Backward compatibility: convert string to dict
                reasoning_str = output["reasoning"]
                output["reasoning"] = {
                    dim.value: reasoning_str for dim in Dimension
                }
            elif isinstance(output["reasoning"], dict):
                # Ensure all dimensions are present
                for dim in Dimension:
                    if dim.value not in output["reasoning"]:
                        output["reasoning"][dim.value] = "No specific reasoning provided"
            else:
                raise ValueError(f"Invalid reasoning type: {type(output['reasoning'])}")
            
            # Validate grade_vector
            for dim in Dimension:
                if dim.value not in output["grade_vector"]:
                    raise ValueError(f"Missing dimension in grade_vector: {dim.value}")
                if output["grade_vector"][dim.value] not in ["A", "B", "C", "D"]:
                    raise ValueError(f"Invalid grade: {output['grade_vector'][dim.value]}")
            
            # Validate overall_grade
            if output["overall_grade"] not in ["A", "B", "C", "D"]:
                raise ValueError(f"Invalid overall_grade: {output['overall_grade']}")
            
            return output
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON output: {e}")
    
    def _validate_monotonicity(self, evidence_summary: Dict[str, Any], 
                              grade_vector: Dict[str, str]) -> Tuple[bool, List[str]]:
        """
        Validate monotonicity constraints
        
        Args:
            evidence_summary: Evidence summary
            grade_vector: Grade vector from LLM
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        # Check each monotonicity rule
        for rule_name, rule in MONOTONICITY_CHECKS.items():
            # Check protocol dimension
            if "protocol" in rule_name:
                protocol_grade = grade_vector.get(Dimension.PROTOCOL_SCHEMA.value)
                if protocol_grade:
                    if not rule["check"](evidence_summary, Grade(protocol_grade)):
                        errors.append(f"Monotonicity violation: {rule['condition']}")
            
            # Check safety dimension
            elif "safety" in rule_name:
                safety_grade = grade_vector.get(Dimension.SAFETY_CONSTRAINT.value)
                if safety_grade:
                    if not rule["check"](evidence_summary, Grade(safety_grade)):
                        errors.append(f"Monotonicity violation: {rule['condition']}")
            
            # Check quality dimension
            elif "quality" in rule_name or "error" in rule_name:
                quality_grade = grade_vector.get(Dimension.PREDICTIVE_QUALITY.value)
                if quality_grade:
                    if not rule["check"](evidence_summary, Grade(quality_grade)):
                        errors.append(f"Monotonicity violation: {rule['condition']}")
        
        return len(errors) == 0, errors
    
    def _validate_evidence_citations(self, judge_output: Dict[str, Any], 
                                    evidence_atoms: List[EvidenceAtom]) -> Tuple[bool, List[str]]:
        """
        Validate that all cited evidence IDs exist
        
        Args:
            judge_output: LLM judge output
            evidence_atoms: All evidence atoms
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        evidence_ids = {atom.id for atom in evidence_atoms}
        
        # Check critical_findings
        for finding in judge_output.get("critical_findings", []):
            for evid_id in finding.get("evidence_ids", []):
                if evid_id not in evidence_ids:
                    errors.append(f"Cited evidence ID not found: {evid_id}")
        
        # Check checklist
        for item in judge_output.get("checklist", []):
            for evid_id in item.get("evidence_ids", []):
                if evid_id not in evidence_ids:
                    errors.append(f"Cited evidence ID not found: {evid_id}")
        
        return len(errors) == 0, errors
    
    def judge(self, evidence_atoms: List[EvidenceAtom], 
              protocol_result: Dict[str, Any],
              task_spec: Dict[str, Any],
              conditional_error: Optional[Dict[str, float]] = None) -> JudgeOutput:
        """
        Judge sample based on evidence (evidence-only, no raw response)
        
        Args:
            evidence_atoms: All evidence atoms
            protocol_result: Protocol result
            task_spec: Task specification
            conditional_error: Conditional error scores if available
        
        Returns:
            JudgeOutput with grades and citations
        """
        # Build evidence summary
        evidence_summary = self._build_evidence_summary(evidence_atoms, protocol_result, conditional_error)
        
        # Build cache key (deterministic)
        cache_key = self._build_cache_key(evidence_summary, task_spec)
        
        # Check cache
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Build prompt
        prompt = self._build_prompt(task_spec, evidence_summary)
        
        # Call LLM with retries
        llm_response = None
        api_metadata = None
        last_error = None
        for attempt in range(self.max_retries):
            try:
                llm_response, api_metadata = self._call_llm_api(prompt)
                if llm_response:
                    break
            except Exception as e:
                last_error = e
                print(f"  ⚠️  LLM API调用失败 (尝试 {attempt+1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    # Fallback: return lowest grade
                    print(f"  ⚠️  使用fallback judge（LLM调用失败）")
                    fallback_output = self._fallback_judge(evidence_atoms, protocol_result)
                    # Add API metadata to fallback output
                    fallback_output.judge_metadata["api_request_response"] = {
                        "error": str(last_error),
                        "attempts": self.max_retries
                    }
                    return fallback_output
                continue
        
        if not llm_response:
            # Fallback: return lowest grade
            print(f"  ⚠️  使用fallback judge（无LLM响应）")
            if last_error:
                print(f"     最后错误: {last_error}")
            fallback_output = self._fallback_judge(evidence_atoms, protocol_result)
            fallback_output.judge_metadata["api_request_response"] = {
                "error": str(last_error) if last_error else "No response",
                "attempts": self.max_retries
            }
            return fallback_output
        
        # Parse and validate
        try:
            parsed_output = self._parse_llm_output(llm_response)
        except ValueError as e:
            # Fallback: return lowest grade
            fallback_output = self._fallback_judge(evidence_atoms, protocol_result)
            fallback_output.judge_metadata["api_request_response"] = api_metadata or {}
            fallback_output.judge_metadata["api_request_response"]["parse_error"] = str(e)
            return fallback_output
        
        # Validate monotonicity
        is_valid, monotonicity_errors = self._validate_monotonicity(evidence_summary, parsed_output["grade_vector"])
        if not is_valid:
            # Fallback: return lowest grade
            fallback_output = self._fallback_judge(evidence_atoms, protocol_result)
            fallback_output.judge_metadata["api_request_response"] = api_metadata or {}
            fallback_output.judge_metadata["api_request_response"]["monotonicity_errors"] = monotonicity_errors
            return fallback_output
        
        # Validate evidence citations
        is_valid, citation_errors = self._validate_evidence_citations(parsed_output, evidence_atoms)
        if not is_valid:
            # Fallback: return lowest grade
            fallback_output = self._fallback_judge(evidence_atoms, protocol_result)
            fallback_output.judge_metadata["api_request_response"] = api_metadata or {}
            fallback_output.judge_metadata["api_request_response"]["citation_errors"] = citation_errors
            return fallback_output
        
        # Build JudgeOutput
        judge_output = JudgeOutput(
            grade_vector=parsed_output["grade_vector"],
            overall_grade=parsed_output["overall_grade"],
            critical_findings=parsed_output["critical_findings"],
            checklist=parsed_output["checklist"],
            evidence_citations=[evid_id for finding in parsed_output["critical_findings"] 
                              for evid_id in finding.get("evidence_ids", [])],
            reasoning=parsed_output["reasoning"],
            judge_metadata={
                "model": self.model,
                "temperature": self.temperature,
                "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:16],
                "evidence_hash": cache_key,
                "api_request_response": api_metadata  # 完整请求和响应
            }
        )
        
        # Cache result
        self._cache[cache_key] = judge_output
        
        return judge_output
    
    def _build_cache_key(self, evidence_summary: Dict[str, Any], task_spec: Dict[str, Any]) -> str:
        """Build deterministic cache key"""
        key_data = {
            "evidence_summary": evidence_summary,
            "task_spec": task_spec
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()[:32]
    
    def _fallback_judge(self, evidence_atoms: List[EvidenceAtom], 
                       protocol_result: Dict[str, Any]) -> JudgeOutput:
        """
        Fallback judge (lowest grade) when LLM fails or validation fails
        
        Args:
            evidence_atoms: All evidence atoms
            protocol_result: Protocol result
        
        Returns:
            JudgeOutput with lowest grades
        """
        # Assign lowest grade (D) to all dimensions
        grade_vector = {dim.value: Grade.D.value for dim in Dimension}
        
        # Collect critical findings from evidence
        critical_findings = []
        for atom in evidence_atoms:
            if atom.severity.value == 'critical' and not atom.pass_:
                critical_findings.append({
                    "reason": atom.message,
                    "evidence_ids": [atom.id],
                    "dimension": self._map_evidence_type_to_dimension(atom.type),
                    "severity": "critical"
                })
        
        return JudgeOutput(
            grade_vector=grade_vector,
            overall_grade=Grade.D.value,
            critical_findings=critical_findings[:5],  # Top 5
            checklist=[],
            evidence_citations=[atom.id for atom in evidence_atoms if not atom.pass_],
            reasoning={
                dim.value: "Fallback judge: LLM failed or validation failed"
                for dim in Dimension
            },
            judge_metadata={
                "model": "fallback",
                "temperature": 0,
                "prompt_hash": None,
                "evidence_hash": None
            }
        )
    
    def _map_evidence_type_to_dimension(self, evidence_type: str) -> str:
        """Map evidence type to dimension"""
        mapping = {
            "numeric_validity": Dimension.PROTOCOL_SCHEMA.value,
            "range_sanity": Dimension.FIELD_VALIDITY.value,
            "jump_dynamics": Dimension.FIELD_VALIDITY.value,
            "cross_field_consistency": Dimension.PHYSICS_CONSISTENCY.value,
            "physics_constraint": Dimension.PHYSICS_CONSISTENCY.value,
            "safety_constraint": Dimension.SAFETY_CONSTRAINT.value
        }
        return mapping.get(evidence_type, Dimension.PROTOCOL_SCHEMA.value)
    
    def grade_to_score(self, grade: str) -> float:
        """Convert grade to score using fixed mapping"""
        return GRADE_SCORE_MAP.get(Grade(grade), 0.0)
    
    def compute_overall_score(self, judge_output: JudgeOutput) -> float:
        """
        Compute overall score from judge output
        
        Uses fixed protocol: grade -> score -> aggregate
        """
        grade_scores = [self.grade_to_score(grade) for grade in judge_output.grade_vector.values()]
        return aggregate_grade_scores(grade_scores)

