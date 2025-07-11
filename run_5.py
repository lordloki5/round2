"""
Practical Testing Guide: pydantic-partial

This script shows you exactly how to install and test pydantic-partial
alongside our custom ModelFiller solution.

INSTALLATION:
pip install pydantic-partial

Then run this script to see both approaches in action!
"""

import json
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ValidationError
from enum import Enum

# First, let's try to import pydantic-partial
print("🔧 TESTING PYDANTIC-PARTIAL INSTALLATION")
print("=" * 50)

try:
    from pydantic_partial import create_partial_model, PartialModelMixin
    print("✅ pydantic-partial successfully imported!")
    PYDANTIC_PARTIAL_AVAILABLE = True
except ImportError as e:
    print("❌ pydantic-partial not found!")
    print(f"   Error: {e}")
    print("   💡 Install with: pip install pydantic-partial")
    print("   Then re-run this script.")
    PYDANTIC_PARTIAL_AVAILABLE = False


# Define test models
class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class User(BaseModel):
    id: int
    name: str
    email: str
    age: Optional[int] = None
    status: UserStatus = UserStatus.ACTIVE
    is_verified: bool = False
    tags: List[str] = Field(default_factory=list)


class UserWithMixin(PartialModelMixin, BaseModel):
    id: int
    name: str
    email: str
    age: Optional[int] = None
    status: UserStatus = UserStatus.ACTIVE
    is_verified: bool = False
    tags: List[str] = Field(default_factory=list)


def test_pydantic_partial_installation():
    """Test that pydantic-partial works correctly."""
    if not PYDANTIC_PARTIAL_AVAILABLE:
        print("\n❌ Cannot test pydantic-partial - not installed")
        return False
    
    print("\n🧪 TESTING PYDANTIC-PARTIAL FUNCTIONALITY")
    print("-" * 50)
    
    try:
        # Test 1: create_partial_model function
        print("📋 Test 1: create_partial_model function")
        UserPartial = create_partial_model(User)
        
        # This should work - partial model with only some fields
        partial_user = UserPartial(name="John Doe", email="john@example.com")
        print(f"   ✅ Partial user created: {partial_user.model_dump()}")
        
        # Test 2: PartialModelMixin
        print("\n📋 Test 2: PartialModelMixin")
        UserPartialMixin = UserWithMixin.model_as_partial()
        partial_user2 = UserPartialMixin(id=123)
        print(f"   ✅ Mixin partial created: {partial_user2.model_dump()}")
        
        # Test 3: Selective partial fields
        print("\n📋 Test 3: Selective partial fields")
        UserPartialSelective = create_partial_model(User, 'name', 'email', 'age')
        partial_user3 = UserPartialSelective(id=456, is_verified=True)  # id and is_verified still required
        print(f"   ✅ Selective partial: {partial_user3.model_dump()}")
        
        # Test 4: exclude_unset for PATCH operations
        print("\n📋 Test 4: exclude_unset for PATCH operations")
        patch_data = UserPartial(age=30, tags=["developer"])
        patch_dict = patch_data.model_dump(exclude_unset=True)
        print(f"   ✅ PATCH data (exclude_unset): {patch_dict}")
        
        print("\n✅ All pydantic-partial tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ pydantic-partial test failed: {e}")
        return False


def test_realistic_patch_api():
    """Show realistic PATCH API usage with pydantic-partial."""
    if not PYDANTIC_PARTIAL_AVAILABLE:
        return
    
    print("\n🌐 REALISTIC PATCH API EXAMPLE")
    print("-" * 50)
    
    # Simulate existing user in database
    existing_user = User(
        id=123,
        name="Alice Johnson",
        email="alice@example.com",
        age=28,
        status=UserStatus.ACTIVE,
        is_verified=True,
        tags=["developer", "python"]
    )
    print(f"📋 Existing user in DB:")
    print(f"   {existing_user.model_dump_json(indent=2)}")
    
    # Create partial model for PATCH requests
    UserPatch = create_partial_model(User)
    
    # Simulate PATCH request payload
    patch_requests = [
        {"description": "Update age", "data": {"age": 29}},
        {"description": "Add tags", "data": {"tags": ["developer", "python", "senior"]}},
        {"description": "Change status", "data": {"status": "inactive", "is_verified": False}},
        {"description": "Invalid data", "data": {"age": "not_a_number"}},  # Should fail validation
    ]
    
    for i, patch_request in enumerate(patch_requests, 1):
        print(f"\n📡 PATCH Request {i}: {patch_request['description']}")
        print(f"   Payload: {patch_request['data']}")
        
        try:
            # Validate PATCH data
            patch_model = UserPatch(**patch_request['data'])
            patch_dict = patch_model.model_dump(exclude_unset=True)
            print(f"   ✅ Validation passed: {patch_dict}")
            
            # Apply patch to existing user
            updated_data = existing_user.model_dump()
            updated_data.update(patch_dict)
            updated_user = User(**updated_data)
            
            print(f"   📄 Updated user: {updated_user.model_dump()}")
            existing_user = updated_user  # Update for next iteration
            
        except ValidationError as e:
            print(f"   ❌ Validation failed: {str(e).split('validation error')[0]}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")


def compare_with_modelfiller():
    """Compare pydantic-partial with our ModelFiller approach."""
    print("\n📊 SIDE-BY-SIDE COMPARISON")
    print("=" * 70)
    
    # Our simple ModelFiller for comparison
    class SimpleModelFiller:
        def __init__(self, model_class):
            self.model_class = model_class
            self.data = {}
            self.history = []
        
        def add_data(self, data):
            self.data.update(data)
            self.history.append(data.copy())
            
            # Check if we can build a complete model
            try:
                model = self.model_class.model_validate(self.data)
                return {"success": True, "model": model, "steps": len(self.history)}
            except ValidationError as e:
                missing_fields = []
                for error in e.errors():
                    if error['type'] == 'missing':
                        missing_fields.append(error['loc'][0])
                return {"success": False, "missing_fields": missing_fields, "steps": len(self.history)}
    
    print("🔧 Scenario: Creating a user with incremental data")
    print("-" * 70)
    
    # Test data sequence
    data_steps = [
        {"step": "Basic info", "data": {"name": "Bob Wilson"}},
        {"step": "Contact", "data": {"email": "bob@example.com"}},
        {"step": "Identity", "data": {"id": 789}},
        {"step": "Profile", "data": {"age": 35, "tags": ["manager"]}}
    ]
    
    # Test with ModelFiller
    print("\n📋 APPROACH 1: ModelFiller (Incremental Building)")
    filler = SimpleModelFiller(User)
    
    for step_info in data_steps:
        result = filler.add_data(step_info['data'])
        status = "✅ Complete" if result['success'] else f"⚠️ Missing: {result.get('missing_fields', [])}"
        print(f"   {step_info['step']}: {step_info['data']} → {status}")
    
    if result['success']:
        print(f"   🎉 Final model: {result['model'].model_dump_json()}")
    
    # Test with pydantic-partial
    if PYDANTIC_PARTIAL_AVAILABLE:
        print("\n📋 APPROACH 2: pydantic-partial (All-at-once with optional fields)")
        UserPartial = create_partial_model(User)
        
        # Collect all data
        all_data = {}
        for step_info in data_steps:
            all_data.update(step_info['data'])
            
            try:
                partial_model = UserPartial(**all_data)
                print(f"   After {step_info['step']}: ✅ Valid partial model")
                print(f"      Data: {partial_model.model_dump(exclude_unset=True)}")
            except ValidationError as e:
                print(f"   After {step_info['step']}: ❌ Validation error")
    
    print("\n💡 COMPARISON INSIGHTS:")
    print("   🔧 ModelFiller: Perfect for step-by-step building with progress tracking")
    print("   🔧 pydantic-partial: Perfect for optional field handling and PATCH APIs")
    print("   🤝 Both: Can complement each other in a complete API solution")


def show_integration_example():
    """Show how both approaches can work together."""
    if not PYDANTIC_PARTIAL_AVAILABLE:
        return
    
    print("\n🤝 INTEGRATION EXAMPLE: Using Both Together")
    print("-" * 70)
    
    print("📋 Scenario: API with both creation (POST) and update (PATCH) endpoints")
    
    # Simulate POST endpoint (creation) using incremental approach
    print("\n1️⃣ POST /users (Create user with ModelFiller)")
    
    class APIModelFiller:
        def __init__(self, model_class):
            self.model_class = model_class
            self.data = {}
        
        def add_step_data(self, data):
            self.data.update(data)
            try:
                model = self.model_class.model_validate(self.data)
                return {"complete": True, "model": model}
            except ValidationError:
                required_fields = [name for name, info in self.model_class.model_fields.items() if info.is_required()]
                missing = [field for field in required_fields if field not in self.data]
                return {"complete": False, "missing_required": missing}
    
    # Multi-step creation
    filler = APIModelFiller(User)
    creation_steps = [
        {"id": 999, "name": "Integration User"},
        {"email": "integration@example.com"}
    ]
    
    for step_data in creation_steps:
        result = filler.add_step_data(step_data)
        print(f"   Added: {step_data}")
        print(f"   Status: {'✅ Ready to create' if result['complete'] else f'⚠️ Missing: {result.get("missing_required", [])}'}")
    
    if result['complete']:
        created_user = result['model']
        print(f"   ✅ User created: {created_user.model_dump()}")
    
    # Simulate PATCH endpoint (update) using pydantic-partial
    print("\n2️⃣ PATCH /users/999 (Update user with pydantic-partial)")
    
    UserPatch = create_partial_model(User)
    update_data = {"age": 32, "status": "active", "tags": ["integration", "api"]}
    
    try:
        patch_model = UserPatch(**update_data)
        validated_updates = patch_model.model_dump(exclude_unset=True)
        print(f"   Update data: {update_data}")
        print(f"   ✅ Validated: {validated_updates}")
        
        # Apply updates
        final_data = created_user.model_dump()
        final_data.update(validated_updates)
        updated_user = User(**final_data)
        print(f"   ✅ Updated user: {updated_user.model_dump()}")
        
    except ValidationError as e:
        print(f"   ❌ Update validation failed: {e}")


def run_comprehensive_test():
    """Run all tests and comparisons."""
    print("🧪 COMPREHENSIVE pydantic-partial TESTING")
    print("=" * 80)
    
    # Test installation
    success = test_pydantic_partial_installation()
    
    if success:
        test_realistic_patch_api()
        compare_with_modelfiller()
        show_integration_example()
        
        print("\n" + "=" * 80)
        print("🎯 FINAL RECOMMENDATIONS")
        print("=" * 80)
        print("✅ pydantic-partial: Excellent for PATCH APIs and optional field handling")
        print("✅ Our ModelFiller: Perfect for incremental building and progress tracking")
        print("✅ Use together: Complete API solution with creation AND update capabilities")
        print("\n💡 Quick decision guide:")
        print("   • Need PATCH endpoint? → Use pydantic-partial")
        print("   • Need multi-step forms? → Use ModelFiller")  
        print("   • Need default tracking? → Use ModelFiller")
        print("   • Need both? → Use both together!")
        
    else:
        print("\n❌ Could not test pydantic-partial")
        print("💡 Install it with: pip install pydantic-partial")
        print("   Then re-run this script to see the comparison!")
    
    print("=" * 80)


if __name__ == "__main__":
    run_comprehensive_test()