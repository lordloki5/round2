"""
A partial model will set certain (or all) fields to be optional with a default value of
`None`. This means you can construct a model copy with a partial representation of the details
you would normally provide.

Partial models can be used to for example only send a reduced version of your internal
models as response data to the client when you combine partial models with actively
replacing certain fields with `None` values and usage of `exclude_none` (or
`response_model_exclude_none`).

Usage example:
```python
# Something can be used as a partial, too
class Something(PartialModelMixin, pydantic.BaseModel):
    name: str
    age: int


# Create a full partial model
FullSomethingPartial = Something.as_partial()
FullSomethingPartial(name=None, age=None)
# You could also create a "partial Partial":
#AgeSomethingPartial = Something.as_partial("age")
```
"""
from typing import Union, List, Tuple, Any, Optional
import functools
import warnings
from typing import Any, Optional, TypeVar, Union, cast, get_args, get_origin

from pydantic_partial.utils import copy_field_info

try:
    from types import UnionType
except ImportError:
    UnionType = Union

import pydantic
from pydantic import BaseModel
SelfT = TypeVar("SelfT", bound=pydantic.BaseModel)
ModelSelfT = TypeVar("ModelSelfT", bound="PartialModelMixin")


@functools.lru_cache(maxsize=None, typed=True)
def create_partial_model(
    base_cls: type[SelfT],
    *fields: str,
    recursive: bool = False,
    partial_cls_name: Optional[str] = None,
) -> type[SelfT]:
    # Convert one type to being partial - if possible
    def _partial_annotation_arg(field_name_: str, field_annotation: type) -> type:
        if (
                isinstance(field_annotation, type)
                and issubclass(field_annotation, PartialModelMixin)
        ):
            field_prefix = f"{field_name_}."
            children_fields = [
                field.removeprefix(field_prefix)
                for field
                in fields_
                if field.startswith(field_prefix)
            ]
            if children_fields == ["*"]:
                children_fields = []
            return field_annotation.model_as_partial(*children_fields, recursive=recursive)
        else:
            return field_annotation

    # By default make all fields optional, but use passed fields when possible
    if fields:
        fields_ = list(fields)
    else:
        fields_ = list(base_cls.model_fields.keys())

    # Construct list of optional new field overrides
    optional_fields: dict[str, Any] = {}
    for field_name, field_info in base_cls.model_fields.items():
        field_annotation = field_info.annotation
        if field_annotation is None:  # pragma: no cover
            continue  # This is just to handle edge cases for pydantic 1.x - can be removed in pydantic 2.0

        # Do we have any fields starting with $FIELD_NAME + "."?
        sub_fields_requested = any(
            field.startswith(f"{field_name}.")
            for field
            in fields_
        )

        # Continue if this field needs not to be handled
        if field_name not in fields_ and not sub_fields_requested:
            continue

        # Change type for sub models, if requested
        if recursive or sub_fields_requested:
            field_annotation_origin = get_origin(field_annotation)
            if field_annotation_origin in (Union, UnionType, tuple, list, set, dict):
                if field_annotation_origin is UnionType:
                    field_annotation_origin = Union
                field_annotation = field_annotation_origin[  # type: ignore
                    tuple(  # type: ignore
                        _partial_annotation_arg(field_name, field_annotation_arg)
                        for field_annotation_arg
                        in get_args(field_annotation)
                    )
                ]
            else:
                field_annotation = _partial_annotation_arg(field_name, field_annotation)

        # Construct new field definition
        if field_name in fields_:
            if (  # if field is required, create Optional annotation
                field_info.is_required()
                or (
                    field_info.json_schema_extra is not None
                    and isinstance(field_info.json_schema_extra, dict)
                    and field_info.json_schema_extra.get("required", False)
                )
            ):
                optional_fields[field_name] = (
                    Optional[field_annotation],
                    copy_field_info(
                        field_info,
                        default=None,  # Set default to None
                        default_factory=None,  # Remove default_factory if set
                    ),
                )
        elif recursive or sub_fields_requested:
            optional_fields[field_name] = (
                field_annotation,
                copy_field_info(field_info),
            )

    # Return original model class if nothing has changed
    if not optional_fields:
        return base_cls

    if partial_cls_name is None:
        partial_cls_name = f"{base_cls.__name__}Partial"

    # Generate new subclass model with those optional fields
    return pydantic.create_model(
        partial_cls_name,
        __base__=base_cls,
        **optional_fields,
    )


class FieldNotSetError(Exception):
    pass


def get_set_field_info(
    model: BaseModel,
    key: Union[str, List[str]],
    allow_partial_match: bool = True,
    raise_on_not_set: bool = False,
    not_set_message: str = "Field was not set"
) -> Union[Tuple[str, Any], None]:
    """
    Checks if a (possibly nested) field was explicitly set on a Pydantic model.
    
    Uses comprehensive field validation to distinguish between:
    - Field not declared in schema (raises KeyError)
    - Field declared but not set (raises FieldNotSetError or returns None)
    - Field declared and set (returns tuple)

    Args:
        model: Pydantic BaseModel instance.
        key: Field name or dot-separated path or list of path components.
        allow_partial_match: If True, allows matching by suffix when full path not given.
        raise_on_not_set: If True, raises FieldNotSetError on missing.
        not_set_message: Custom message for missing fields.

    Returns:
        (full_path, value) if found and set.
        None if not found and raise_on_not_set=False.
        
    Raises:
        KeyError: If the field does not exist in the model schema.
        FieldNotSetError: If raise_on_not_set=True and field exists but not set.
    """
    if isinstance(key, str):
        key_path = key.split('.') if key else []
    else:
        key_path = list(key)
    
    if not key_path or key_path == [""]:
        raise KeyError('No field key provided (got empty key or list)')

    def _collect_declared_paths(model: BaseModel, prefix: str = "") -> set:
        """Collect all declared field paths from a model and its nested models."""
        declared = set()
        
        # Get the model class to access field definitions
        model_class = model.__class__
        
        for name, field in model_class.model_fields.items():
            path = f"{prefix}.{name}" if prefix else name
            declared.add(path)
            
            # Handle nested BaseModel fields
            ann = field.annotation
            
            # Handle Optional types (Union with None)
            if get_origin(ann) is Union:
                args = get_args(ann)
                for arg in args:
                    if arg is not type(None) and isinstance(arg, type) and issubclass(arg, BaseModel):
                        try:
                            nested_instance = arg()
                            declared.update(_collect_declared_paths(nested_instance, path))
                        except Exception:
                            # If we can't instantiate, try to get field info directly
                            try:
                                for nested_name in arg.model_fields:
                                    nested_path = f"{path}.{nested_name}"
                                    declared.add(nested_path)
                            except Exception:
                                pass
            # Handle direct BaseModel types
            elif isinstance(ann, type) and issubclass(ann, BaseModel):
                try:
                    nested_instance = ann()
                    declared.update(_collect_declared_paths(nested_instance, path))
                except Exception:
                    # If we can't instantiate, try to get field info directly
                    try:
                        for nested_name in ann.model_fields:
                            nested_path = f"{path}.{nested_name}"
                            declared.add(nested_path)
                    except Exception:
                        pass
        
        return declared

    def _collect_set_paths(model: BaseModel, prefix: str = "") -> dict:
        """Collect all paths to set fields in nested models."""
        result = {}
        
        for name in model.model_fields_set:
            path = f"{prefix}.{name}" if prefix else name
            val = getattr(model, name)
            
            if isinstance(val, BaseModel):
                result.update(_collect_set_paths(val, path))
                result[path] = val
            else:
                result[path] = val
        
        return result

    # Get all declared and set paths
    declared_paths = _collect_declared_paths(model)
    set_paths = _collect_set_paths(model)
    search = ".".join(key_path)

    # 1. Exact set match
    if search in set_paths:
        return search, set_paths[search]

    # 2. Partial set match if allowed
    if allow_partial_match:
        suffix = key_path[-1]
        candidates = [(p, v) for p, v in set_paths.items() if p.split('.')[-1] == suffix]
        if candidates:
            # Prefer leaf values (non-BaseModel)
            for p, v in candidates:
                if not isinstance(v, BaseModel):
                    return p, v
            return candidates[0]

    # 3. Check if field exists in schema
    field_exists = False
    
    # Check exact path
    if search in declared_paths:
        field_exists = True
    elif allow_partial_match:
        # Check suffix match in declared paths
        suffix = key_path[-1]
        if any(p.split('.')[-1] == suffix for p in declared_paths):
            field_exists = True

    if not field_exists:
        raise KeyError(f"No such field: '{key}'")

    # Field exists but not set
    message = f"{not_set_message}: '{key}'"
    if raise_on_not_set:
        raise FieldNotSetError(message)
    
    print(f"INFO: {message}")
    return None

def get_set_field_info2(
    model: pydantic.BaseModel,
    key: Union[str, List[str]],
    allow_partial_match: bool = True,
    raise_on_not_set: bool = False,
    not_set_message: str = "Field was not set"
) -> Union[Tuple[str, Any], None]:
    """
    Checks if a (possibly nested) field was explicitly set on a Pydantic model.
    
    This enhanced version performs deep recursive search for partial field matching
    across all nested models when allow_partial_match=True.

    Args:
        model: Pydantic BaseModel instance.
        key: Field name or dot-separated path or list of path components.
        allow_partial_match: If True, allows matching by suffix when full path not given.
        raise_on_not_set: If True, raises FieldNotSetError on missing.
        not_set_message: Custom message for missing fields.

    Returns:
        (full_path, value) if found and set.
        None if not found and raise_on_not_set=False.
    """
    if isinstance(key, str):
        key_path = key.split('.')
    else:
        key_path = key[:]

    def _collect_all_set_paths(model, prefix=""):
        """Recursively collect all paths to set fields in nested models"""
        paths = {}
        if not hasattr(model, "model_fields_set"):
            return paths
            
        for field_name in model.model_fields_set:
            field_value = getattr(model, field_name, None)
            full_path = f"{prefix}.{field_name}" if prefix else field_name
            
            if isinstance(field_value, pydantic.BaseModel):
                # If it's a nested model, recursively collect its paths
                nested_paths = _collect_all_set_paths(field_value, full_path)
                paths.update(nested_paths)
                # Also add the nested model itself
                paths[full_path] = field_value
            else:
                # It's a leaf value (including explicit None)
                paths[full_path] = field_value
        
        return paths

    def _exact_path_match(all_paths, key_path):
        """Try to find exact path match"""
        search_path = ".".join(key_path)
        if search_path in all_paths:
            return (search_path, all_paths[search_path])
        return None

    def _partial_path_match(all_paths, key_path):
        """Try to find partial path match (suffix matching)"""
        if not allow_partial_match:
            return None
            
        search_key = key_path[-1]  # Use the last component for suffix matching
        
        # Look for paths ending with the search key
        candidates = []
        for path, value in all_paths.items():
            if path.split('.')[-1] == search_key:
                candidates.append((path, value))
        
        # Prefer leaf nodes (non-BaseModel)
        leaf_candidates = [(p, v) for p, v in candidates if not isinstance(v, pydantic.BaseModel)]
        if leaf_candidates:
            return leaf_candidates[0]
        if candidates:
            return candidates[0]
        return None

    # Collect all set paths from the model
    all_set_paths = _collect_all_set_paths(model)
    
    # Try exact match first
    result = _exact_path_match(all_set_paths, key_path)
    if result:
        return result
    
    # Try partial match
    result = _partial_path_match(all_set_paths, key_path)
    if result:
        return result
    
    # No match found
    message = f"{not_set_message}: '{key}'"
    if raise_on_not_set:
        raise FieldNotSetError(message)
    print(f"INFO: {message}")
    return None

class PartialModelMixin(pydantic.BaseModel):
    """
    Partial model mixin. Will allow usage of `as_partial()` on the model class
    to create a partial version of the model class.
    """

    @classmethod
    def model_as_partial(
        cls: type[ModelSelfT],
        *fields: str,
        recursive: bool = False,
        partial_cls_name: Optional[str] = None,
    ) -> type[ModelSelfT]:
        return cast(
            type[ModelSelfT],
            create_partial_model(cls, *fields, recursive=recursive, partial_cls_name=partial_cls_name),
        )

    @classmethod
    def as_partial(
        cls: type[ModelSelfT],
        *fields: str,
        recursive: bool = False,
        partial_cls_name: Optional[str] = None,
    ) -> type[ModelSelfT]:
        warnings.warn(
            "as_partial(...) is deprecated, use model_as_partial(...) instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return cls.model_as_partial(*fields, recursive=recursive, partial_cls_name=partial_cls_name)
