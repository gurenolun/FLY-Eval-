"""
FLY-EVAL++ Main Entry Point

Orchestrates the evaluation workflow:
1. Load configuration
2. Load data (samples, model outputs, model confidence)
3. Build verifier graph
4. Process each sample
5. Generate reports
"""

import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from .core.data_structures import (
    EvalConfig, Sample, ModelOutput, ModelConfidence,
    Record, TaskSummary, ModelProfile
)
from .core.verifier_base import VerifierGraph
from .verifiers import (
    NumericValidityChecker,
    RangeSanityChecker,
    JumpDynamicsChecker,
    PhysicsConstraintChecker,
    SafetyConstraintChecker,
    CrossFieldConsistencyChecker
)
from .agents import EvaluatorAgent
from .fusion import RuleBasedFusion
from .fusion.llm_based_fusion import LLMBasedFusion
from .utils.config_loader import load_field_limits, load_jump_thresholds
from .utils.json_parser import extract_json_from_response, is_api_error
from .data_loader import DataLoader


class FLYEvalPlusPlus:
    """
    FLY-EVAL++ Main Evaluator
    
    Orchestrates the complete evaluation workflow.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize FLY-EVAL++ evaluator
        
        Args:
            config_path: Path to EvalConfig JSON file (optional)
        """
        # Load configuration
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            self.config = EvalConfig(**config_dict)
        else:
            # Use default config
            self.config = self._create_default_config()
        
        # Build verifier graph
        self.verifier_graph = self._build_verifier_graph()
        
        # Initialize evaluator agent
        self.evaluator_agent = EvaluatorAgent(self.config.agent_meta_prompt)
        
        # Initialize fusion (LLM-based or rule-based based on config)
        self.fusion = self._create_fusion(self.config.fusion_protocol)
        
        # Store previous predictions for mutation checking
        self.previous_predictions: Dict[str, Dict[str, Any]] = {}
        
        # Initialize data loader
        self.data_loader = DataLoader()
    
    def _create_default_config(self) -> EvalConfig:
        """Create default configuration"""
        # Load FIELD_LIMITS and JUMP_THRESHOLDS
        field_limits = load_field_limits()
        jump_thresholds = load_jump_thresholds()
        
        # Required fields (19 fields)
        required_fields = [
            "Latitude (WGS84 deg)", "Longitude (WGS84 deg)", "GPS Altitude (WGS84 ft)",
            "GPS Ground Track (deg true)", "Magnetic Heading (deg)", 
            "GPS Velocity E (m/s)", "GPS Velocity N (m/s)", "GPS Velocity U (m/s)",
            "GPS Ground Speed (kt)", "Roll (deg)", "Pitch (deg)", "Turn Rate (deg/sec)",
            "Slip/Skid", "Normal Acceleration (G)", "Lateral Acceleration (G)",
            "Vertical Speed (fpm)", "Indicated Airspeed (kt)", 
            "Baro Altitude (ft)", "Pressure Altitude (ft)"
        ]
        
        # Angle fields
        angle_fields = {
            'GPS Ground Track (deg true)',
            'Magnetic Heading (deg)'
        }
        
        return EvalConfig(
            version="1.0.0",
            methodology="FLY-EVAL++",
            task_specs={
                "S1": {
                    "name": "Next Second Prediction",
                    "output_schema": {},
                    "protocol": "single_value",
                    "reference_source": "next_second_pairs.jsonl"
                },
                "M1": {
                    "name": "Next Second from 3-Window",
                    "output_schema": {},
                    "protocol": "single_value",
                    "reference_source": "flight_3window_samples.jsonl"
                },
                "M3": {
                    "name": "Next 3 Seconds from 3-Window",
                    "output_schema": {},
                    "protocol": "array_value",
                    "reference_source": "flight_3window_samples.jsonl"
                }
            },
            constraint_lib={
                "numeric_validity": {
                    "check_nan": True,
                    "check_inf": True,
                    "check_type": True,
                    "check_missing": True
                },
                "range_sanity": {
                    "field_limits": field_limits,
                    "unit_validation": True
                },
                "jump_dynamics": {
                    "mutation_thresholds": jump_thresholds,
                    "phase_aware": False,
                    "change_rate_limits": {},
                    "angle_fields": angle_fields
                },
                "physics_constraints": {
                    "enabled": True,
                    "rules": {
                        "m3_continuity_thresholds": {}
                    }
                },
                "safety_constraints": {
                    "enabled": True,
                    "extreme_values": {},
                    "emergency_patterns": []
                },
                "cross_field_consistency": {
                    "enabled": True,
                    "rules": {}
                }
            },
            agent_meta_prompt={
                "model": "gpt-4o",
                "temperature": 0,
                "system_prompt": "You are an evaluator agent for flight prediction models...",
                "output_schema": {}
            },
            fusion_protocol={
                "type": "rule_based",  # Can be changed to "llm_based" to use LLM Judge
                "gating_rules": {
                    "protocol_failure": {"max_allowed": 0, "severity": "critical"},
                    "safety_constraint_violation": {"max_allowed": 0, "severity": "critical"},
                    "key_field_missing": {"max_allowed": 0, "severity": "critical"}
                },
                "scoring_rules": {
                    "availability_weight": 0.2,
                    "constraint_satisfaction_weight": 0.3,
                    "conditional_error_weight": 0.5
                },
                # LLM Judge configuration (used when type="llm_based")
                "llm_judge": {
                    "model": "gpt-4o",
                    "temperature": 0,
                    "api_key": os.getenv("OPENAI_API_KEY"),
                    "max_retries": 3
                }
            }
        )
    
    def _build_verifier_graph(self) -> VerifierGraph:
        """Build verifier graph with all verifiers"""
        graph = VerifierGraph()
        
        # Add verifiers in order
        constraint_lib = self.config.constraint_lib
        
        # 1. Numeric Validity Checker (no dependencies)
        numeric_config = constraint_lib.get('numeric_validity', {})
        graph.add_verifier(NumericValidityChecker(numeric_config))
        
        # 2. Range Sanity Checker (depends on numeric validity)
        range_config = constraint_lib.get('range_sanity', {})
        graph.add_verifier(
            RangeSanityChecker(range_config),
            dependencies=["NUMERIC_VALIDITY"]
        )
        
        # 3. Jump Dynamics Checker (depends on numeric validity)
        jump_config = constraint_lib.get('jump_dynamics', {})
        graph.add_verifier(
            JumpDynamicsChecker(jump_config),
            dependencies=["NUMERIC_VALIDITY"]
        )
        
        # 4. Cross-Field Consistency Checker (depends on range sanity)
        consistency_config = constraint_lib.get('cross_field_consistency', {})
        consistency_config['enabled'] = True  # Enable by default
        graph.add_verifier(
            CrossFieldConsistencyChecker(consistency_config),
            dependencies=["RANGE_SANITY"]
        )
        
        # 5. Physics Constraint Checker (depends on range sanity)
        physics_config = constraint_lib.get('physics_constraints', {})
        physics_config['enabled'] = True  # Enable by default
        graph.add_verifier(
            PhysicsConstraintChecker(physics_config),
            dependencies=["RANGE_SANITY"]
        )
        
        # 6. Safety Constraint Checker (depends on range sanity)
        safety_config = constraint_lib.get('safety_constraints', {})
        safety_config['enabled'] = True  # Enable by default
        graph.add_verifier(
            SafetyConstraintChecker(safety_config),
            dependencies=["RANGE_SANITY"]
        )
        
        return graph
    
    def _create_fusion(self, fusion_protocol: Dict[str, Any]):
        """Create fusion instance based on protocol type"""
        fusion_type = fusion_protocol.get('type', 'rule_based')
        if fusion_type == 'llm_based':
            return LLMBasedFusion(fusion_protocol)
        else:
            return RuleBasedFusion(fusion_protocol)
    
    def evaluate_sample(self, sample: Sample, model_output: ModelOutput, model_confidence: Optional[ModelConfidence] = None) -> Record:
        """
        Evaluate a single sample
        
        Args:
            sample: Sample data
            model_output: Model output
            model_confidence: Model-level confidence (optional)
        
        Returns:
            Record with all evaluation results
        """
        # 1. Parse JSON from response
        json_data = extract_json_from_response(model_output.raw_response_text)
        
        # Check for API errors
        if is_api_error(model_output.raw_response_text):
            # Return record with API error
            return Record(
                sample_id=sample.sample_id,
                model_name=model_output.model_name,
                task_id=sample.task_id,
                protocol_result={
                    "parsing": {
                        "success": False,
                        "error": "API error",
                        "evidence_id": None
                    }
                },
                evidence_pack={"atoms": []},
                agent_output={},
                optional_scores={},
                trace={"config_version": self.config.version}
            )
        
        # 2. Build context for verifiers
        context = {
            "json_data": json_data,
            "task_type": sample.task_id,
            "required_fields": self._get_required_fields(sample.task_id),
            "previous_predictions": self.previous_predictions,
            "sample": sample,
            "model_output": model_output
        }
        
        # 3. Run verifier graph (full evidence collection)
        evidence_atoms = self.verifier_graph.execute(sample, model_output, context)
        
        # 4. Agent generates checklist and adjudication
        task_spec = self.config.task_specs.get(sample.task_id, {})
        verifier_capabilities = []
        for verifier in self.verifier_graph.verifiers:
            verifier_capabilities.extend(verifier.get_capabilities())
        
        checklist = self.evaluator_agent.generate_checklist(task_spec, verifier_capabilities)
        
        # Organize workflow: update checklist with evidence IDs
        workflow_result = self.evaluator_agent.organize_verification_workflow(checklist, evidence_atoms)
        updated_checklist = workflow_result.get('checklist', checklist)
        
        # Adjudicate based on evidence
        adjudication_result = self.evaluator_agent.adjudicate(evidence_atoms, updated_checklist)
        
        # 5. Build protocol result (before fusion scoring)
        protocol_result = {
            "parsing": {
                "success": json_data is not None,
                "error": None if json_data else "JSON parsing failed",
                "evidence_id": None
            },
            "field_completeness": {
                "missing_fields": self._get_missing_fields(json_data, context["required_fields"]),
                "completeness_rate": self._calculate_completeness(json_data, context["required_fields"]),
                "evidence_id": None
            },
            "type_validation": {
                "invalid_fields": [],
                "evidence_id": None
            }
        }
        
        # 6. Optional: Calculate scores using fusion
        # Apply gating first
        passed_gating, gating_reasons = self.fusion.gate(evidence_atoms)
        
        # Build record for fusion
        record = Record(
            sample_id=sample.sample_id,
            model_name=model_output.model_name,
            task_id=sample.task_id,
            evidence_pack={"atoms": evidence_atoms},
            protocol_result=protocol_result
        )
        
        # Add task spec to context for LLM Judge
        task_spec = self.config.task_specs.get(sample.task_id, {})
        context['task_spec'] = task_spec
        
        # Calculate scores (LLM Judge should work even if gating fails)
        # For LLM-based fusion, we always call calculate_scores to get LLM judgment
        # For rule-based fusion aligned, we also always calculate scores to get dimension scores
        fusion_type = self.config.fusion_protocol.get('type', 'rule_based')
        
        # Check if using RuleBasedFusionAligned (which needs dimension scores even if gating fails)
        from .fusion.rule_based_fusion_aligned import RuleBasedFusionAligned
        is_aligned_fusion = isinstance(self.fusion, RuleBasedFusionAligned)
        
        if fusion_type == 'llm_based' or passed_gating or is_aligned_fusion:
            optional_scores = self.fusion.calculate_scores(
                record,
                sample=sample,
                model_output=model_output,
                context=context
            )
            # Add gating info even if passed
            if not passed_gating:
                optional_scores["gating_failed"] = True
                optional_scores["gating_reasons"] = gating_reasons
        else:
            # If failed gating and rule-based (not aligned), set scores to None or 0
            optional_scores = {
                "availability_score": None,
                "constraint_satisfaction_score": None,
                "conditional_error_score": None,
                "total_score": None,
                "gating_failed": True,
                "gating_reasons": gating_reasons
            }
        
        # 7. Update previous predictions
        if model_output.model_name not in self.previous_predictions:
            self.previous_predictions[model_output.model_name] = {}
        if json_data:
            for field in context["required_fields"]:
                if field in json_data:
                    self.previous_predictions[model_output.model_name][field] = json_data[field]
        
        # 8. Build record with complete trace
        import hashlib
        import json
        from datetime import datetime
        
        # Calculate config hash
        config_str = json.dumps({
            "version": self.config.version,
            "methodology": self.config.methodology,
            "task_specs": self.config.task_specs,
            "constraint_lib_keys": list(self.config.constraint_lib.keys())
        }, sort_keys=True)
        config_hash = hashlib.sha256(config_str.encode()).hexdigest()[:16]
        
        # Calculate constraint_lib version (hash of field_limits and jump_thresholds)
        from .utils.config_loader import load_field_limits, load_jump_thresholds
        field_limits = load_field_limits()
        jump_thresholds = load_jump_thresholds()
        constraint_lib_str = json.dumps({
            "field_limits_keys": list(field_limits.keys()),
            "jump_thresholds_keys": list(jump_thresholds.keys())
        }, sort_keys=True)
        constraint_lib_hash = hashlib.sha256(constraint_lib_str.encode()).hexdigest()[:16]
        
        # Schema version (based on required fields)
        schema_str = json.dumps({
            "required_fields": context.get("required_fields", []),
            "task_type": sample.task_id
        }, sort_keys=True)
        schema_hash = hashlib.sha256(schema_str.encode()).hexdigest()[:16]
        
        # Build complete trace
        trace = {
            "config_version": self.config.version,
            "config_hash": config_hash,
            "evaluator_version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "schema_version": schema_hash,
            "constraint_lib_version": constraint_lib_hash,
            "reproducibility_info": {
                "model": self.evaluator_agent.model,
                "temperature": self.evaluator_agent.temperature,
                "seed": None,
                "verifier_count": len(self.verifier_graph.verifiers),
                "verifier_ids": [v.verifier_id for v in self.verifier_graph.verifiers]
            }
        }
        
        # 8. Build record
        record = Record(
            sample_id=sample.sample_id,
            model_name=model_output.model_name,
            task_id=sample.task_id,
            protocol_result=protocol_result,
            evidence_pack={"atoms": evidence_atoms},
            agent_output={
                "checklist": updated_checklist,
                "adjudication": adjudication_result["adjudication"],
                "attribution": adjudication_result["attribution"]
            },
            optional_scores=optional_scores,
            trace=trace
        )
        
        return record
    
    def _get_required_fields(self, task_id: str) -> List[str]:
        """Get required fields for task"""
        # All tasks use the same 19 fields
        return [
            "Latitude (WGS84 deg)", "Longitude (WGS84 deg)", "GPS Altitude (WGS84 ft)",
            "GPS Ground Track (deg true)", "Magnetic Heading (deg)", 
            "GPS Velocity E (m/s)", "GPS Velocity N (m/s)", "GPS Velocity U (m/s)",
            "GPS Ground Speed (kt)", "Roll (deg)", "Pitch (deg)", "Turn Rate (deg/sec)",
            "Slip/Skid", "Normal Acceleration (G)", "Lateral Acceleration (G)",
            "Vertical Speed (fpm)", "Indicated Airspeed (kt)", 
            "Baro Altitude (ft)", "Pressure Altitude (ft)"
        ]
    
    def _get_missing_fields(self, json_data: Dict[str, Any], required_fields: List[str]) -> List[str]:
        """Get missing fields"""
        if json_data is None:
            return required_fields
        return [f for f in required_fields if f not in json_data]
    
    def _calculate_completeness(self, json_data: Dict[str, Any], required_fields: List[str]) -> float:
        """Calculate field completeness rate"""
        if json_data is None:
            return 0.0
        provided = sum(1 for f in required_fields if f in json_data)
        return (provided / len(required_fields)) * 100.0
    
    def evaluate_all_samples(self, samples: List[Sample], model_outputs: List[ModelOutput], 
                           model_confidence: Optional[ModelConfidence] = None) -> List[Record]:
        """
        Evaluate all samples
        
        Args:
            samples: List of samples
            model_outputs: List of model outputs (must match samples)
            model_confidence: Model-level confidence (optional)
        
        Returns:
            List of Records
        """
        records = []
        
        for sample, model_output in zip(samples, model_outputs):
            record = self.evaluate_sample(sample, model_output, model_confidence)
            records.append(record)
        
        return records
    
    def generate_task_summary(self, records: List[Record], task_id: str) -> TaskSummary:
        """
        Generate task-level summary
        
        Aggregates:
        - Compliance rates (by constraint type)
        - Availability rate
        - Constraint satisfaction profile
        - Conditional error statistics (for eligible samples)
        - Tail risk (P95/P99/超阈率)
        - Failure mode distribution
        
        Args:
            records: List of records for this task
            task_id: Task ID (S1/M1/M3)
        
        Returns:
            TaskSummary
        """
        import numpy as np
        from collections import defaultdict
        
        total_samples = len(records)
        if total_samples == 0:
            return TaskSummary(
                task_id=task_id,
                total_samples=0,
                eligible_samples=0,
                ineligible_samples=0
            )
        
        # 1. Eligibility statistics
        eligible_samples = sum(1 for r in records if r.agent_output.get('adjudication') == 'eligible')
        ineligible_samples = total_samples - eligible_samples
        
        # 2. Availability rate (field completeness)
        availability_scores = []
        for r in records:
            protocol_result = r.protocol_result
            completeness = protocol_result.get('field_completeness', {}).get('completeness_rate', 0.0)
            availability_scores.append(completeness)
        availability_rate = np.mean(availability_scores) if availability_scores else 0.0
        
        # 3. Compliance rates by constraint type
        compliance_rate = {}
        constraint_types = ['numeric_validity', 'range_sanity', 'jump_dynamics', 
                          'cross_field_consistency', 'physics_constraint', 'safety_constraint']
        
        for constraint_type in constraint_types:
            passed = 0
            total = 0
            for r in records:
                evidence_atoms = r.evidence_pack.get('atoms', [])
                type_atoms = [a for a in evidence_atoms if a.type == constraint_type]
                if type_atoms:
                    total += len(type_atoms)
                    passed += sum(1 for a in type_atoms if a.pass_)
            
            if total > 0:
                compliance_rate[constraint_type] = (passed / total) * 100.0
            else:
                compliance_rate[constraint_type] = 100.0  # No evidence = all pass
        
        # 4. Constraint satisfaction profile
        constraint_satisfaction = {}
        for constraint_type in constraint_types:
            severity_counts = defaultdict(int)
            for r in records:
                evidence_atoms = r.evidence_pack.get('atoms', [])
                type_atoms = [a for a in evidence_atoms if a.type == constraint_type]
                for atom in type_atoms:
                    if not atom.pass_:
                        severity_counts[atom.severity.value] += 1
            
            constraint_satisfaction[constraint_type] = {
                'total_violations': sum(severity_counts.values()),
                'critical': severity_counts.get('critical', 0),
                'warning': severity_counts.get('warning', 0),
                'info': severity_counts.get('info', 0),
                'compliance_rate': compliance_rate.get(constraint_type, 100.0)
            }
        
        # 5. Conditional error statistics (for eligible samples only)
        eligible_records = [r for r in records if r.agent_output.get('adjudication') == 'eligible']
        conditional_error = {}
        
        if eligible_records:
            # Collect error scores
            error_scores = []
            for r in eligible_records:
                scores = r.optional_scores
                if scores and scores.get('conditional_error_score') is not None:
                    error_scores.append(scores['conditional_error_score'])
            
            if error_scores:
                conditional_error = {
                    'mean': np.mean(error_scores),
                    'median': np.median(error_scores),
                    'std': np.std(error_scores),
                    'min': np.min(error_scores),
                    'max': np.max(error_scores),
                    'p95': np.percentile(error_scores, 95),
                    'p99': np.percentile(error_scores, 99),
                    'count': len(error_scores)
                }
            else:
                conditional_error = {'count': 0}
        else:
            conditional_error = {'count': 0}
        
        # 6. Tail risk (P95/P99 and threshold exceedance rates)
        tail_risk = {}
        if eligible_records:
            # Calculate tail risk based on error scores
            error_scores = []
            for r in eligible_records:
                scores = r.optional_scores
                if scores and scores.get('conditional_error_score') is not None:
                    error_scores.append(scores['conditional_error_score'])
            
            if error_scores:
                p95 = np.percentile(error_scores, 95)
                p99 = np.percentile(error_scores, 99)
                
                # Threshold exceedance rates
                thresholds = [50, 70, 90]  # Error score thresholds
                exceedance_rates = {}
                for threshold in thresholds:
                    exceedance_rates[f'below_{threshold}'] = (np.array(error_scores) < threshold).sum() / len(error_scores) * 100.0
                
                tail_risk = {
                    'p95': float(p95),
                    'p99': float(p99),
                    'exceedance_rates': exceedance_rates
                }
            else:
                tail_risk = {}
        else:
            tail_risk = {}
        
        # 7. Failure mode distribution
        failure_modes = defaultdict(int)
        for r in records:
            if r.agent_output.get('adjudication') == 'ineligible':
                attribution = r.agent_output.get('attribution', [])
                for attr in attribution:
                    reason = attr.get('reason', 'unknown')
                    # Extract failure type from reason
                    if 'numeric' in reason.lower() or 'invalid' in reason.lower():
                        failure_modes['numeric_validity'] += 1
                    elif 'range' in reason.lower() or 'out of range' in reason.lower():
                        failure_modes['range_sanity'] += 1
                    elif 'mutation' in reason.lower() or 'jump' in reason.lower():
                        failure_modes['jump_dynamics'] += 1
                    elif 'cross' in reason.lower() or 'consistency' in reason.lower():
                        failure_modes['cross_field_consistency'] += 1
                    elif 'physics' in reason.lower() or 'continuity' in reason.lower():
                        failure_modes['physics_constraint'] += 1
                    elif 'safety' in reason.lower() or 'rapid' in reason.lower() or 'stall' in reason.lower():
                        failure_modes['safety_constraint'] += 1
                    else:
                        failure_modes['other'] += 1
        
        return TaskSummary(
            task_id=task_id,
            total_samples=total_samples,
            eligible_samples=eligible_samples,
            ineligible_samples=ineligible_samples,
            compliance_rate=compliance_rate,
            availability_rate=availability_rate,
            constraint_satisfaction=constraint_satisfaction,
            conditional_error=conditional_error,
            tail_risk=tail_risk,
            failure_modes=dict(failure_modes)
        )
    
    def generate_model_profile(self, records: List[Record], model_confidence: Optional[ModelConfidence]) -> ModelProfile:
        """
        Generate model-level profile
        
        Combines:
        - Data-driven profile (aggregated from records)
        - Model-level confidence prior (from ModelConfidence)
        - Conditional error distribution
        - Tail risk metrics
        
        Args:
            records: All records for this model
            model_confidence: Model-level confidence
        
        Returns:
            ModelProfile
        """
        import numpy as np
        from collections import defaultdict
        
        model_name = records[0].model_name if records else "unknown"
        
        if not records:
            return ModelProfile(
                model_name=model_name,
                data_driven_profile={},
                model_confidence_prior={}
            )
        
        # 1. Data-driven profile
        # Aggregate statistics across all records
        total_samples = len(records)
        eligible_samples = sum(1 for r in records if r.agent_output.get('adjudication') == 'eligible')
        eligibility_rate = (eligible_samples / total_samples * 100.0) if total_samples > 0 else 0.0
        
        # Score statistics
        availability_scores = []
        constraint_scores = []
        error_scores = []
        total_scores = []
        
        for r in records:
            scores = r.optional_scores
            if scores:
                if scores.get('availability_score') is not None:
                    availability_scores.append(scores['availability_score'])
                if scores.get('constraint_satisfaction_score') is not None:
                    constraint_scores.append(scores['constraint_satisfaction_score'])
                if scores.get('conditional_error_score') is not None:
                    error_scores.append(scores['conditional_error_score'])
                if scores.get('total_score') is not None:
                    total_scores.append(scores['total_score'])
        
        # Constraint violation statistics
        constraint_violations = defaultdict(int)
        for r in records:
            evidence_atoms = r.evidence_pack.get('atoms', [])
            for atom in evidence_atoms:
                if not atom.pass_:
                    constraint_violations[atom.type] += 1
        
        # Failure mode distribution
        failure_modes = defaultdict(int)
        for r in records:
            if r.agent_output.get('adjudication') == 'ineligible':
                attribution = r.agent_output.get('attribution', [])
                for attr in attribution:
                    reason = attr.get('reason', 'unknown')
                    if 'numeric' in reason.lower():
                        failure_modes['numeric_validity'] += 1
                    elif 'range' in reason.lower():
                        failure_modes['range_sanity'] += 1
                    elif 'mutation' in reason.lower():
                        failure_modes['jump_dynamics'] += 1
                    elif 'cross' in reason.lower():
                        failure_modes['cross_field_consistency'] += 1
                    elif 'physics' in reason.lower():
                        failure_modes['physics_constraint'] += 1
                    elif 'safety' in reason.lower():
                        failure_modes['safety_constraint'] += 1
        
        # Conditional error distribution (eligible samples only)
        eligible_records = [r for r in records if r.agent_output.get('adjudication') == 'eligible']
        conditional_error_dist = {}
        
        if eligible_records:
            eligible_error_scores = []
            for r in eligible_records:
                scores = r.optional_scores
                if scores and scores.get('conditional_error_score') is not None:
                    eligible_error_scores.append(scores['conditional_error_score'])
            
            if eligible_error_scores:
                conditional_error_dist = {
                    'mean': float(np.mean(eligible_error_scores)),
                    'median': float(np.median(eligible_error_scores)),
                    'std': float(np.std(eligible_error_scores)),
                    'p95': float(np.percentile(eligible_error_scores, 95)),
                    'p99': float(np.percentile(eligible_error_scores, 99)),
                    'min': float(np.min(eligible_error_scores)),
                    'max': float(np.max(eligible_error_scores)),
                    'count': len(eligible_error_scores)
                }
        
        # Tail risk metrics
        tail_risk = {}
        if eligible_records and error_scores:
            p95 = np.percentile(error_scores, 95)
            p99 = np.percentile(error_scores, 99)
            tail_risk = {
                'p95': float(p95),
                'p99': float(p99),
                'high_risk_samples': sum(1 for s in error_scores if s < 50),  # Error score < 50
                'high_risk_rate': (sum(1 for s in error_scores if s < 50) / len(error_scores) * 100.0) if error_scores else 0.0
            }
        
        # Build data-driven profile
        data_driven_profile = {
            'total_samples': total_samples,
            'eligible_samples': eligible_samples,
            'eligibility_rate': eligibility_rate,
            'score_statistics': {
                'availability': {
                    'mean': float(np.mean(availability_scores)) if availability_scores else None,
                    'std': float(np.std(availability_scores)) if availability_scores else None,
                    'min': float(np.min(availability_scores)) if availability_scores else None,
                    'max': float(np.max(availability_scores)) if availability_scores else None
                },
                'constraint_satisfaction': {
                    'mean': float(np.mean(constraint_scores)) if constraint_scores else None,
                    'std': float(np.std(constraint_scores)) if constraint_scores else None,
                    'min': float(np.min(constraint_scores)) if constraint_scores else None,
                    'max': float(np.max(constraint_scores)) if constraint_scores else None
                },
                'conditional_error': {
                    'mean': float(np.mean(error_scores)) if error_scores else None,
                    'std': float(np.std(error_scores)) if error_scores else None,
                    'min': float(np.min(error_scores)) if error_scores else None,
                    'max': float(np.max(error_scores)) if error_scores else None
                },
                'total': {
                    'mean': float(np.mean(total_scores)) if total_scores else None,
                    'std': float(np.std(total_scores)) if total_scores else None,
                    'min': float(np.min(total_scores)) if total_scores else None,
                    'max': float(np.max(total_scores)) if total_scores else None
                }
            },
            'constraint_violations': dict(constraint_violations),
            'failure_modes': dict(failure_modes),
            'conditional_error_distribution': conditional_error_dist,
            'tail_risk': tail_risk
        }
        
        # 2. Model-level confidence prior (keep separate from data-driven profile)
        model_confidence_prior = {}
        if model_confidence:
            model_confidence_prior = {
                "S1_score": model_confidence.confidence_m.get("S1_score"),
                "M1_score": model_confidence.confidence_m.get("M1_score"),
                "M3_score": model_confidence.confidence_m.get("M3_score"),
                "calculation_source": model_confidence.calculation_source,
                "version": model_confidence.version,
                "metadata": model_confidence.metadata
            }
        
        # 3. Optional total score (weighted average across tasks if multiple)
        optional_total_score = None
        if total_scores:
            optional_total_score = {
                'mean': float(np.mean(total_scores)),
                'median': float(np.median(total_scores)),
                'std': float(np.std(total_scores))
            }
        
        return ModelProfile(
            model_name=model_name,
            data_driven_profile=data_driven_profile,
            model_confidence_prior=model_confidence_prior,
            optional_total_score=optional_total_score
        )


if __name__ == "__main__":
    # Example usage
    evaluator = FLYEvalPlusPlus()
    print("FLY-EVAL++ initialized successfully")

