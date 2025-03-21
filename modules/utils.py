# modules/utils.py
import logging
from typing import Type, Any, TypeVar, List, Dict, Optional, Union

logger = logging.getLogger(__name__)

T = TypeVar('T')

def ensure_type(value: Any, expected_type: Type[T], default: Optional[T] = None) -> T:
    """
    Ensures a value is of the expected type or converts/defaults it.
    
    Args:
        value: The value to check/convert
        expected_type: The expected type
        default: Optional default value to use if conversion isn't possible
        
    Returns:
        Value with the correct type
    """
    if isinstance(value, expected_type):
        return value
    
    logger.warning(f"Type mismatch: Expected {expected_type.__name__}, got {type(value).__name__}: {value}")
    
    # Handle default value if provided
    if default is not None:
        return default
    
    # Try type-specific conversions
    try:
        if expected_type is str:
            if value is None:
                return ""
            return str(value)
            
        elif expected_type is list:
            if value is None:
                return []
            if hasattr(value, '__iter__') and not isinstance(value, (str, dict, bytes)):
                return list(value)
            return [value]
            
        elif expected_type is dict:
            if value is None:
                return {}
            if hasattr(value, 'items'):
                return dict(value)
            return {}
            
        elif expected_type is bool:
            if value is None:
                return False
            return bool(value)
            
        elif expected_type is int:
            if value is None:
                return 0
            return int(float(value)) if isinstance(value, (str, float)) else int(value)
            
        elif expected_type is float:
            if value is None:
                return 0.0
            return float(value)
            
        else:
            # For custom classes and other types, try initialization or return a default instance
            try:
                return expected_type(value)
            except:
                return expected_type()
    except Exception as e:
        logger.error(f"Error converting {value} to {expected_type.__name__}: {e}")
        # Final fallback - create empty/default instance
        try:
            return expected_type()
        except:
            logger.error(f"Could not create default instance of {expected_type.__name__}")
            if expected_type is str:
                return ""
            elif expected_type is list:
                return []
            elif expected_type is dict:
                return {}
            elif expected_type is bool:
                return False
            elif expected_type is int:
                return 0
            elif expected_type is float:
                return 0.0
            else:
                return None  # Last resort

def ensure_list(value: Any, item_type: Type = None) -> List:
    """
    Ensures a value is a list. Optionally ensures all items are of a specific type.
    
    Args:
        value: The value to convert to a list
        item_type: Optional type to enforce for all list items
        
    Returns:
        A list
    """
    result = ensure_type(value, list, [])
    
    if item_type and result:
        # Ensure each item in the list has the correct type
        return [ensure_type(item, item_type) for item in result]
    
    return result

def ensure_dict(value: Any, key_type: Type = None, value_type: Type = None) -> Dict:
    """
    Ensures a value is a dictionary. Optionally ensures keys/values have specific types.
    
    Args:
        value: The value to convert to a dict
        key_type: Optional type to enforce for dict keys
        value_type: Optional type to enforce for dict values
        
    Returns:
        A dictionary
    """
    result = ensure_type(value, dict, {})
    
    if (key_type or value_type) and result:
        new_dict = {}
        for k, v in result.items():
            new_key = ensure_type(k, key_type) if key_type else k
            new_value = ensure_type(v, value_type) if value_type else v
            new_dict[new_key] = new_value
        return new_dict
    
    return result

def ensure_str(value: Any) -> str:
    """Ensures a value is a string."""
    return ensure_type(value, str, "")

def ensure_int(value: Any) -> int:
    """Ensures a value is an integer."""
    return ensure_type(value, int, 0)

def ensure_float(value: Any) -> float:
    """Ensures a value is a float."""
    return ensure_type(value, float, 0.0)

def ensure_bool(value: Any) -> bool:
    """Ensures a value is a boolean."""
    return ensure_type(value, bool, False)