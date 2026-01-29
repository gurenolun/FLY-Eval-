"""
Safety Constraint Checker V2
重新设计：基于预测误差而非绝对值进行安全性评估
"""

from typing import List, Dict, Any
from ..core.verifier_base import Verifier
from ..core.data_structures import EvidenceAtom, Severity, Scope


class SafetyConstraintCheckerV2(Verifier):
    """
    Safety constraint checker - 基于预测误差的安全性评估
    
    核心改进：
    1. 检查预测误差是否会导致安全问题（而非检查绝对值）
    2. 使用多级评分（0.0, 0.25, 0.5, 0.75, 1.0）
    3. 不同模型会得到不同的安全性得分
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize safety constraint checker"""
        super().__init__(config, verifier_id="SAFETY_CONSTRAINT_V2")
        self.enabled = config.get('enabled', False)
    
    def _normalize_to_list(self, value):
        """Convert scalar or list to list format"""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]
    
    def verify(self, sample: Any, model_output: Any, context: Dict[str, Any]) -> List[EvidenceAtom]:
        """
        Verify safety constraints based on prediction error
        
        Args:
            sample: Sample with gold/ground truth data
            model_output: ModelOutput object
            context: Context dict with 'json_data', 'task_type'
        
        Returns:
            List of EvidenceAtom objects with multi-level scores
        """
        evidence = []
        
        if not self.enabled:
            return evidence
        
        # 获取预测值和真实值
        predicted_data = context.get('json_data')
        ground_truth = sample.gold.get('next_second') or sample.gold.get('T+1', {})
        
        if predicted_data is None or not ground_truth:
            return evidence
        
        # Rule 1: Airspeed prediction error safety assessment
        evidence.extend(self._check_airspeed_safety(predicted_data, ground_truth))
        
        # Rule 2: Altitude prediction error safety assessment
        evidence.extend(self._check_altitude_safety(predicted_data, ground_truth))
        
        # Rule 3: Vertical speed prediction error safety assessment
        evidence.extend(self._check_vertical_speed_safety(predicted_data, ground_truth))
        
        return evidence
    
    def _check_airspeed_safety(self, predicted_data: Dict, ground_truth: Dict) -> List[EvidenceAtom]:
        """
        检查空速预测误差是否会导致安全问题
        """
        evidence = []
        
        pred_airspeed = predicted_data.get("Indicated Airspeed (kt)")
        true_airspeed = ground_truth.get("Indicated Airspeed (kt)")
        
        if pred_airspeed is None or true_airspeed is None:
            return evidence
        
        try:
            pred_vals = self._normalize_to_list(pred_airspeed)
            true_vals = self._normalize_to_list(true_airspeed)
            
            # 计算所有时间步的误差
            errors = []
            for pred_val, true_val in zip(pred_vals, true_vals):
                try:
                    pred_float = float(pred_val)
                    true_float = float(true_val)
                    error = abs(pred_float - true_float)
                    relative_error = error / max(abs(true_float), 1.0)  # 避免除零
                    errors.append((error, relative_error, pred_float, true_float))
                except (ValueError, TypeError):
                    continue
            
            if not errors:
                return evidence
            
            # 使用平均误差评分
            avg_error = sum(e[0] for e in errors) / len(errors)
            avg_rel_error = sum(e[1] for e in errors) / len(errors)
            max_error = max(e[0] for e in errors)
            
            # 多级评分
            # 考虑：绝对误差 + 相对误差 + 是否会导致危险决策
            score = self._calculate_airspeed_safety_score(
                avg_error, avg_rel_error, max_error, errors
            )
            
            # 判断是否通过
            pass_check = score >= 0.5
            
            # 根据得分设置严重程度
            if score < 0.25:
                severity = Severity.CRITICAL
            elif score < 0.5:
                severity = Severity.WARNING
            else:
                severity = Severity.INFO
            
            evidence.append(EvidenceAtom(
                id=self._generate_evidence_id(),
                type="safety_constraint",
                field="Airspeed_Safety",
                pass_=pass_check,
                severity=severity,
                scope=Scope.SAMPLE,
                score=score,
                message=f"Airspeed prediction safety: avg_error={avg_error:.1f}kt, max_error={max_error:.1f}kt, score={score:.2f}",
                meta={
                    "checker": "SafetyConstraintCheckerV2",
                    "rule": "airspeed_prediction_safety",
                    "avg_error": avg_error,
                    "avg_relative_error": avg_rel_error,
                    "max_error": max_error,
                    "num_timesteps": len(errors),
                    "score": score
                }
            ))
            
        except (ValueError, TypeError, IndexError) as e:
            pass
        
        return evidence
    
    def _calculate_airspeed_safety_score(self, avg_error, avg_rel_error, max_error, errors):
        """
        计算空速预测的安全性得分
        
        考虑因素：
        1. 平均绝对误差
        2. 平均相对误差
        3. 最大误差
        4. 是否会导致危险决策
        """
        # 基础评分（基于平均误差）
        if avg_error < 5:  # 误差 < 5 kt
            base_score = 1.0
        elif avg_error < 15:  # 误差 < 15 kt
            base_score = 0.75
        elif avg_error < 30:  # 误差 < 30 kt
            base_score = 0.5
        elif avg_error < 50:  # 误差 < 50 kt
            base_score = 0.25
        else:
            base_score = 0.0
        
        # 检查是否存在危险误判
        danger_penalty = 0.0
        for error, rel_error, pred, true in errors:
            # 情况1：低速误判为高速（失速风险）
            if true < 50 and pred > 100:
                danger_penalty = max(danger_penalty, 0.5)
            # 情况2：高速误判为低速（超速风险）
            elif true > 150 and pred < 100:
                danger_penalty = max(danger_penalty, 0.5)
            # 情况3：相对误差过大（> 50%）
            elif rel_error > 0.5:
                danger_penalty = max(danger_penalty, 0.25)
        
        # 最终得分
        final_score = max(0.0, base_score - danger_penalty)
        
        # 量化到5个等级
        if final_score >= 0.9:
            return 1.0
        elif final_score >= 0.65:
            return 0.75
        elif final_score >= 0.4:
            return 0.5
        elif final_score >= 0.15:
            return 0.25
        else:
            return 0.0
    
    def _check_altitude_safety(self, predicted_data: Dict, ground_truth: Dict) -> List[EvidenceAtom]:
        """检查高度预测误差是否会导致安全问题"""
        evidence = []
        
        pred_altitude = predicted_data.get("GPS Altitude (WGS84 ft)")
        true_altitude = ground_truth.get("GPS Altitude (WGS84 ft)")
        
        if pred_altitude is None or true_altitude is None:
            return evidence
        
        try:
            pred_vals = self._normalize_to_list(pred_altitude)
            true_vals = self._normalize_to_list(true_altitude)
            
            errors = []
            for pred_val, true_val in zip(pred_vals, true_vals):
                try:
                    pred_float = float(pred_val)
                    true_float = float(true_val)
                    error = abs(pred_float - true_float)
                    errors.append((error, pred_float, true_float))
                except (ValueError, TypeError):
                    continue
            
            if not errors:
                return evidence
            
            avg_error = sum(e[0] for e in errors) / len(errors)
            max_error = max(e[0] for e in errors)
            
            # 高度误差评分
            if avg_error < 50:  # < 50 ft
                score = 1.0
            elif avg_error < 150:  # < 150 ft
                score = 0.75
            elif avg_error < 300:  # < 300 ft
                score = 0.5
            elif avg_error < 500:  # < 500 ft
                score = 0.25
            else:
                score = 0.0
            
            # 检查危险情况：低空误判
            for error, pred, true in errors:
                if true < 500 and error > 200:  # 低空且误差大
                    score = min(score, 0.25)  # 降低得分
            
            pass_check = score >= 0.5
            severity = Severity.CRITICAL if score < 0.25 else (Severity.WARNING if score < 0.5 else Severity.INFO)
            
            evidence.append(EvidenceAtom(
                id=self._generate_evidence_id(),
                type="safety_constraint",
                field="Altitude_Safety",
                pass_=pass_check,
                severity=severity,
                scope=Scope.SAMPLE,
                score=score,
                message=f"Altitude prediction safety: avg_error={avg_error:.1f}ft, max_error={max_error:.1f}ft, score={score:.2f}",
                meta={
                    "checker": "SafetyConstraintCheckerV2",
                    "rule": "altitude_prediction_safety",
                    "avg_error": avg_error,
                    "max_error": max_error,
                    "num_timesteps": len(errors),
                    "score": score
                }
            ))
            
        except (ValueError, TypeError, IndexError):
            pass
        
        return evidence
    
    def _check_vertical_speed_safety(self, predicted_data: Dict, ground_truth: Dict) -> List[EvidenceAtom]:
        """检查垂直速度预测误差是否会导致安全问题"""
        evidence = []
        
        pred_vs = predicted_data.get("Vertical Speed (fpm)")
        true_vs = ground_truth.get("Vertical Speed (fpm)")
        
        if pred_vs is None or true_vs is None:
            return evidence
        
        try:
            pred_vals = self._normalize_to_list(pred_vs)
            true_vals = self._normalize_to_list(true_vs)
            
            errors = []
            for pred_val, true_val in zip(pred_vals, true_vals):
                try:
                    pred_float = float(pred_val)
                    true_float = float(true_val)
                    error = abs(pred_float - true_val)
                    errors.append((error, pred_float, true_float))
                except (ValueError, TypeError):
                    continue
            
            if not errors:
                return evidence
            
            avg_error = sum(e[0] for e in errors) / len(errors)
            max_error = max(e[0] for e in errors)
            
            # 垂直速度误差评分
            if avg_error < 500:  # < 500 fpm
                score = 1.0
            elif avg_error < 1000:  # < 1000 fpm
                score = 0.75
            elif avg_error < 1500:  # < 1500 fpm
                score = 0.5
            elif avg_error < 2000:  # < 2000 fpm
                score = 0.25
            else:
                score = 0.0
            
            # 检查危险情况：快速下降误判
            for error, pred, true in errors:
                if true < -2000 and abs(pred - true) > 1000:  # 快速下降且误差大
                    score = min(score, 0.25)
            
            pass_check = score >= 0.5
            severity = Severity.CRITICAL if score < 0.25 else (Severity.WARNING if score < 0.5 else Severity.INFO)
            
            evidence.append(EvidenceAtom(
                id=self._generate_evidence_id(),
                type="safety_constraint",
                field="Vertical_Speed_Safety",
                pass_=pass_check,
                severity=severity,
                scope=Scope.SAMPLE,
                score=score,
                message=f"Vertical speed prediction safety: avg_error={avg_error:.1f}fpm, max_error={max_error:.1f}fpm, score={score:.2f}",
                meta={
                    "checker": "SafetyConstraintCheckerV2",
                    "rule": "vertical_speed_prediction_safety",
                    "avg_error": avg_error,
                    "max_error": max_error,
                    "num_timesteps": len(errors),
                    "score": score
                }
            ))
            
        except (ValueError, TypeError, IndexError):
            pass
        
        return evidence
    
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities"""
        return ["safety_constraints_v2"]
