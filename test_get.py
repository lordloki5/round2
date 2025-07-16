# test_get_set_field_info_final.py

import pytest
from typing import Union, List, Tuple, Any, Optional
from pydantic import BaseModel
from pydantic_partial import get_set_field_info
from pydantic_partial.partial import FieldNotSetError
# --- Exceptions

# class FieldNotSetError(Exception):
#     pass

# --- Utility: Enhanced Field Detection

# def get_set_field_info2(
#     model: BaseModel,
#     key: Union[str, List[str]],
#     allow_partial_match: bool = True,
#     raise_on_not_set: bool = False,
#     not_set_message: str = "Field was not set"
# ) -> Union[Tuple[str, Any], None]:
#     """
#     Checks if a (possibly nested) field was explicitly set on a Pydantic model.
    
#     This enhanced version performs deep recursive search for partial field matching
#     across all nested models when allow_partial_match=True.

#     Args:
#         model: Pydantic BaseModel instance.
#         key: Field name or dot-separated path or list of path components.
#         allow_partial_match: If True, allows matching by suffix when full path not given.
#         raise_on_not_set: If True, raises FieldNotSetError on missing.
#         not_set_message: Custom message for missing fields.

#     Returns:
#         (full_path, value) if found and set.
#         None if not found and raise_on_not_set=False.
#     """
#     if isinstance(key, str):
#         key_path = key.split('.')
#     else:
#         key_path = key[:]

#     def _collect_all_set_paths(model, prefix=""):
#         """Recursively collect all paths to set fields in nested models"""
#         paths = {}
#         if not hasattr(model, "model_fields_set"):
#             return paths
            
#         for field_name in model.model_fields_set:
#             field_value = getattr(model, field_name, None)
#             full_path = f"{prefix}.{field_name}" if prefix else field_name
            
#             if isinstance(field_value, BaseModel):
#                 # If it's a nested model, recursively collect its paths
#                 nested_paths = _collect_all_set_paths(field_value, full_path)
#                 paths.update(nested_paths)
#                 # Also add the nested model itself
#                 paths[full_path] = field_value
#             else:
#                 # It's a leaf value (including explicit None)
#                 paths[full_path] = field_value
        
#         return paths

#     def _exact_path_match(all_paths, key_path):
#         """Try to find exact path match"""
#         search_path = ".".join(key_path)
#         if search_path in all_paths:
#             return (search_path, all_paths[search_path])
#         return None

#     def _partial_path_match(all_paths, key_path):
#         """Try to find partial path match (suffix matching)"""
#         if not allow_partial_match:
#             return None
            
#         search_key = key_path[-1]  # Use the last component for suffix matching
        
#         # Look for paths ending with the search key
#         candidates = []
#         for path, value in all_paths.items():
#             if path.split('.')[-1] == search_key:
#                 candidates.append((path, value))
        
#         # Prefer leaf nodes (non-BaseModel)
#         leaf_candidates = [(p, v) for p, v in candidates if not isinstance(v, BaseModel)]
#         if leaf_candidates:
#             return leaf_candidates[0]
#         if candidates:
#             return candidates[0]
#         return None

#     # Collect all set paths from the model
#     all_set_paths = _collect_all_set_paths(model)
    
#     # Try exact match first
#     result = _exact_path_match(all_set_paths, key_path)
#     if result:
#         return result
    
#     # Try partial match
#     result = _partial_path_match(all_set_paths, key_path)
#     if result:
#         return result
    
#     # No match found
#     message = f"{not_set_message}: '{key}'"
#     if raise_on_not_set:
#         raise FieldNotSetError(message)
#     print(f"INFO: {message}")
#     return None


# --- Test Models - CORRECTED with Optional types

class Inner(BaseModel):
    foo: Optional[int] = None    # ✅ Now accepts None explicitly
    bar: Optional[str] = None    # ✅ Now accepts None explicitly

class Middle(BaseModel):
    baz: Optional[float] = None   # ✅ Now accepts None explicitly
    inner: Optional[Inner] = None # ✅ Now accepts None explicitly

class Outer(BaseModel):
    alpha: Optional[str] = None    # ✅ Now accepts None explicitly
    middle: Optional[Middle] = None # ✅ Now accepts None explicitly
    count: Optional[int] = None    # ✅ Now accepts None explicitly


# --- Test Suite

class TestGetSetFieldInfoBasic:
    def setup_method(self):
        self.outer = Outer(
            alpha="A",
            middle=Middle(
                baz=3.14,
                inner=Inner(foo=42)
            )
        )

    def test_top_level_set(self):
        assert get_set_field_info(self.outer, "alpha") == ("alpha", "A")

    def test_top_level_not_set(self, capsys):
        result = get_set_field_info(self.outer, "count")
        assert result is None
        captured = capsys.readouterr()
        assert "Field was not set: 'count'" in captured.out

    def test_nested_exact(self):
        assert get_set_field_info(self.outer, ["middle", "baz"]) == ("middle.baz", 3.14)
        assert get_set_field_info(self.outer, "middle.baz") == ("middle.baz", 3.14)

    def test_deep_nested_exact(self):
        assert get_set_field_info(self.outer, ["middle", "inner", "foo"]) == ("middle.inner.foo", 42)
        assert get_set_field_info(self.outer, "middle.inner.foo") == ("middle.inner.foo", 42)

    def test_not_set_deep(self, capsys):
        result = get_set_field_info(self.outer, "middle.inner.bar")
        assert result is None
        captured = capsys.readouterr()
        assert "Field was not set: 'middle.inner.bar'" in captured.out

    def test_raise_on_not_set(self):
        with pytest.raises(FieldNotSetError):
            get_set_field_info(self.outer, "count", raise_on_not_set=True)

    def test_custom_message(self, capsys):
        result = get_set_field_info(self.outer, "count", not_set_message="Missing field")
        assert result is None
        captured = capsys.readouterr()
        assert "Missing field: 'count'" in captured.out


class TestGetSetFieldInfoPartialMatching:
    def setup_method(self):
        self.outer = Outer(
            alpha="Z",
            middle=Middle(
                inner=Inner(bar="hello")
            )
        )

    def test_partial_suffix(self):
        assert get_set_field_info(self.outer, "bar") == ("middle.inner.bar", "hello")

    def test_partial_disabled(self, capsys):
        result = get_set_field_info(self.outer, "bar", allow_partial_match=False)
        assert result is None
        captured = capsys.readouterr()
        assert "Field was not set: 'bar'" in captured.out

    def test_partial_mid(self):
        result = get_set_field_info(self.outer, "baz")
        assert result is None


class TestGetSetFieldInfoFalsyValues:
    def setup_method(self):
        self.outer = Outer(
            alpha="",
            middle=Middle(
                baz=0.0,
                inner=Inner(foo=0, bar="")
            ),
            count=0
        )

    def test_empty_string(self):
        assert get_set_field_info(self.outer, "alpha") == ("alpha", "")

    def test_zero_int(self):
        assert get_set_field_info(self.outer, "count") == ("count", 0)

    def test_zero_float(self):
        assert get_set_field_info(self.outer, "middle.baz") == ("middle.baz", 0.0)

    def test_empty_string_nested(self):
        assert get_set_field_info(self.outer, "middle.inner.bar") == ("middle.inner.bar", "")


class TestGetSetFieldInfoIntegration:
    def setup_method(self):
        data = {"alpha": "X", "middle": {"inner": {"foo": 7}}}
        self.outer = Outer.model_validate(data)

    def test_model_dump_exclude_unset(self):
        dumped = self.outer.model_dump(exclude_unset=True)
        assert dumped == {"alpha": "X", "middle": {"inner": {"foo": 7}}}

    def test_detect_after_validate(self):
        assert get_set_field_info(self.outer, "alpha") == ("alpha", "X")
        assert get_set_field_info(self.outer, "middle.inner.foo") == ("middle.inner.foo", 7)


class TestGetSetFieldInfoRealWorld:
    def setup_method(self):
        class Config(BaseModel):
            host: str
            port: int = 8080
            credentials: Optional[dict] = None  # ✅ Fixed with Optional

        self.cfg = Config(host="localhost")

    def test_required_field(self):
        assert get_set_field_info(self.cfg, "host") == ("host", "localhost")

    def test_default_field_not_set(self, capsys):
        result = get_set_field_info(self.cfg, "port")
        assert result is None
        captured = capsys.readouterr()
        assert "Field was not set: 'port'" in captured.out


class TestGetSetFieldInfoExplicitNone:
    def setup_method(self):
        # ✅ Now this works correctly - explicitly set some values to None
        self.outer = Outer(
            alpha=None,
            middle=Middle(
                baz=None,
                inner=Inner(foo=None, bar=None)
            ),
            count=None
        )

    def test_explicit_none_top(self):
        # alpha set explicitly to None
        assert get_set_field_info(self.outer, "alpha") == ("alpha", None)

    def test_explicit_none_nested(self):
        # middle.baz set explicitly to None
        assert get_set_field_info(self.outer, "middle.baz") == ("middle.baz", None)

    def test_explicit_none_deep(self):
        # middle.inner.foo set explicitly to None
        assert get_set_field_info(self.outer, "middle.inner.foo") == ("middle.inner.foo", None)

    def test_partial_match_explicit_none(self):
        # 'bar' matches middle.inner.bar and is explicitly None
        assert get_set_field_info(self.outer, "bar") == ("middle.inner.bar", None)

    def test_explicit_none_count(self):
        # count set explicitly to None
        assert get_set_field_info(self.outer, "count") == ("count", None)

    def test_explicit_none_vs_unset_distinction(self):
        # Create a model with some None values and some unset values
        outer_partial = Outer(alpha=None)  # Only alpha is set to None
        
        # alpha is explicitly set to None
        assert get_set_field_info(outer_partial, "alpha") == ("alpha", None)
        
        # count is not set at all (should return None from function)
        result = get_set_field_info(outer_partial, "count")
        assert result is None


