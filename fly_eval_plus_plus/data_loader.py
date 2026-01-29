"""
Data Loader for FLY-EVAL++

Loads and aligns:
- S1/M1/M3 sample inputs
- Ground truth (if available)
- Model raw responses
- Model-level confidence

Maps to Sample/ModelOutput/ModelConfidence data structures.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from .core.data_structures import Sample, ModelOutput, ModelConfidence


class DataLoader:
    """
    Data loader for FLY-EVAL++
    
    Handles loading and alignment of:
    - Sample inputs (questions, context)
    - Ground truth (reference data)
    - Model outputs (raw responses)
    - Model-level confidence
    """
    
    def __init__(self, base_dir: str = None):
        """
        Initialize data loader
        
        Args:
            base_dir: Base directory for data files (default: ICML2026/)
        """
        if base_dir is None:
            # Default to ICML2026 directory
            self.base_dir = Path(__file__).parent.parent
        else:
            self.base_dir = Path(base_dir)
        
        # Data paths (支持多种路径)
        self.s1_results_dir = self.base_dir / "data" / "model_results" / "S1_20251106_020205"
        # 如果不存在，尝试外部路径
        if not self.s1_results_dir.exists():
            self.s1_results_dir = Path("../../model_invocation/results/S1/20251106_020205")
        
        self.m1_results_dir = self.base_dir / "data" / "model_results" / "M1" / "20251107_155714"
        if not self.m1_results_dir.exists():
            # 尝试多个可能的路径
            possible_paths = [
                self.base_dir.parent / "model_invocation" / "results" / "M1" / "20251107_155714",
                Path("../../model_invocation/results/M1/20251107_155714"),
                Path("../../../model_invocation/results/M1/20251107_155714")
            ]
            for path in possible_paths:
                if path.exists():
                    self.m1_results_dir = path
                    break
        
        self.m3_results_dir = self.base_dir / "data" / "model_results" / "M3" / "20251108_155714"
        if not self.m3_results_dir.exists():
            # 尝试多个可能的路径
            possible_paths = [
                self.base_dir.parent / "model_invocation" / "results" / "M3" / "20251108_155714",
                Path("../../model_invocation/results/M3/20251108_155714"),
                Path("../../../model_invocation/results/M3/20251108_155714")
            ]
            for path in possible_paths:
                if path.exists():
                    self.m3_results_dir = path
                    break
        
        self.s1_reference_file = self.base_dir / "data" / "reference_data" / "next_second_pairs.jsonl"
        if not self.s1_reference_file.exists():
            self.s1_reference_file = Path("../../flight_prediction/next_second_pairs.jsonl")
        
        self.m1_m3_reference_file = self.base_dir / "data" / "reference_data" / "flight_3window_samples.jsonl"
        if not self.m1_m3_reference_file.exists():
            self.m1_m3_reference_file = Path("../../flight_prediction/flight_3window_samples.jsonl")
        
        # Confidence data paths
        self.s1_confidence_file = Path("model_invocation/results/S1_Sampled/20251211_232322/confidence_scores_v8.json")
        self.m1_confidence_file = Path("model_invocation/results/M1_Sampled/20251207_215742_cleaned/confidence_scores_v8.json")
        self.m3_confidence_file = Path("model_invocation/results/M3_Sampled/20251213_000254/confidence_scores_v8.json")
        
        # Cache
        self._reference_data_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._confidence_cache: Dict[str, Dict[str, float]] = {}
    
    def load_reference_data(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Load reference data (ground truth)
        
        Args:
            task_id: Task ID ("S1", "M1", "M3")
        
        Returns:
            List of reference records
        """
        if task_id in self._reference_data_cache:
            return self._reference_data_cache[task_id]
        
        reference_data = []
        
        if task_id == "S1":
            if self.s1_reference_file.exists():
                with open(self.s1_reference_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            reference_data.append(json.loads(line))
        elif task_id in ["M1", "M3"]:
            if self.m1_m3_reference_file.exists():
                with open(self.m1_m3_reference_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            reference_data.append(json.loads(line))
        
        self._reference_data_cache[task_id] = reference_data
        return reference_data
    
    def load_model_confidence(self) -> Dict[str, ModelConfidence]:
        """
        Load model-level confidence for all tasks
        
        Returns:
            Dictionary mapping model_name to ModelConfidence
        """
        confidence_dict = {}
        
        # Load S1 confidence
        if self.s1_confidence_file.exists():
            with open(self.s1_confidence_file, 'r', encoding='utf-8') as f:
                s1_data = json.load(f)
                for result in s1_data.get('results', []):
                    model_name = result.get('model_name', '')
                    if model_name:
                        if model_name not in confidence_dict:
                            confidence_dict[model_name] = {
                                'S1_score': None,
                                'M1_score': None,
                                'M3_score': None
                            }
                        confidence_dict[model_name]['S1_score'] = result.get('c_score')
        
        # Load M1 confidence
        if self.m1_confidence_file.exists():
            with open(self.m1_confidence_file, 'r', encoding='utf-8') as f:
                m1_data = json.load(f)
                for result in m1_data.get('results', []):
                    model_name = result.get('model_name', '')
                    if model_name:
                        if model_name not in confidence_dict:
                            confidence_dict[model_name] = {
                                'S1_score': None,
                                'M1_score': None,
                                'M3_score': None
                            }
                        confidence_dict[model_name]['M1_score'] = result.get('c_score')
        
        # Load M3 confidence
        if self.m3_confidence_file.exists():
            with open(self.m3_confidence_file, 'r', encoding='utf-8') as f:
                m3_data = json.load(f)
                for result in m3_data.get('results', []):
                    model_name = result.get('model_name', '')
                    if model_name:
                        if model_name not in confidence_dict:
                            confidence_dict[model_name] = {
                                'S1_score': None,
                                'M1_score': None,
                                'M3_score': None
                            }
                        confidence_dict[model_name]['M3_score'] = result.get('c_score')
        
        # Convert to ModelConfidence objects
        model_confidence_objects = {}
        for model_name, scores in confidence_dict.items():
            model_confidence_objects[model_name] = ModelConfidence(
                model_name=model_name,
                confidence_m=scores,
                calculation_source="calculate_confidence_score_v8_refined.py",
                version="v8",
                metadata={
                    "calculation_date": "2025-01-19",
                    "method": "ENCE-based",
                    "scoring_method": "refined_absolute",
                    "metrics_used": ["ENCE", "Interval_Width"]
                }
            )
        
        return model_confidence_objects
    
    def load_model_outputs(self, task_id: str, model_name: str) -> List[Dict[str, Any]]:
        """
        Load model outputs for a specific task and model
        
        Args:
            task_id: Task ID ("S1", "M1", "M3")
            model_name: Model name
        
        Returns:
            List of model output records (JSONL format)
        """
        # Determine results directory
        if task_id == "S1":
            results_dir = self.s1_results_dir
        elif task_id == "M1":
            results_dir = self.m1_results_dir
        elif task_id == "M3":
            results_dir = self.m3_results_dir
        else:
            return []
        
        if not results_dir.exists():
            return []
        
        # Find model directory
        model_dir = results_dir / model_name
        if not model_dir.exists():
            return []
        
        # Find JSONL file
        jsonl_files = list(model_dir.glob("*.jsonl"))
        if not jsonl_files:
            return []
        
        # Load first JSONL file
        outputs = []
        with open(jsonl_files[0], 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    outputs.append(json.loads(line))
        
        return outputs
    
    def create_samples_and_outputs(self, task_id: str, model_name: str) -> Tuple[List[Sample], List[ModelOutput]]:
        """
        Create Sample and ModelOutput objects for a task and model
        
        Args:
            task_id: Task ID ("S1", "M1", "M3")
            model_name: Model name
        
        Returns:
            Tuple of (samples, model_outputs)
        """
        # Load model outputs
        model_outputs_raw = self.load_model_outputs(task_id, model_name)
        if not model_outputs_raw:
            return [], []
        
        # Load reference data
        reference_data = self.load_reference_data(task_id)
        
        samples = []
        model_outputs = []
        
        for i, output_raw in enumerate(model_outputs_raw):
            sample_id = output_raw.get('id', f"{task_id}_{i:03d}")
            question = output_raw.get('question', '')
            response = output_raw.get('response', '')
            timestamp = output_raw.get('timestamp', '')
            
            # Extract current state from question (simplified - could be improved)
            current_state = self._extract_current_state_from_question(question)
            
            # Get gold (ground truth)
            gold = {}
            gold_available = False
            
            if task_id == "S1" and i < len(reference_data):
                ref_record = reference_data[i]
                gold = {
                    "next_second": ref_record.get('next_second', {}),
                    "available": True
                }
                gold_available = True
            elif task_id in ["M1", "M3"]:
                # M1/M3 use record_idx or calculate index
                # For M1: use index directly
                # For M3: use index 504+i (as in original code)
                if task_id == "M1" and i < len(reference_data):
                    ref_record = reference_data[i]
                    t_plus_1 = ref_record.get('T+1', {})
                    # Extract first value for M1
                    gold = {}
                    for field in [
                        "Latitude (WGS84 deg)", "Longitude (WGS84 deg)", "GPS Altitude (WGS84 ft)",
                        "GPS Ground Track (deg true)", "Magnetic Heading (deg)",
                        "GPS Velocity E (m/s)", "GPS Velocity N (m/s)", "GPS Velocity U (m/s)",
                        "GPS Ground Speed (kt)", "Roll (deg)", "Pitch (deg)", "Turn Rate (deg/sec)",
                        "Slip/Skid", "Normal Acceleration (G)", "Lateral Acceleration (G)",
                        "Vertical Speed (fpm)", "Indicated Airspeed (kt)",
                        "Baro Altitude (ft)", "Pressure Altitude (ft)"
                    ]:
                        if field in t_plus_1:
                            value_array = t_plus_1[field]
                            if isinstance(value_array, list) and len(value_array) > 0:
                                gold[field] = value_array[0]
                    gold = {"T+1": gold, "available": True}
                    gold_available = True
                elif task_id == "M3":
                    ref_idx = 504 + i  # M3 uses index 504+i
                    if ref_idx < len(reference_data):
                        ref_record = reference_data[ref_idx]
                        gold = {
                            "T+1": ref_record.get('T+1', {}),
                            "available": True
                        }
                        gold_available = True
            
            # Create Sample
            sample = Sample(
                sample_id=sample_id,
                task_id=task_id,
                context={
                    "question": question,
                    "current_state": current_state,
                    "record_idx": i if task_id == "S1" else (i if task_id == "M1" else 504 + i)
                },
                gold=gold if gold_available else {"available": False}
            )
            samples.append(sample)
            
            # Create ModelOutput
            model_output = ModelOutput(
                model_name=model_name,
                sample_id=sample_id,
                raw_response_text=response,
                timestamp=timestamp,
                task_id=task_id
            )
            model_outputs.append(model_output)
        
        return samples, model_outputs
    
    def _extract_current_state_from_question(self, question: str) -> Dict[str, Any]:
        """
        Extract current state from question text
        
        Simplified extraction - could be improved with better parsing
        """
        current_state = {}
        
        # Try to extract JSON from question
        try:
            # Look for JSON in question
            import re
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_pattern, question)
            if matches:
                # Try to parse first JSON match
                json_str = matches[0]
                current_state = json.loads(json_str)
        except:
            pass
        
        return current_state
    
    def get_all_models_for_task(self, task_id: str) -> List[str]:
        """
        Get all model names for a task
        
        Args:
            task_id: Task ID ("S1", "M1", "M3")
        
        Returns:
            List of model names
        """
        if task_id == "S1":
            results_dir = self.s1_results_dir
        elif task_id == "M1":
            results_dir = self.m1_results_dir
        elif task_id == "M3":
            results_dir = self.m3_results_dir
        else:
            return []
        
        if not results_dir.exists():
            return []
        
        # Get all subdirectories (model names)
        models = [d.name for d in results_dir.iterdir() if d.is_dir()]
        return sorted(models)

