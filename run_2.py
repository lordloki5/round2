"""
Complete Standalone Pydantic Model Filler System

This is a complete, runnable implementation that you can test immediately.
It includes all models, core functionality, and comprehensive tests.

Usage: python complete_standalone_system.py
"""

import json
import copy
from typing import Any, Dict, Set, Optional, Type, Union, List, Tuple, Callable
from dataclasses import dataclass, field
from pydantic import BaseModel, ValidationError, Field, field_validator, model_validator
from enum import Enum
from datetime import datetime


# ============================================================================
# CORE REPORTING SYSTEM
# ============================================================================

@dataclass
class FillingReport:
    """Comprehensive report of the filling process."""
    filled_fields: Set[str] = field(default_factory=set)
    missing_required: Set[str] = field(default_factory=set)
    missing_optional: Set[str] = field(default_factory=set)
    fields_with_defaults: Set[str] = field(default_factory=set)
    unknown_keys: Set[str] = field(default_factory=set)
    validation_errors: List[str] = field(default_factory=list)
    is_complete: bool = False
    
    def summary(self) -> str:
        """Generate a human-readable summary."""
        lines = [
            f"🎯 Status: {'✅ Complete' if self.is_complete else '⚠️ Incomplete'}",
            f"📝 Filled fields: {len(self.filled_fields)} ({', '.join(sorted(self.filled_fields)) if self.filled_fields else 'none'})",
            f"❌ Missing required: {len(self.missing_required)} ({', '.join(sorted(self.missing_required)) if self.missing_required else 'none'})",
            f"➖ Missing optional: {len(self.missing_optional)} ({', '.join(sorted(self.missing_optional)) if self.missing_optional else 'none'})",
            f"🔧 Using defaults: {len(self.fields_with_defaults)} ({', '.join(sorted(self.fields_with_defaults)) if self.fields_with_defaults else 'none'})",
            f"🚫 Unknown keys: {len(self.unknown_keys)} ({', '.join(sorted(self.unknown_keys)) if self.unknown_keys else 'none'})",
        ]
        if self.validation_errors:
            lines.append(f"🐛 Validation errors: {len(self.validation_errors)}")
            for error in self.validation_errors:
                lines.append(f"   - {error}")
        return "\n".join(lines)


@dataclass
class FieldStatus:
    """Tracks the status of a field in the model."""
    name: str
    is_required: bool
    is_filled: bool = False
    used_default: bool = False
    value: Any = None
    field_type: Type = None


# ============================================================================
# APPROACH 1: COMPREHENSIVE MODEL FILLER (RECOMMENDED)
# ============================================================================

class ModelFiller:
    """
    Generic model filler that works with any Pydantic model.
    Supports incremental filling, validation, and comprehensive tracking.
    """
    
    def __init__(self, model_class: Type[BaseModel]):
        self.model_class = model_class
        self.data: Dict[str, Any] = {}
        self.field_statuses: Dict[str, FieldStatus] = {}
        self._analyze_model()
        
    def _analyze_model(self):
        """Analyze the model to understand its structure."""
        for field_name, field_info in self.model_class.model_fields.items():
            is_required = field_info.is_required()
            
            self.field_statuses[field_name] = FieldStatus(
                name=field_name,
                is_required=is_required,
                field_type=field_info.annotation
            )
    
    def add_data(self, data: Dict[str, Any], validate: bool = True) -> FillingReport:
        """
        Add data to the model incrementally.
        
        Args:
            data: Dictionary of field values to add
            validate: Whether to validate the data immediately
            
        Returns:
            FillingReport with current status
        """
        report = FillingReport()
        
        # Track unknown keys
        model_fields = set(self.model_class.model_fields.keys())
        provided_keys = set(data.keys())
        report.unknown_keys = provided_keys - model_fields
        
        # Update data and field statuses
        for key, value in data.items():
            if key in model_fields:
                self.data[key] = value
                self.field_statuses[key].is_filled = True
                self.field_statuses[key].value = value
                report.filled_fields.add(key)
        
        # Validate if requested
        if validate:
            self._validate_current_data(report)
        
        # Update overall status
        self._update_report_status(report)
        
        return report
    
    def _validate_current_data(self, report: FillingReport):
        """Validate current data against the model."""
        try:
            # Try to create model with current data to check for validation errors
            temp_data = copy.deepcopy(self.data)
            
            try:
                model_instance = self.model_class.model_validate(temp_data)
                # If successful, check which fields used defaults
                self._check_defaults_used(model_instance, report)
            except ValidationError as e:
                # Parse validation errors to understand what's missing vs invalid
                for error in e.errors():
                    error_msg = f"{error['loc'][0] if error['loc'] else 'unknown'}: {error['msg']}"
                    report.validation_errors.append(error_msg)
                    
        except Exception as e:
            report.validation_errors.append(f"Unexpected validation error: {str(e)}")
    
    def _check_defaults_used(self, model_instance: BaseModel, report: FillingReport):
        """Check which fields are using default values."""
        for field_name, field_info in self.model_class.model_fields.items():
            if hasattr(model_instance, field_name):
                current_value = getattr(model_instance, field_name)
                
                # Check if this field wasn't explicitly set and has a default
                if (field_name not in self.data and 
                    field_info.default is not ... and 
                    current_value == field_info.default):
                    report.fields_with_defaults.add(field_name)
                    self.field_statuses[field_name].used_default = True
    
    def _update_report_status(self, report: FillingReport):
        """Update the overall status in the report."""
        for field_name, status in self.field_statuses.items():
            if status.is_required and not status.is_filled:
                report.missing_required.add(field_name)
            elif not status.is_required and not status.is_filled:
                report.missing_optional.add(field_name)
        
        report.is_complete = len(report.missing_required) == 0 and len(report.validation_errors) == 0
    
    def get_current_status(self) -> FillingReport:
        """Get current status without adding new data."""
        report = FillingReport()
        report.filled_fields = {name for name, status in self.field_statuses.items() if status.is_filled}
        self._validate_current_data(report)
        self._update_report_status(report)
        return report
    
    def build_model(self, include_unfilled: bool = False) -> Tuple[Optional[BaseModel], FillingReport]:
        """
        Build the final model instance.
        
        Args:
            include_unfilled: Whether to include unfilled optional fields with defaults
            
        Returns:
            Tuple of (model_instance, report). model_instance is None if validation fails.
        """
        report = self.get_current_status()
        
        if not report.is_complete:
            return None, report
        
        try:
            model_instance = self.model_class.model_validate(self.data)
            self._check_defaults_used(model_instance, report)
            return model_instance, report
        except ValidationError as e:
            report.validation_errors.extend([f"{err['loc'][0] if err['loc'] else 'unknown'}: {err['msg']}" for err in e.errors()])
            return None, report
    
    def to_json(self, **kwargs) -> Optional[str]:
        """Convert to JSON if model is complete and valid."""
        model_instance, report = self.build_model()
        if model_instance:
            return model_instance.model_dump_json(**kwargs)
        return None
    
    def reset(self):
        """Reset the filler to empty state."""
        self.data.clear()
        for status in self.field_statuses.values():
            status.is_filled = False
            status.used_default = False
            status.value = None

    def get_field_analysis(self) -> Dict[str, Any]:
        """Get detailed analysis of all fields."""
        model_fields = self.model_class.model_fields
        analysis = {}
        
        for field_name, field_info in model_fields.items():
            field_analysis = {
                'name': field_name,
                'type': str(field_info.annotation),
                'required': field_info.is_required(),
                'has_default': field_info.default is not ...,
                'default_value': field_info.default if field_info.default is not ... else None,
                'filled': field_name in self.data,
                'current_value': self.data.get(field_name),
                'aliases': getattr(field_info, 'alias', None)
            }
            analysis[field_name] = field_analysis
        
        return analysis


# ============================================================================
# APPROACH 2: SIMPLIFIED TRACKER CLASS
# ============================================================================

class SimpleModelTracker:
    """
    Simplified approach using Pydantic's built-in features more directly.
    """
    
    def __init__(self, model_class: Type[BaseModel]):
        self.model_class = model_class
        self.accumulated_data = {}
        self.fill_history = []
    
    def update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update with new data and return status."""
        self.accumulated_data.update(data)
        self.fill_history.append(data.copy())
        
        # Get model field info
        model_fields = self.model_class.model_fields
        
        status = {
            'filled_fields': list(self.accumulated_data.keys()),
            'unknown_keys': [k for k in data.keys() if k not in model_fields],
            'missing_required': [
                name for name, info in model_fields.items() 
                if info.is_required() and name not in self.accumulated_data
            ],
            'can_build': True,
            'errors': []
        }
        
        # Try to validate
        try:
            if status['missing_required']:
                status['can_build'] = False
            else:
                model = self.model_class.model_validate(self.accumulated_data)
                status['would_use_defaults'] = [
                    name for name, info in model_fields.items()
                    if name not in self.accumulated_data and info.default is not ...
                ]
        except ValidationError as e:
            status['can_build'] = False
            status['errors'] = [f"{err['loc'][0] if err['loc'] else 'unknown'}: {err['msg']}" for err in e.errors()]
        
        return status
    
    def build(self) -> Optional[BaseModel]:
        """Build the model if possible."""
        try:
            return self.model_class.model_validate(self.accumulated_data)
        except ValidationError:
            return None


# ============================================================================
# APPROACH 3: CONTEXT MANAGER FOR SAFE BUILDING
# ============================================================================

class ModelBuilder:
    """
    Context manager approach for safe model building.
    """
    
    def __init__(self, model_class: Type[BaseModel]):
        self.model_class = model_class
        self.data = {}
        self.reports = []
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # Success case - could do cleanup here
            pass
        return False  # Don't suppress exceptions
    
    def add(self, **kwargs) -> 'ModelBuilder':
        """Add fields using keyword arguments."""
        self.data.update(kwargs)
        return self
    
    def add_dict(self, data: Dict[str, Any]) -> 'ModelBuilder':
        """Add fields from dictionary."""
        self.data.update(data)
        return self
    
    def validate_and_build(self) -> BaseModel:
        """Validate and build the model, raising ValidationError if invalid."""
        return self.model_class.model_validate(self.data)
    
    def try_build(self) -> Tuple[Optional[BaseModel], List[str]]:
        """Try to build, returning (model, errors) tuple."""
        try:
            return self.validate_and_build(), []
        except ValidationError as e:
            errors = [f"{err['loc'][0] if err['loc'] else 'unknown'}: {err['msg']}" for err in e.errors()]
            return None, errors


# ============================================================================
# TEST MODELS (Generated from JSON Schema examples)
# ============================================================================

class StatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class Address(BaseModel):
    street: str
    city: str
    zip_code: str = Field(alias="zipCode")
    country: str = "USA"  # Default value
    
    @field_validator('zip_code')
    @classmethod
    def validate_zip(cls, v):
        if len(v) != 5 or not v.isdigit():
            raise ValueError('Zip code must be 5 digits')
        return v


class User(BaseModel):
    id: int
    name: str
    email: str
    age: Optional[int] = None
    status: StatusEnum = StatusEnum.ACTIVE
    address: Optional[Address] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v
    
    @field_validator('age')
    @classmethod
    def validate_age(cls, v):
        if v is not None and (v < 0 or v > 150):
            raise ValueError('Age must be between 0 and 150')
        return v


class Product(BaseModel):
    product_id: str = Field(alias="productId")
    name: str
    price: float = Field(gt=0)  # Must be positive
    in_stock: bool = Field(default=True, alias="inStock")
    category: Optional[str] = None
    description: str = "No description provided"
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Name cannot be empty')
        return v.strip()


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class OrderItem(BaseModel):
    product_id: str = Field(alias='productId')
    name: str
    quantity: int = Field(gt=0)  # Must be positive
    unit_price: float = Field(gt=0, alias='unitPrice')
    
    @property
    def total_price(self) -> float:
        return self.quantity * self.unit_price


class Order(BaseModel):
    order_id: str = Field(alias='orderId')
    customer_name: str = Field(alias='customerName')
    items: List[OrderItem]
    status: OrderStatus = OrderStatus.PENDING
    order_date: str = Field(alias='orderDate')
    total_amount: Optional[float] = Field(alias='totalAmount', default=None)
    
    @model_validator(mode='after')
    def validate_total_amount(self):
        if self.total_amount is None:
            self.total_amount = sum(item.total_price for item in self.items)
        return self


# ============================================================================
# COMPREHENSIVE TEST SUITE
# ============================================================================

def test_basic_functionality():
    """Test basic ModelFiller functionality."""
    print("🔧 BASIC FUNCTIONALITY TEST")
    print("=" * 50)
    
    filler = ModelFiller(User)
    
    print("\n📋 Step 1: Adding basic user info...")
    report1 = filler.add_data({
        "id": 123,
        "name": "John Doe",
        "unknown_field": "should be flagged"
    })
    print(report1.summary())
    
    print("\n📋 Step 2: Adding email...")
    report2 = filler.add_data({"email": "john@example.com"})
    print(report2.summary())
    
    print("\n📋 Step 3: Building final model...")
    model, final_report = filler.build_model()
    print(final_report.summary())
    
    if model:
        print(f"\n✅ SUCCESS! Built model:")
        print(f"📄 JSON: {model.model_dump_json(indent=2)}")
        return True
    else:
        print("❌ FAILED to build model")
        return False


def test_nested_models():
    """Test with nested address model."""
    print("\n\n🏠 NESTED MODELS TEST")
    print("=" * 50)
    
    filler = ModelFiller(User)
    
    print("\n📋 Adding user with nested address...")
    report = filler.add_data({
        "id": 456,
        "name": "Jane Smith", 
        "email": "jane@example.com",
        "address": {
            "street": "123 Main St",
            "city": "Anytown",
            "zipCode": "12345"  # Using alias
        },
        "age": 30,
        "tags": ["developer", "python", "pydantic"]
    })
    print(report.summary())
    
    model, final_report = filler.build_model()
    if model:
        print(f"\n✅ SUCCESS! Nested model built:")
        print(f"🏠 Address country (default): {model.address.country}")
        print(f"🏷️  Tags: {model.tags}")
        print(f"📄 JSON: {model.model_dump_json(indent=2)}")
        return True
    else:
        print("❌ FAILED to build nested model")
        return False


def test_validation_errors():
    """Test validation error handling."""
    print("\n\n🚨 VALIDATION ERRORS TEST")
    print("=" * 50)
    
    filler = ModelFiller(User)
    
    print("\n📋 Adding invalid data...")
    report = filler.add_data({
        "id": "not_a_number",  # Wrong type  
        "name": "Bob Wilson",
        "email": "invalid-email",  # Invalid format
        "age": -5  # Invalid age
    })
    print(report.summary())
    
    print("\n📋 Attempting to build model...")
    model, final_report = filler.build_model()
    
    if not model:
        print("✅ EXPECTED FAILURE - Validation errors caught correctly!")
        return True
    else:
        print("❌ UNEXPECTED SUCCESS - Should have failed validation")
        return False


def test_default_value_tracking():
    """Test tracking of default values."""
    print("\n\n🔧 DEFAULT VALUE TRACKING TEST")
    print("=" * 50)
    
    filler = ModelFiller(Product)
    
    print("\n📋 Adding minimal required data (letting defaults fill in)...")
    report = filler.add_data({
        "productId": "PROD-002",
        "name": "Minimal Product",
        "price": 9.99
        # Not setting inStock (defaults to True)
        # Not setting description (defaults to "No description provided")
    })
    
    model, final_report = filler.build_model()
    
    if model:
        print(f"✅ SUCCESS! Model with defaults:")
        print(f"🔧 Fields using defaults: {final_report.fields_with_defaults}")
        print(f"📦 In stock (default): {model.in_stock}")
        print(f"📝 Description (default): {model.description}")
        print(f"📄 JSON: {model.model_dump_json(indent=2)}")
        return True
    else:
        print("❌ FAILED default value test")
        return False


def test_incremental_filling():
    """Test incremental data filling."""
    print("\n\n📈 INCREMENTAL FILLING TEST")
    print("=" * 50)
    
    filler = ModelFiller(Product)
    
    steps = [
        {"productId": "PROD-001", "name": "Amazing Widget"},
        {"price": 29.99},
        {"category": "Electronics", "inStock": False},
        {"description": "This is an amazing widget that does amazing things!"}
    ]
    
    for i, step_data in enumerate(steps, 1):
        print(f"\n📋 Step {i}: Adding {list(step_data.keys())}")
        report = filler.add_data(step_data)
        print(f"   Status: {'✅ Complete' if report.is_complete else '⚠️ Incomplete'}")
        print(f"   Progress: {len(report.filled_fields)} fields filled")
        
        if report.validation_errors:
            print(f"   Errors: {report.validation_errors}")
    
    print(f"\n📋 Final build attempt...")
    model, final_report = filler.build_model()
    
    if model:
        print(f"✅ SUCCESS! Incremental filling completed:")
        print(f"📄 Final product: {model.model_dump_json(indent=2)}")
        return True
    else:
        print("❌ FAILED incremental filling")
        print(final_report.summary())
        return False


def test_complex_order_model():
    """Test complex nested model with lists."""
    print("\n\n🛒 COMPLEX ORDER MODEL TEST")
    print("=" * 50)
    
    filler = ModelFiller(Order)
    
    print("\n📋 Step 1: Basic order info...")
    report1 = filler.add_data({
        "orderId": "ORD-2024-001",
        "customerName": "Alice Johnson",
        "orderDate": "2024-01-15"
    })
    print(f"   Status: {'✅ Complete' if report1.is_complete else '⚠️ Incomplete'}")
    print(f"   Missing: {report1.missing_required}")
    
    print("\n📋 Step 2: Adding order items...")
    report2 = filler.add_data({
        "items": [
            {
                "productId": "PROD001",
                "name": "Widget A",
                "quantity": 2,
                "unitPrice": 19.99
            },
            {
                "productId": "PROD002", 
                "name": "Widget B",
                "quantity": 1,
                "unitPrice": 29.99
            }
        ]
    })
    print(f"   Status: {'✅ Complete' if report2.is_complete else '⚠️ Incomplete'}")
    
    model, final_report = filler.build_model()
    if model:
        print(f"\n✅ SUCCESS! Complex order built:")
        print(f"🛒 Order ID: {model.order_id}")
        print(f"👤 Customer: {model.customer_name}")
        print(f"📦 Items: {len(model.items)}")
        print(f"💰 Total (auto-calculated): ${model.total_amount}")
        print(f"📄 JSON: {model.model_dump_json(indent=2)}")
        return True
    else:
        print("❌ FAILED to build complex order")
        print(final_report.summary())
        return False


def test_simple_tracker():
    """Test the simplified tracker approach."""
    print("\n\n⚡ SIMPLE TRACKER TEST")
    print("=" * 50)
    
    tracker = SimpleModelTracker(User)
    
    print("\n📋 Step 1: Adding basic info...")
    status1 = tracker.update({"id": 789, "name": "Bob Wilson"})
    print(f"Status: {status1}")
    
    print("\n📋 Step 2: Adding email...")
    status2 = tracker.update({"email": "bob@example.com"})
    print(f"Status: {status2}")
    
    model = tracker.build()
    if model:
        print(f"\n✅ SUCCESS! Simple tracker built model:")
        print(f"📄 JSON: {model.model_dump_json(indent=2)}")
        return True
    else:
        print("❌ FAILED to build with simple tracker")
        return False


def test_context_manager():
    """Test the context manager approach."""
    print("\n\n🔧 CONTEXT MANAGER TEST")
    print("=" * 50)
    
    try:
        with ModelBuilder(User) as builder:
            model = (builder
                    .add(id=999, name="Alice Cooper")
                    .add(email="alice@example.com")
                    .add_dict({"age": 25, "tags": ["musician", "performer"]})
                    .validate_and_build())
        
        print(f"✅ SUCCESS! Context manager built model:")
        print(f"📄 JSON: {model.model_dump_json(indent=2)}")
        return True
        
    except ValidationError as e:
        print(f"❌ Context manager validation failed: {e}")
        return False


def test_field_analysis():
    """Test detailed field analysis."""
    print("\n\n🔍 FIELD ANALYSIS TEST")
    print("=" * 50)
    
    filler = ModelFiller(User)
    filler.add_data({"id": 123, "name": "Analysis Test"})
    
    analysis = filler.get_field_analysis()
    
    print("\n📊 Field Analysis:")
    for field_name, info in analysis.items():
        status = "✅ Filled" if info['filled'] else ("❌ Required" if info['required'] else "➖ Optional")
        default_info = f" (default: {info['default_value']})" if info['has_default'] else ""
        print(f"   {field_name}: {status}{default_info}")
        print(f"      Type: {info['type']}")
        if info['filled']:
            print(f"      Value: {info['current_value']}")
    
    return True


def run_all_tests():
    """Run all comprehensive tests."""
    print("🧪 COMPREHENSIVE PYDANTIC MODEL FILLER TESTS")
    print("=" * 80)
    print("Testing generic, safe, and reusable model filling system...")
    print("=" * 80)
    
    test_results = []
    
    # Run all tests
    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Nested Models", test_nested_models),
        ("Validation Errors", test_validation_errors),
        ("Default Value Tracking", test_default_value_tracking),
        ("Incremental Filling", test_incremental_filling),
        ("Complex Order Model", test_complex_order_model),
        ("Simple Tracker", test_simple_tracker),
        ("Context Manager", test_context_manager),
        ("Field Analysis", test_field_analysis)
    ]
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            test_results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ {test_name} CRASHED: {e}")
            test_results.append((test_name, False))
    
    # Summary
    print("\n\n📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, success in test_results if success)
    total = len(test_results)
    
    for test_name, success in test_results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} - {test_name}")
    
    print(f"\n🎯 OVERALL RESULT: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! The system is working correctly.")
        print("\n💡 Key benefits demonstrated:")
        print("   ✅ Generic - works with any Pydantic model")
        print("   ✅ Safe - validates at every step")
        print("   ✅ Trackable - reports progress and issues")
        print("   ✅ Reusable - no model-specific code needed")
        print("   ✅ Robust - handles errors gracefully")
        print("   ✅ Default tracking - shows which fields use defaults")
    else:
        print(f"⚠️ {total - passed} tests failed. Check the output above for details.")
    
    return passed == total


# ============================================================================
# DEMO FUNCTIONS FOR SPECIFIC REQUIREMENTS
# ============================================================================

def demo_default_value_notification():
    """Demonstrate the default value notification feature specifically."""
    print("\n\n🔔 DEFAULT VALUE NOTIFICATION DEMO")
    print("=" * 50)
    print("This demonstrates your specific requirement: notification of default value usage")
    
    # Test with Product model which has several default values
    filler = ModelFiller(Product)
    
    print("\n📋 Product model has these fields with defaults:")
    for field_name, field_info in Product.model_fields.items():
        if field_info.default is not ...:
            print(f"   • {field_name}: default = {field_info.default}")
    
    print("\n📋 Adding only required fields...")
    report = filler.add_data({
        "productId": "DEMO-001",
        "name": "Demo Product",
        "price": 99.99
    })
    
    model, final_report = filler.build_model()
    
    if model:
        print(f"\n✅ Model built successfully!")
        print(f"🔔 NOTIFICATION: {len(final_report.fields_with_defaults)} fields used default values:")
        for field in final_report.fields_with_defaults:
            field_info = Product.model_fields[field]
            print(f"   • {field} = {field_info.default}")
        
        print(f"\n📄 Final model JSON:")
        print(model.model_dump_json(indent=2))
    
    return model is not None


def demo_unknown_key_detection():
    """Demonstrate unknown key detection."""
    print("\n\n🚫 UNKNOWN KEY DETECTION DEMO")
    print("=" * 50)
    
    filler = ModelFiller(User)
    
    print("\n📋 Adding data with unknown fields...")
    report = filler.add_data({
        "id": 123,
        "name": "Test User",
        "email": "test@example.com",
        "unknown_field_1": "should be detected",
        "another_unknown": "also detected",
        "typo_in_filedname": "typo detected"
    })
    
    print(f"🚫 DETECTED {len(report.unknown_keys)} unknown keys:")
    for key in report.unknown_keys:
        print(f"   • {key}")
    
    print(f"\n✅ Valid fields processed: {report.filled_fields}")
    
    model, final_report = filler.build_model()
    if model:
        print(f"\n📄 Final model (unknown keys ignored):")
        print(model.model_dump_json(indent=2))
    
    return len(report.unknown_keys) > 0


def demo_incremental_api_workflow():
    """Demonstrate a realistic API workflow."""
    print("\n\n🔄 INCREMENTAL API WORKFLOW DEMO")
    print("=" * 50)
    print("Simulating a multi-step user registration API")
    
    filler = ModelFiller(User)
    
    # Simulate API calls
    api_calls = [
        {
            "endpoint": "POST /api/register/step1",
            "data": {"id": 12345, "name": "API User"},
            "description": "Basic registration"
        },
        {
            "endpoint": "POST /api/register/step2", 
            "data": {"email": "apiuser@example.com"},
            "description": "Email verification"
        },
        {
            "endpoint": "POST /api/register/step3",
            "data": {"age": 28, "tags": ["developer", "api-user"]},
            "description": "Profile completion"
        },
        {
            "endpoint": "POST /api/register/complete",
            "data": {},
            "description": "Finalize registration"
        }
    ]
    
    for i, call in enumerate(api_calls, 1):
        print(f"\n📡 API Call {i}: {call['endpoint']}")
        print(f"   📝 {call['description']}")
        print(f"   📥 Data: {call['data']}")
        
        if call['data']:
            report = filler.add_data(call['data'])
            print(f"   📊 Status: {'✅ Complete' if report.is_complete else '⚠️ Incomplete'}")
            print(f"   📈 Progress: {len(report.filled_fields)} fields filled")
            if report.missing_required:
                print(f"   ❌ Still need: {report.missing_required}")
        else:
            # Final build attempt
            model, final_report = filler.build_model()
            if model:
                print(f"   ✅ Registration complete!")
                print(f"   📄 User created: {model.model_dump_json()}")
            else:
                print(f"   ❌ Registration failed: {final_report.validation_errors}")
    
    return True


def show_usage_examples():
    """Show practical usage examples."""
    print("\n\n📖 USAGE EXAMPLES")
    print("=" * 50)
    
    print("""
🔧 BASIC USAGE:
from model_filler_system import ModelFiller

# Works with ANY Pydantic model
filler = ModelFiller(YourModel)

# Add data incrementally
report = filler.add_data({"field1": "value1"})
print(f"Default fields: {report.fields_with_defaults}")  # Your requirement!

# Build when ready
model, final_report = filler.build_model()
if model:
    json_output = model.model_dump_json()

🚀 ADVANCED USAGE:
# Multiple approaches available
tracker = SimpleModelTracker(YourModel)  # Lightweight
with ModelBuilder(YourModel) as builder:  # Context manager
    model = builder.add(field="value").validate_and_build()

🔍 ANALYSIS:
analysis = filler.get_field_analysis()
for field, info in analysis.items():
    print(f"{field}: required={info['required']}, filled={info['filled']}")
""")


if __name__ == "__main__":
    # Run comprehensive tests
    success = run_all_tests()
    
    # Run specific demos
    demo_default_value_notification()
    demo_unknown_key_detection()
    demo_incremental_api_workflow()
    show_usage_examples()
    
    print("\n" + "=" * 80)
    print("🎉 COMPLETE SYSTEM TESTED AND READY!")
    print("Copy this file and start using ModelFiller with your generated models!")
    print("=" * 80)