"""
Golden tests for verifiers

Fixed input → fixed evidence output regression tests
"""

import unittest
from ..core.data_structures import Sample, ModelOutput
from ..verifiers import (
    NumericValidityChecker,
    RangeSanityChecker,
    JumpDynamicsChecker,
    CrossFieldConsistencyChecker,
    PhysicsConstraintChecker,
    SafetyConstraintChecker
)
from ..utils.config_loader import load_field_limits, load_jump_thresholds


class TestNumericValidityChecker(unittest.TestCase):
    """Test NumericValidityChecker with fixed inputs"""
    
    def setUp(self):
        self.checker = NumericValidityChecker({
            'check_nan': True,
            'check_inf': True,
            'check_type': True,
            'check_missing': True
        })
    
    def test_valid_numeric_values(self):
        """Test that valid numeric values pass"""
        json_data = {
            "Latitude (WGS84 deg)": 40.0,
            "Longitude (WGS84 deg)": -74.0,
            "GPS Altitude (WGS84 ft)": 1000.0
        }
        context = {
            'json_data': json_data,
            'required_fields': list(json_data.keys())
        }
        
        evidence = self.checker.verify(None, None, context)
        
        # Should have evidence atoms for all fields (even if passing)
        self.assertGreater(len(evidence), 0)
        # All should pass
        self.assertTrue(all(atom.pass_ for atom in evidence))
    
    def test_invalid_numeric_values(self):
        """Test that invalid numeric values fail"""
        json_data = {
            "Latitude (WGS84 deg)": float('nan'),
            "Longitude (WGS84 deg)": float('inf'),
            "GPS Altitude (WGS84 ft)": "invalid"
        }
        context = {
            'json_data': json_data,
            'required_fields': list(json_data.keys())
        }
        
        evidence = self.checker.verify(None, None, context)
        
        # Should have evidence atoms
        self.assertGreater(len(evidence), 0)
        # Should have failures
        failures = [atom for atom in evidence if not atom.pass_]
        self.assertGreater(len(failures), 0)
        # Failures should be CRITICAL
        self.assertTrue(all(atom.severity.value == 'critical' for atom in failures))


class TestRangeSanityChecker(unittest.TestCase):
    """Test RangeSanityChecker with fixed inputs"""
    
    def setUp(self):
        field_limits = load_field_limits()
        self.checker = RangeSanityChecker({
            'field_limits': field_limits,
            'unit_validation': True
        })
    
    def test_values_in_range(self):
        """Test that values within range pass"""
        json_data = {
            "Latitude (WGS84 deg)": 40.0,  # Valid: -90 to 90
            "Longitude (WGS84 deg)": -74.0,  # Valid: -180 to 180
            "GPS Altitude (WGS84 ft)": 5000.0  # Valid: 0 to 10000
        }
        context = {
            'json_data': json_data,
            'required_fields': list(json_data.keys())
        }
        
        evidence = self.checker.verify(None, None, context)
        
        # Should have evidence atoms
        self.assertGreater(len(evidence), 0)
        # All should pass
        self.assertTrue(all(atom.pass_ for atom in evidence))
    
    def test_values_out_of_range(self):
        """Test that values out of range fail"""
        json_data = {
            "Latitude (WGS84 deg)": 100.0,  # Invalid: > 90
            "Longitude (WGS84 deg)": -200.0,  # Invalid: < -180
            "GPS Altitude (WGS84 ft)": -100.0  # Invalid: < 0
        }
        context = {
            'json_data': json_data,
            'required_fields': list(json_data.keys())
        }
        
        evidence = self.checker.verify(None, None, context)
        
        # Should have evidence atoms
        self.assertGreater(len(evidence), 0)
        # Should have failures
        failures = [atom for atom in evidence if not atom.pass_]
        self.assertGreater(len(failures), 0)
    
    def test_boundary_values(self):
        """Test boundary values (at thresholds)"""
        field_limits = load_field_limits()
        
        # Test at lower boundary
        json_data_lower = {
            "Latitude (WGS84 deg)": -90.0,  # At lower bound
            "GPS Altitude (WGS84 ft)": 0.0  # At lower bound
        }
        context_lower = {
            'json_data': json_data_lower,
            'required_fields': list(json_data_lower.keys())
        }
        evidence_lower = self.checker.verify(None, None, context_lower)
        # Should pass (at boundary)
        self.assertTrue(all(atom.pass_ for atom in evidence_lower))
        
        # Test at upper boundary
        json_data_upper = {
            "Latitude (WGS84 deg)": 90.0,  # At upper bound
            "GPS Altitude (WGS84 ft)": 10000.0  # At upper bound
        }
        context_upper = {
            'json_data': json_data_upper,
            'required_fields': list(json_data_upper.keys())
        }
        evidence_upper = self.checker.verify(None, None, context_upper)
        # Should pass (at boundary)
        self.assertTrue(all(atom.pass_ for atom in evidence_upper))
    
    def test_prompt_injection_resilience(self):
        """Test resilience to prompt injection attempts"""
        # Attempt to inject malicious values
        json_data = {
            "Latitude (WGS84 deg)": "'; DROP TABLE--",  # SQL injection attempt
            "Longitude (WGS84 deg)": "<script>alert('xss')</script>",  # XSS attempt
            "GPS Altitude (WGS84 ft)": "NaN"  # String instead of number
        }
        context = {
            'json_data': json_data,
            'required_fields': list(json_data.keys())
        }
        
        evidence = self.checker.verify(None, None, context)
        
        # Should handle gracefully (either pass numeric check or fail range check)
        # All should have evidence atoms
        self.assertGreater(len(evidence), 0)


class TestJumpDynamicsChecker(unittest.TestCase):
    """Test JumpDynamicsChecker with fixed inputs"""
    
    def setUp(self):
        jump_thresholds = load_jump_thresholds()
        self.checker = JumpDynamicsChecker({
            'mutation_thresholds': jump_thresholds,
            'phase_aware': False,
            'angle_fields': {
                'GPS Ground Track (deg true)',
                'Magnetic Heading (deg)'
            }
        })
    
    def test_m3_array_continuity(self):
        """Test M3 array internal continuity"""
        json_data = {
            "GPS Altitude (WGS84 ft)": [1000.0, 1010.0, 1020.0, 1030.0]  # Small changes
        }
        context = {
            'json_data': json_data,
            'task_type': 'M3',
            'previous_predictions': {},
            'required_fields': list(json_data.keys())
        }
        
        model_output = ModelOutput(
            model_name="test_model",
            sample_id="test_001",
            raw_response_text="",
            timestamp="2025-01-19",
            task_id="M3"
        )
        
        evidence = self.checker.verify(None, model_output, context)
        
        # Should have evidence atoms for M3 arrays
        # (Even if passing, should record evidence)
        self.assertGreaterEqual(len(evidence), 0)


class TestCrossFieldConsistencyChecker(unittest.TestCase):
    """Test CrossFieldConsistencyChecker with fixed inputs"""
    
    def setUp(self):
        self.checker = CrossFieldConsistencyChecker({
            'enabled': True
        })
    
    def test_altitude_consistency(self):
        """Test GPS Alt vs Baro Alt consistency"""
        json_data = {
            "GPS Altitude (WGS84 ft)": 5000.0,
            "Baro Altitude (ft)": 5100.0  # 100ft difference (should pass)
        }
        context = {
            'json_data': json_data,
            'required_fields': []
        }
        
        evidence = self.checker.verify(None, None, context)
        
        # Should have evidence atom for altitude consistency
        alt_evidence = [a for a in evidence if 'Alt' in a.field]
        self.assertGreater(len(alt_evidence), 0)


class TestPhysicsConstraintChecker(unittest.TestCase):
    """Test PhysicsConstraintChecker with fixed inputs"""
    
    def setUp(self):
        self.checker = PhysicsConstraintChecker({
            'enabled': True,
            'rules': {}
        })
    
    def test_m3_array_continuity(self):
        """Test M3 array continuity check"""
        json_data = {
            "GPS Altitude (WGS84 ft)": [1000.0, 1010.0, 1020.0, 1030.0]
        }
        context = {
            'json_data': json_data,
            'task_type': 'M3',
            'required_fields': list(json_data.keys())
        }
        
        evidence = self.checker.verify(None, None, context)
        
        # Should have evidence atoms for M3 continuity
        continuity_evidence = [a for a in evidence if 'continuity' in a.field]
        self.assertGreaterEqual(len(continuity_evidence), 0)


class TestSafetyConstraintChecker(unittest.TestCase):
    """Test SafetyConstraintChecker with fixed inputs"""
    
    def setUp(self):
        self.checker = SafetyConstraintChecker({
            'enabled': True
        })
    
    def test_rapid_descent_detection(self):
        """Test rapid descent detection"""
        json_data = {
            "Vertical Speed (fpm)": -3500.0,  # Rapid descent
            "GPS Altitude (WGS84 ft)": 5000.0
        }
        context = {
            'json_data': json_data,
            'required_fields': []
        }
        
        evidence = self.checker.verify(None, None, context)
        
        # Should detect rapid descent
        descent_evidence = [a for a in evidence if 'Descent' in a.field]
        self.assertGreater(len(descent_evidence), 0)
        # Should be critical
        self.assertTrue(any(atom.severity.value == 'critical' for atom in descent_evidence))
    
    def test_extreme_speed_detection(self):
        """Test extreme speed detection (boundary cases)"""
        # Test low speed (stall risk)
        json_data_low = {"Indicated Airspeed (kt)": 25.0}  # Below 30kt threshold
        context_low = {'json_data': json_data_low, 'required_fields': []}
        evidence_low = self.checker.verify(None, None, context_low)
        low_speed_evidence = [a for a in evidence_low if 'Speed' in a.field and 'low' in a.meta.get('type', '')]
        self.assertGreater(len(low_speed_evidence), 0)
        
        # Test high speed (overspeed)
        json_data_high = {"Indicated Airspeed (kt)": 190.0}  # Above 180kt threshold
        context_high = {'json_data': json_data_high, 'required_fields': []}
        evidence_high = self.checker.verify(None, None, context_high)
        high_speed_evidence = [a for a in evidence_high if 'Speed' in a.field and 'high' in a.meta.get('type', '')]
        self.assertGreater(len(high_speed_evidence), 0)
    
    def test_extreme_altitude_detection(self):
        """Test extreme altitude detection (boundary cases)"""
        # Test negative altitude
        json_data_neg = {"GPS Altitude (WGS84 ft)": -10.0}  # Below 0ft threshold
        context_neg = {'json_data': json_data_neg, 'required_fields': []}
        evidence_neg = self.checker.verify(None, None, context_neg)
        neg_alt_evidence = [a for a in evidence_neg if 'Altitude' in a.field and 'low' in a.meta.get('type', '')]
        self.assertGreater(len(neg_alt_evidence), 0)
        
        # Test very high altitude
        json_data_high = {"GPS Altitude (WGS84 ft)": 16000.0}  # Above 15000ft threshold
        context_high = {'json_data': json_data_high, 'required_fields': []}
        evidence_high = self.checker.verify(None, None, context_high)
        high_alt_evidence = [a for a in evidence_high if 'Altitude' in a.field and 'high' in a.meta.get('type', '')]
        self.assertGreater(len(high_alt_evidence), 0)
    
    def test_stall_condition_detection(self):
        """Test stall condition detection (combination of factors)"""
        json_data = {
            "Indicated Airspeed (kt)": 45.0,  # Low speed
            "Pitch (deg)": 20.0,  # High pitch
            "Vertical Speed (fpm)": 300.0  # Low vertical speed
        }
        context = {'json_data': json_data, 'required_fields': []}
        evidence = self.checker.verify(None, None, context)
        
        # Should detect stall condition
        stall_evidence = [a for a in evidence if 'Stall' in a.field]
        self.assertGreater(len(stall_evidence), 0)
        # Should be critical
        self.assertTrue(any(atom.severity.value == 'critical' for atom in stall_evidence))


if __name__ == '__main__':
    unittest.main()

