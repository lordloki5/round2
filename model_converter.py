from pydantic import BaseModel, ValidationError
from typing import Type, TypeVar, Any
import importlib

T = TypeVar("T", bound=BaseModel)

def convert_partial_to_full(partial_instance: BaseModel) -> BaseModel:
    """
    Convert a partial Pydantic model instance to its corresponding full model instance.
    
    Args:
        partial_instance: An instance of a partial model (e.g., created with create_partial_model).
    
    Returns:
        An instance of the corresponding full model.
    
    Raises:
        ValueError: If the model name doesn't end with 'Partial' or the full model is not found.
        ValidationError: Warped validation errors if the full model cannot be created due to missing required fields.
    """
    # Get the partial model class name (e.g., 'AddressPartial')
    partial_class_name = partial_instance.__class__.__name__
    
    # Check if the model name ends with 'Partial'
    if not partial_class_name.endswith("Partial"):
        raise ValueError(f"Expected a partial model ending with 'Partial', got '{partial_class_name}'")
    
    # Remove "Partial" suffix to get full model name
    full_class_name = partial_class_name[:-len("Partial")]
    
    # Get the module where the partial model is defined
    module_name = partial_instance.__class__.__module__
    
    # Import the module
    module = importlib.import_module(module_name)
    
    # Get the full model class
    try:
        full_model_class: Type[BaseModel] = getattr(module, full_class_name)
    except AttributeError:
        raise ValueError(f"Full model class '{full_class_name}' not found in module '{module_name}'")
    
    # Get non-None fields from the partial instance
    data = partial_instance.model_dump(exclude_none=True)
    
    # Recursively convert nested partial models
    for field_name, field_value in list(data.items()):
        if isinstance(field_value, BaseModel) and field_value.__class__.__name__.endswith("Partial"):
            data[field_name] = convert_partial_to_full(field_value)
        elif isinstance(field_value, list) and field_value and all(isinstance(item, BaseModel) and item.__class__.__name__.endswith("Partial") for item in field_value):
            data[field_name] = [convert_partial_to_full(item) for item in field_value]
    
    # Create the full model instance
    try:
        return full_model_class(**data)
    except ValidationError as e:
        raise ValidationError(f"Failed to create full model '{full_class_name}' due to validation errors: {str(e)}", full_model_class)