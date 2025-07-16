# test_get_set_field_info_final.py

import pytest
from typing import Union, List, Tuple, Any, Optional
from pydantic import BaseModel
from pydantic_partial import get_set_field_info
from pydantic_partial.partial import FieldNotSetError

# --- Test Models with Optional types (to allow explicit None) ---

class Inner(BaseModel):
    foo: Optional[int] = None
    bar: Optional[str] = None

class Middle(BaseModel):
    baz: Optional[float] = None
    inner: Optional[Inner] = None

class Outer(BaseModel):
    alpha: Optional[str] = None
    middle: Optional[Middle] = None
    count: Optional[int] = None

# --- Test Suite ---

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
            credentials: Optional[dict] = None

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
        self.outer = Outer(
            alpha=None,
            middle=Middle(
                baz=None,
                inner=Inner(foo=None, bar=None)
            ),
            count=None
        )

    def test_explicit_none_top(self):
        assert get_set_field_info(self.outer, "alpha") == ("alpha", None)

    def test_explicit_none_nested(self):
        assert get_set_field_info(self.outer, "middle.baz") == ("middle.baz", None)

    def test_explicit_none_deep(self):
        assert get_set_field_info(self.outer, "middle.inner.foo") == ("middle.inner.foo", None)

    def test_partial_match_explicit_none(self):
        assert get_set_field_info(self.outer, "bar") == ("middle.inner.bar", None)

    def test_explicit_none_count(self):
        assert get_set_field_info(self.outer, "count") == ("count", None)

    def test_explicit_none_vs_unset_distinction(self):
        outer_partial = Outer(alpha=None)
        assert get_set_field_info(outer_partial, "alpha") == ("alpha", None)
        result = get_set_field_info(outer_partial, "count")
        assert result is None

# -------- NEW TESTS BELOW --------

class TestGetSetFieldInfoNonexistentField:
    def setup_method(self):
        self.outer = Outer(alpha="A", count=5)

    def test_nonexistent_field_keyerror(self):
        # Field 'beta' does not exist anywhere in the Outer model definition
        with pytest.raises(KeyError):
            get_set_field_info(self.outer, "beta", raise_on_not_set=True)

    def test_deep_nonexistent_field(self):
        # 'middle.qux' does not exist at any depth in the model
        with pytest.raises(KeyError):
            get_set_field_info(self.outer, ["middle", "qux"], raise_on_not_set=True)

    def test_similar_but_nonexistent(self):
        with pytest.raises(KeyError):
            get_set_field_info(self.outer, "nonexistent", allow_partial_match=True, raise_on_not_set=True)

class TestGetSetFieldInfoKeyVsNotSet:
    def setup_method(self):
        self.outer = Outer(alpha="A")

    def test_field_declared_but_not_set(self):
        with pytest.raises(FieldNotSetError):
            get_set_field_info(self.outer, "count", raise_on_not_set=True)

    def test_field_declared_but_not_set_nested(self):
        with pytest.raises(FieldNotSetError):
            get_set_field_info(self.outer, "middle.baz", raise_on_not_set=True)

class TestGetSetFieldInfoPathErrors:
    def setup_method(self):
        self.outer = Outer(alpha="B", middle=Middle(inner=Inner()))

    def test_too_deep_path(self):
        # 'baz' is not valid inside Inner
        with pytest.raises(KeyError):
            get_set_field_info(self.outer, "middle.inner.baz", raise_on_not_set=True)

    def test_empty_path(self):
        with pytest.raises(KeyError):
            get_set_field_info(self.outer, [], raise_on_not_set=True)

class TestGetSetFieldInfoAliasesAndTypos:
    def setup_method(self):
        self.outer = Outer(alpha="AliasTest")

    def test_typo_field_keyerror(self):
        with pytest.raises(KeyError):
            get_set_field_info(self.outer, "alpah", raise_on_not_set=True)  # typo!

    def test_case_sensitivity(self):
        with pytest.raises(KeyError):
            get_set_field_info(self.outer, "Alpha", raise_on_not_set=True)  # capitalized

class TestGetSetFieldInfoExplicitNoneNonexistentNested:
    def setup_method(self):
        self.outer = Outer(
            alpha=None,
            middle=Middle(
                baz=None,
                inner=Inner(foo=None)  # bar not set
            ),
            count=None
        )

    def test_nonexistent_field_in_inner(self):
        with pytest.raises(KeyError):
            get_set_field_info(self.outer, "middle.inner.baz", raise_on_not_set=True)

