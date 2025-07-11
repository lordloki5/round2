import json
from typing import Any, Dict, Type, List, Optional
from pydantic import BaseModel, ValidationError, TypeAdapter

# --- Example schema-generated models (replace with your own if needed) ---

class Pet(BaseModel):
    name: str
    age: int
    nickname: Optional[str] = None
    model_config = {"extra": "forbid"}

class Owner(BaseModel):
    name: str
    pets: List[Pet]
    status: int
    model_config = {"extra": "forbid"}


# --- Generic StepwiseModelFiller Implementation ---

class StepwiseModelFiller:
    def __init__(self, model_cls: Type[BaseModel]):
        self.model_cls = model_cls
        self.adapter = TypeAdapter(model_cls)
        self.partial_data: Dict[str, Any] = {}

    def fill(self, new_data: Dict[str, Any]) -> Dict[str, Any]:
        # Merge new data with current state
        combined = {**self.partial_data, **new_data}
        unknown_keys = set(new_data) - set(self.model_cls.model_fields)
        try:
            # Partial validation
            self.adapter.validate_python(
                combined, experimental_allow_partial=True
            )
            # Only update state if validation passes and no unknown keys
            if unknown_keys:
                raise ValidationError(
                    [
                        {
                            "type": "extra_forbidden",
                            "loc": [key],
                            "msg": "Extra inputs are not permitted",
                            "input": new_data[key],
                            "url": "https://errors.pydantic.dev/2.11/v/extra_forbidden"
                        }
                        for key in unknown_keys
                    ],
                    self.model_cls
                )
            self.partial_data = combined
            return {
                "success": True,
                "filled_fields": list(self.partial_data.keys()),
                "missing_required": [
                    k for k, f in self.model_cls.model_fields.items()
                    if f.is_required() and k not in self.partial_data
                ],
                "missing_optional": [
                    k for k, f in self.model_cls.model_fields.items()
                    if not f.is_required() and k not in self.partial_data
                ],
                "unknown_keys": list(unknown_keys),
                "errors": None
            }
        except ValidationError as e:
            return {
                "success": False,
                "filled_fields": list(self.partial_data.keys()),
                "missing_required": [
                    k for k, f in self.model_cls.model_fields.items()
                    if f.is_required() and k not in self.partial_data
                ],
                "missing_optional": [
                    k for k, f in self.model_cls.model_fields.items()
                    if not f.is_required() and k not in self.partial_data
                ],
                "unknown_keys": list(unknown_keys),
                "errors": e.errors()
            }

    def is_complete(self) -> bool:
        return all(
            k in self.partial_data
            for k, f in self.model_cls.model_fields.items() if f.is_required()
        )

    def to_json(self) -> str:
        if not self.is_complete():
            raise ValueError("Model is not fully filled")
        return self.model_cls(**self.partial_data).model_dump_json(indent=2)


# --- Test Cases with Pretty-Print Formatting ---

def test_stepwise_filling():
    filler = StepwiseModelFiller(Owner)

    # Step 1: Fill only 'name'
    result1 = filler.fill({"name": "Alice"})
    print(" \n\n Step 1: \n\n ", json.dumps(result1, indent=4))

    # Step 2: Fill 'pets'
    result2 = filler.fill({
        "pets": [{"name": "dog", "age": 2}]
    })
    print("\n\n Step 2: \n\n ", json.dumps(result2, indent=4))

    # Step 3: Fill 'status'
    result3 = filler.fill({"status": 200})
    print("\n\n Step 3:\n\n ", json.dumps(result3, indent=4))

    # Step 4: Try to fill unknown field
    result4 = filler.fill({"unknown_field": "oops"})
    print("\n\n Step 4:\n\n ", json.dumps(result4, indent=4))

    # Step 5: Try to output final JSON
    if filler.is_complete():
        print("\n\n Final JSON Output:\n", filler.to_json())
    else:
        print("\n\n  Model is not fully filled yet \n\n ")

if __name__ == "__main__":
    test_stepwise_filling()
