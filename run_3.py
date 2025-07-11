"""
Quick Start Example - Essential Usage

This is the minimal example to get started immediately.
Copy and run this to see the core functionality.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

# Import the ModelFiller (you would import this from the main module)
# For this example, we'll include a simplified version
import json
from dataclasses import dataclass, field as dc_field
from typing import Set


@dataclass 
class FillingReport:
    filled_fields: Set[str] = dc_field(default_factory=set)
    missing_required: Set[str] = dc_field(default_factory=set)
    fields_with_defaults: Set[str] = dc_field(default_factory=set)
    unknown_keys: Set[str] = dc_field(default_factory=set)
    validation_errors: List[str] = dc_field(default_factory=list)
    is_complete: bool = False


class ModelFiller:
    def __init__(self, model_class):
        self.model_class = model_class
        self.data = {}
    
    def add_data(self, data):
        report = FillingReport()
        
        # Track unknown keys
        model_fields = set(self.model_class.model_fields.keys())
        report.unknown_keys = set(data.keys()) - model_fields
        
        # Add valid data
        for key, value in data.items():
            if key in model_fields:
                self.data[key] = value
                report.filled_fields.add(key)
        
        # Check what's missing
        for field_name, field_info in self.model_class.model_fields.items():
            if field_info.is_required() and field_name not in self.data:
                report.missing_required.add(field_name)
        
        # Try to build and check defaults
        if not report.missing_required:
            try:
                model = self.model_class.model_validate(self.data)
                # Check which fields used defaults
                for field_name, field_info in self.model_class.model_fields.items():
                    if (field_name not in self.data and 
                        field_info.default is not ... and 
                        hasattr(model, field_name)):
                        report.fields_with_defaults.add(field_name)
                report.is_complete = True
            except Exception as e:
                report.validation_errors.append(str(e))
        
        return report
    
    def build_model(self):
        try:
            return self.model_class.model_validate(self.data), None
        except Exception as e:
            return None, str(e)


# ============================================================================
# EXAMPLE MODELS (Your generated models would look like this)
# ============================================================================

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class User(BaseModel):
    """Example user model - could be generated from JSON Schema"""
    id: int
    name: str  
    email: str
    age: Optional[int] = None
    status: UserStatus = UserStatus.ACTIVE  # Default value
    tags: List[str] = Field(default_factory=list)  # Default empty list


class Product(BaseModel):
    """Example product model - could be generated from JSON Schema"""
    product_id: str = Field(alias="productId")
    name: str
    price: float
    in_stock: bool = Field(default=True, alias="inStock")  # Default True
    description: str = "No description provided"  # Default description


# ============================================================================
# QUICK START EXAMPLES
# ============================================================================

def example_1_basic_usage():
    """Most basic usage - fill and build a user."""
    print("📋 EXAMPLE 1: Basic Usage")
    print("-" * 30)
    
    # Create filler for User model
    filler = ModelFiller(User)
    
    # Add data step by step
    print("Step 1: Add basic info")
    report1 = filler.add_data({"id": 123, "name": "John Doe"})
    print(f"  Filled: {report1.filled_fields}")
    print(f"  Missing required: {report1.missing_required}")
    print(f"  Complete: {report1.is_complete}")
    
    print("\nStep 2: Add email")
    report2 = filler.add_data({"email": "john@example.com"})
    print(f"  Filled: {report2.filled_fields}")
    print(f"  Complete: {report2.is_complete}")
    print(f"  🔧 Using defaults: {report2.fields_with_defaults}")  # Your requirement!
    
    # Build final model
    model, error = filler.build_model()
    if model:
        print(f"\n✅ Success! JSON: {model.model_dump_json(indent=2)}")
    else:
        print(f"❌ Error: {error}")


def example_2_default_tracking():
    """Focus on default value tracking (your specific requirement)."""
    print("\n\n📋 EXAMPLE 2: Default Value Tracking")
    print("-" * 30)
    
    filler = ModelFiller(Product)
    
    # Only add required fields, let others use defaults
    print("Adding only required fields...")
    report = filler.add_data({
        "productId": "PROD-001",
        "name": "Amazing Widget", 
        "price": 29.99
        # NOT setting inStock (will default to True)
        # NOT setting description (will default to "No description provided")
    })
    
    print(f"🔧 Fields using defaults: {report.fields_with_defaults}")
    
    model, error = filler.build_model()
    if model:
        print(f"✅ Built with defaults:")
        print(f"  In stock: {model.in_stock} (default)")
        print(f"  Description: '{model.description}' (default)")
        print(f"\n📄 JSON: {model.model_dump_json(indent=2)}")


def example_3_unknown_keys():
    """Show unknown key detection."""
    print("\n\n📋 EXAMPLE 3: Unknown Key Detection")
    print("-" * 30)
    
    filler = ModelFiller(User)
    
    print("Adding data with unknown fields...")
    report = filler.add_data({
        "id": 456,
        "name": "Jane Smith",
        "email": "jane@example.com",
        "unknown_field": "this will be flagged",
        "typo_in_name": "also flagged"
    })
    
    print(f"✅ Valid fields: {report.filled_fields}")
    print(f"🚫 Unknown keys: {report.unknown_keys}")
    
    model, error = filler.build_model()
    if model:
        print(f"📄 Final model (unknowns ignored): {model.model_dump_json()}")


def example_4_validation_errors():
    """Show validation error handling."""
    print("\n\n📋 EXAMPLE 4: Validation Errors")
    print("-" * 30)
    
    filler = ModelFiller(User)
    
    print("Adding invalid data...")
    report = filler.add_data({
        "id": "not_a_number",  # Wrong type
        "name": "Test User",
        "email": "invalid-email-format"  # Invalid email
    })
    
    print(f"❌ Validation errors: {report.validation_errors}")
    print(f"Complete: {report.is_complete}")
    
    model, error = filler.build_model()
    if not model:
        print(f"❌ Build failed as expected: {error}")


def example_5_incremental_filling():
    """Show incremental filling like an API workflow."""
    print("\n\n📋 EXAMPLE 5: Incremental API-like Filling")
    print("-" * 30)
    
    filler = ModelFiller(User)
    
    # Simulate multiple API calls
    steps = [
        {"step": "registration", "data": {"id": 789, "name": "API User"}},
        {"step": "email_verification", "data": {"email": "api@example.com"}},
        {"step": "profile_completion", "data": {"age": 25, "tags": ["developer"]}}
    ]
    
    for step_info in steps:
        print(f"\n{step_info['step']}: Adding {step_info['data']}")
        report = filler.add_data(step_info['data'])
        print(f"  Status: {'✅ Complete' if report.is_complete else '⚠️ Incomplete'}")
        if report.missing_required:
            print(f"  Still need: {report.missing_required}")
    
    model, error = filler.build_model()
    if model:
        print(f"\n🎉 Final result: {model.model_dump_json(indent=2)}")


def run_quickstart_examples():
    """Run all quickstart examples."""
    print("🚀 PYDANTIC MODEL FILLER - QUICK START EXAMPLES")
    print("=" * 60)
    print("These examples show the core functionality you need.")
    print("=" * 60)
    
    example_1_basic_usage()
    example_2_default_tracking()  # Your specific requirement
    example_3_unknown_keys()
    example_4_validation_errors()
    example_5_incremental_filling()
    
    print("\n" + "=" * 60)
    print("✅ ALL EXAMPLES COMPLETED!")
    print("\n💡 KEY TAKEAWAYS:")
    print("• Works with ANY Pydantic model (no custom code per model)")
    print("• Tracks which fields use default values (your requirement!)")
    print("• Detects unknown keys in input data")
    print("• Validates at every step")
    print("• Perfect for multi-step forms and APIs")
    print("• Outputs clean, valid JSON")
    print("\n🔧 USAGE:")
    print("1. filler = ModelFiller(YourModel)")
    print("2. report = filler.add_data(data_dict)")
    print("3. model, error = filler.build_model()")
    print("=" * 60)


if __name__ == "__main__":
    run_quickstart_examples()