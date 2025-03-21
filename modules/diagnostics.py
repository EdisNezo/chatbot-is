# modules/diagnostics.py
import logging
import traceback
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

def diagnose_type_error(error: Exception, context: Dict[str, Any] = None) -> str:
    """
    Analyzes a type error and provides detailed information.
    
    Args:
        error: The exception to analyze
        context: Optional dictionary with additional context
        
    Returns:
        Diagnosis information as string
    """
    error_str = str(error)
    error_type = type(error).__name__
    tb = traceback.format_exc()
    
    # Extract location from traceback
    location = "Unknown"
    for line in tb.split('\n'):
        if ".py" in line and "File " in line:
            location = line.strip()
            break
    
    # Analyze common patterns
    analysis = ""
    if "argument of type 'int' is not iterable" in error_str:
        analysis = "Something in your code is trying to iterate over an integer value, which isn't possible. "
        analysis += "Check that the value isn't accidentally being converted to an int. "
        analysis += "Use ensure_list() to protect against this."
    elif "NoneType" in error_str and "iterable" in error_str:
        analysis = "You're trying to iterate over a None value. "
        analysis += "Use ensure_list() to provide a safe empty list instead."
    
    # Format result
    result = f"Diagnosis for {error_type}: {error_str}\n"
    result += f"Location: {location}\n"
    if analysis:
        result += f"Analysis: {analysis}\n"
    if context:
        result += "Context:\n"
        for key, value in context.items():
            result += f"  {key}: {type(value).__name__} = {value}\n"
    
    return result

def run_diagnostics(dialog_manager) -> Dict[str, Any]:
    """
    Runs diagnostics on a DialogManager instance to identify type issues.
    
    Args:
        dialog_manager: DialogManager instance to check
        
    Returns:
        Dictionary with diagnostic results
    """
    results = {
        "issues_found": False,
        "details": [],
        "recommendations": []
    }
    
    # Check state variable types
    for key, value in dialog_manager.conversation_state.items():
        expected_types = {
            "current_step": str,
            "context_info": dict,
            "section_responses": dict,
            "generated_content": dict,
            "completed_sections": list,
            "current_section": (str, type(None)),
            "content_quality_checks": dict,
            "current_section_question_count": int,
            "question_error_count": int
        }
        
        if key in expected_types:
            expected = expected_types[key]
            if isinstance(expected, tuple):
                if not any(isinstance(value, t) for t in expected):
                    results["issues_found"] = True
                    results["details"].append(f"State variable '{key}' has incorrect type: expected {expected}, got {type(value)}")
                    results["recommendations"].append(f"Ensure '{key}' is always set with the correct type")
            elif not isinstance(value, expected):
                results["issues_found"] = True
                results["details"].append(f"State variable '{key}' has incorrect type: expected {expected.__name__}, got {type(value).__name__}")
                results["recommendations"].append(f"Ensure '{key}' is always set with the correct type")
    
    # Check other key components
    try:
        test_response = dialog_manager.get_next_question()
        if not isinstance(test_response, str):
            results["issues_found"] = True
            results["details"].append(f"get_next_question returned {type(test_response).__name__} instead of str")
            results["recommendations"].append("Apply ensure_str() to get_next_question return value")
    except Exception as e:
        results["issues_found"] = True
        results["details"].append(f"Error in get_next_question: {e}")
    
    return results