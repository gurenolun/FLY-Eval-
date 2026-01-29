"""
Base classes for Verifier Graph Layer

All checks are implemented as verifier nodes in a DAG, each outputting EvidenceAtom.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from .data_structures import EvidenceAtom, Severity, Scope


class Verifier(ABC):
    """
    Base class for all verifiers
    
    Each verifier is a node in the verifier graph, outputting EvidenceAtom.
    New checks = add node/add spec, no need to change main logic.
    """
    
    def __init__(self, config: Dict[str, Any], verifier_id: str):
        """
        Initialize verifier
        
        Args:
            config: Configuration dictionary
            verifier_id: Unique identifier for this verifier
        """
        self.config = config
        self.verifier_id = verifier_id
        self.evidence_counter = 0
    
    def _generate_evidence_id(self) -> str:
        """Generate unique evidence ID"""
        self.evidence_counter += 1
        return f"EVID_{self.verifier_id}_{self.evidence_counter:04d}"
    
    @abstractmethod
    def verify(self, sample: Any, model_output: Any, context: Dict[str, Any]) -> List[EvidenceAtom]:
        """
        Perform verification and return evidence atoms
        
        Args:
            sample: Sample data
            model_output: Model output data
            context: Additional context (previous predictions, reference data, etc.)
        
        Returns:
            List of EvidenceAtom objects
        """
        pass
    
    def get_capabilities(self) -> List[str]:
        """
        Return list of capabilities/constraint IDs this verifier can check
        
        Returns:
            List of capability identifiers
        """
        return []


class VerifierGraph:
    """
    DAG of verifiers
    
    Organizes all verifiers into a directed acyclic graph for execution.
    """
    
    def __init__(self):
        """Initialize empty verifier graph"""
        self.verifiers: List[Verifier] = []
        self.dependencies: Dict[str, List[str]] = {}  # verifier_id -> [dependency_ids]
    
    def add_verifier(self, verifier: Verifier, dependencies: Optional[List[str]] = None):
        """
        Add a verifier to the graph
        
        Args:
            verifier: Verifier instance
            dependencies: List of verifier IDs this verifier depends on
        """
        self.verifiers.append(verifier)
        if dependencies:
            self.dependencies[verifier.verifier_id] = dependencies
        else:
            self.dependencies[verifier.verifier_id] = []
    
    def execute(self, sample: Any, model_output: Any, context: Dict[str, Any]) -> List[EvidenceAtom]:
        """
        Execute all verifiers in the graph and collect evidence
        
        Args:
            sample: Sample data
            model_output: Model output data
            context: Additional context
        
        Returns:
            List of all EvidenceAtom objects from all verifiers
        """
        all_evidence = []
        
        # Execute verifiers in dependency order (topological sort)
        executed = set()
        
        def execute_verifier(verifier: Verifier):
            """Execute verifier and its dependencies"""
            if verifier.verifier_id in executed:
                return
            
            # Execute dependencies first
            for dep_id in self.dependencies.get(verifier.verifier_id, []):
                for v in self.verifiers:
                    if v.verifier_id == dep_id:
                        execute_verifier(v)
                        break
            
            # Execute this verifier
            evidence = verifier.verify(sample, model_output, context)
            all_evidence.extend(evidence)
            executed.add(verifier.verifier_id)
        
        # Execute all verifiers
        for verifier in self.verifiers:
            execute_verifier(verifier)
        
        return all_evidence

