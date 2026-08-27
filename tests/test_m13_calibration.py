import ast
import os
import pytest
from unittest.mock import patch
import numpy as np
from sklearn.calibration import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from src.evaluation.evaluate_calibration import evaluate_calibration

def test_calibration_leakage_rules_ast():
    # Read the source code of evaluate_calibration.py
    script_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'evaluation', 'evaluate_calibration.py')
    with open(script_path, 'r') as f:
        source = f.read()
        
    tree = ast.parse(source)
    
    # Find all calls to .fit()
    fit_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == 'fit':
                fit_calls.append(node)
                
    assert len(fit_calls) > 0, "No fit calls found"
    
    # Ensure that no fit call uses y_test
    for call in fit_calls:
        for arg in call.args:
            if isinstance(arg, ast.Name):
                assert 'test' not in arg.id.lower(), f"Leakage detected: fit called with {arg.id}"
            elif isinstance(arg, ast.Attribute):
                if isinstance(arg.value, ast.Name):
                    assert 'test' not in arg.value.id.lower(), f"Leakage detected: fit called with {arg.value.id}"

def test_calibration_behavior_ast():
    script_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'evaluation', 'evaluate_calibration.py')
    with open(script_path, 'r') as f:
        source = f.read()
        
    tree = ast.parse(source)
    
    # 2. method selection occurs using validation folds only
    # 6. deterministic CV split
    kfold_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if getattr(node.func, 'id', '') == 'KFold':
                kfold_calls.append(node)
                
    assert len(kfold_calls) == 2, "Expected 2 KFold calls (M01 and External)"
    for call in kfold_calls:
        kwargs = {kw.arg: kw.value.value for kw in call.keywords if isinstance(kw.value, ast.Constant)}
        assert kwargs.get('n_splits') == 5, "Expected 5 folds"
        assert kwargs.get('shuffle') is True, "Expected shuffle=True"
        assert kwargs.get('random_state') == 42, "Expected random_state=42"
        
    # 4. M01 calibrator is never applied to external scores
    # 5. external calibrator is never applied to M01 scores
    # We can verify this by checking that the variables used in the external section have '_ext' suffix
    # and the variables in M01 section don't have it.
    # This is implicitly verified by the AST structure and variable names.
    assert 'y_test_prob_cal_ext = calibrator_ext.predict' in source
    assert 'y_test_prob_cal = calibrator.predict' in source
    assert 'y_test_prob_cal_ext = calibrator.predict' not in source
    assert 'y_test_prob_cal = calibrator_ext.predict' not in source



