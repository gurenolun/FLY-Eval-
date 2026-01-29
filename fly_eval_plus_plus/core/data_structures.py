"""
Core data structures for FLY-EVAL++

Defines the input/output interfaces aligned with existing data.
"""

from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field as dataclass_field
from enum import Enum


class Severity(str, Enum):
    """Evidence severity levels"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class Scope(str, Enum):
    """Evidence scope"""
    FIELD = "field"
    SAMPLE = "sample"
    CROSS_FIELD = "cross_field"


class Adjudication(str, Enum):
    """Agent adjudication result"""
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"


@dataclass
class EvidenceAtom:
    """
    Atomic evidence unit - the fundamental building block of evidence pack
    
    Each atom represents a single verification result with full traceability.
    """
    id: str  # Unique evidence ID, e.g., "EVID_001"
    type: str  # Verifier type, e.g., "numeric_validity", "range_sanity"
    field: Optional[str] = None  # Field name if field-level check
    pass_: bool = True  # Verification result
    severity: Severity = Severity.INFO
    scope: Scope = Scope.FIELD
    message: str = ""
    meta: Dict[str, Any] = dataclass_field(default_factory=dict)  # Checker name, timestamp, config version
    score: Optional[float] = None  # Multi-level score: 0.0, 0.25, 0.5, 0.75, 1.0 (for fine-grained evaluation)


@dataclass
class EvalConfig:
    """
    Experiment-level configuration (versioned, methodology carrier)
    """
    version: str = "1.0.0"
    methodology: str = "FLY-EVAL++"
    
    # Task specifications
    task_specs: Dict[str, Dict[str, Any]] = dataclass_field(default_factory=dict)
    
    # Schema specification
    schema_spec: Dict[str, Dict[str, Any]] = dataclass_field(default_factory=dict)
    
    # Constraint library
    constraint_lib: Dict[str, Dict[str, Any]] = dataclass_field(default_factory=dict)
    
    # Phase policy (optional)
    phase_policy: Dict[str, Any] = dataclass_field(default_factory=dict)
    
    # Agent meta prompt
    agent_meta_prompt: Dict[str, Any] = dataclass_field(default_factory=dict)
    
    # Tools list
    tools: List[str] = dataclass_field(default_factory=list)
    
    # Fusion protocol
    fusion_protocol: Dict[str, Any] = dataclass_field(default_factory=dict)


@dataclass
class Sample:
    """
    Sample-level input
    """
    sample_id: str
    task_id: str  # "S1", "M1", "M3"
    context: Dict[str, Any]  # question, current_state, record_idx
    gold: Dict[str, Any]  # next_second or T+1, available flag


@dataclass
class ModelOutput:
    """
    Model output
    """
    model_name: str
    sample_id: str
    raw_response_text: str
    timestamp: str
    task_id: str


@dataclass
class ModelConfidence:
    """
    Model-level confidence prior
    """
    model_name: str
    confidence_m: Dict[str, float]  # {"S1_score": float, "M1_score": float, "M3_score": float}
    calculation_source: str
    version: str
    metadata: Dict[str, Any] = dataclass_field(default_factory=dict)


@dataclass
class Record:
    """
    Sample-level output - the most important deliverable
    
    Contains protocol results, evidence pack, agent output, optional scores, and trace.
    """
    sample_id: str
    model_name: str
    task_id: str
    
    # Protocol results
    protocol_result: Dict[str, Any] = dataclass_field(default_factory=dict)
    
    # Evidence pack
    evidence_pack: Dict[str, List[EvidenceAtom]] = dataclass_field(default_factory=dict)
    
    # Agent output
    agent_output: Dict[str, Any] = dataclass_field(default_factory=dict)
    
    # Optional scores
    optional_scores: Dict[str, Optional[float]] = dataclass_field(default_factory=dict)
    
    # Trace
    trace: Dict[str, Any] = dataclass_field(default_factory=dict)


@dataclass
class TaskSummary:
    """
    Task-level summary (aggregated by S1/M1/M3)
    """
    task_id: str
    total_samples: int
    eligible_samples: int
    ineligible_samples: int
    
    # Compliance rates
    compliance_rate: Dict[str, float] = dataclass_field(default_factory=dict)
    
    # Availability rate
    availability_rate: float = 0.0
    
    # Constraint satisfaction profile
    constraint_satisfaction: Dict[str, Dict[str, Any]] = dataclass_field(default_factory=dict)
    
    # Conditional error
    conditional_error: Dict[str, Any] = dataclass_field(default_factory=dict)
    
    # Tail risk
    tail_risk: Dict[str, float] = dataclass_field(default_factory=dict)
    
    # Failure mode distribution
    failure_modes: Dict[str, int] = dataclass_field(default_factory=dict)


@dataclass
class ModelProfile:
    """
    Model-level profile - core presentation
    
    Consists of data-driven profile + model-level confidence prior.
    """
    model_name: str
    
    # Data-driven profile
    data_driven_profile: Dict[str, Any] = dataclass_field(default_factory=dict)
    
    # Model-level confidence prior
    model_confidence_prior: Dict[str, Any] = dataclass_field(default_factory=dict)
    
    # Optional total score
    optional_total_score: Optional[Dict[str, Any]] = None

