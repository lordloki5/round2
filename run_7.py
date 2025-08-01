import pytest
from pydantic import ValidationError
from json_schemas.models.address_schema import Address
from json_schemas.models.address_schema import PartialAddress
from model_converter import convert_partial_to_full

def test_full_address():
    address = Address(street="123 Main St", city="Anytown", zip_code="12345", country="USA")
    assert address.street == "123 Main St"
    assert address.city == "Anytown"
    assert address.zip_code == "12345"
    assert address.country == "USA"

def test_full_partial_address():
    partial_address = PartialAddress(street="123 Main St", city="Anytown", zip_code="12345", country="USA")
    assert partial_address.street == "123 Main St"
    assert partial_address.city == "Anytown"
    assert partial_address.zip_code == "12345"
    assert partial_address.country == "USA"

def test_partial_data_in_partial_address():
    partial_address = PartialAddress(street="123 Main St", city="Anytown")
    assert partial_address.street == "123 Main St"
    assert partial_address.city == "Anytown"
    assert partial_address.zip_code is None
    assert partial_address.country is None

def test_no_data_in_partial_address():
    partial_address = PartialAddress()
    assert partial_address.street is None
    assert partial_address.city is None
    assert partial_address.zip_code is None
    assert partial_address.country is None

def test_missing_required_fields_in_address():
    with pytest.raises(ValidationError) as e:
        Address(street="123 Main St", city="Anytown")
    assert "zip_code" in str(e)

def test_type_validation_in_partial_address():
    with pytest.raises(ValidationError) as e:
        PartialAddress(street=123)
    assert "street" in str(e)

    partial_address = PartialAddress(zip_code="12345")
    assert partial_address.zip_code == "12345"

    with pytest.raises(ValidationError) as e:
        PartialAddress(zip_code=12345)
    assert "zip_code" in str(e)

def test_optional_field_in_partial_address():
    partial_address = PartialAddress(country="USA")
    assert partial_address.country == "USA"

    partial_address = PartialAddress(country=None)
    assert partial_address.country is None

    partial_address = PartialAddress()
    assert partial_address.country is None

def test_convert_partial_to_full_success():
    partial_address = PartialAddress(street="123 Main St", city="Anytown", zip_code="12345", country="USA")
    full_address = convert_partial_to_full(partial_address)
    assert isinstance(full_address, Address)
    assert full_address.street == "123 Main St"
    assert full_address.city == "Anytown"
    assert full_address.zip_code == "12345"
    assert full_address.country == "USA"

def test_convert_partial_to_full_missing_required():
    partial_address = PartialAddress(street="123 Main St", city="Anytown")
    with pytest.raises(ValidationError) as e:
        convert_partial_to_full(partial_address)
    assert "zip_code" in str(e)

def test_convert_partial_to_full_empty():
    partial_address = PartialAddress()
    with pytest.raises(ValidationError) as e:
        convert_partial_to_full(partial_address)
    assert "street" in str(e)
    assert "city" in str(e)
    assert "zip_code" in str(e)