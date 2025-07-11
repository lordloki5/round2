# round2
I’m working with data models generated from JSON Schemas using datamodel-code-generator, and I want to build a generic, safe, and reusable system for populating these models in multiple steps.
# Track and report:
Which fields have been filled.
Which required/optional fields are still missing.
If any unknown or unexpected keys are present in the input.
Output a fully valid JSON representation of the final filled model.
Avoid writing custom fill functions for each new data model — the system should work with any schema-generated model dynamically.
Strong emphasis on data integrity and validation safety throughout the process.
#  Why:
The current approach requires writing boilerplate code to fill and validate each new model manually. I want to eliminate this redundancy and ensure that all generated data is consistent, schema-compliant, and traceable at every step.
#  Issues:
    (1) Few keys will have a default value also, but I should be notified which keys are taking their default value

# Goals:
Accept a generated Pydantic model (from the JSON Schema).
Allow partial filling of the model in multiple steps.
Ensure strict validation of each field as per the schema.
Generate me a python codes using different ways of doing this which does this and give few test cases with which I can directly run and test the approach


# Approach
    Approach 1: Using a wrapper class that tracks state

    Create a ModelFiller class that wraps any Pydantic model
    Track filled fields, defaults used, missing fields
    Support incremental updates
    Validate at each step

    Approach 2: Using Pydantic's built-in features more directly

    Leverage Pydantic's partial validation
    Use model_validate with strict mode
    Track changes using model differences

    Approach 3: Using a decorator/mixin approach

    Create a mixin that adds tracking capabilities to any model
    Use metaclass or inheritance