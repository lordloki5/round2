#!/bin/bash

# Check if exactly one argument (folder path) is provided
if [ $# -ne 1 ]; then
    echo "Usage: $0 <folder_path>"
    exit 1
fi

folder_path="$1"
models_dir="$folder_path/models"

# Create the 'models' directory if it doesn't exist
mkdir -p "$models_dir" || { echo "Error: Failed to create directory $models_dir"; exit 1; }

# Check if datamodel-codegen is installed
if ! command -v datamodel-codegen &> /dev/null; then
    echo "Error: datamodel-codegen not found. Please install it using 'pip install datamodel-code-generator'"
    exit 1
fi

# Iterate over each JSON file in the folder
for filename in "$folder_path"/*.json; do
    if [ -f "$filename" ]; then
        base_name=$(basename "$filename" .json)
        output_path="$models_dir/${base_name}.py"

        # Step 1: Generate standard Pydantic models using datamodel-code-generator
        if ! datamodel-codegen --input "$filename" --input-file-type jsonschema --output "$output_path"; then
            echo "Error: Failed to generate models for $filename"
            continue
        fi

        # Step 2: Check if the import for create_partial_model is already present
        if ! grep -q "from pydantic_partial import create_partial_model" "$output_path"; then
            # Find the last import line
            last_import_line=$(grep -n -E '^import |^from ' "$output_path" | tail -n 1 | cut -d: -f1)
            if [ -z "$last_import_line" ]; then
                # No imports found, insert at the beginning
                sed -i '' '1i\
from pydantic_partial import create_partial_model\
' "$output_path" || { echo "Error: Failed to insert import at beginning of $output_path"; continue; }
            else
                # Insert after the last import
                sed -i '' "${last_import_line}a\\
from pydantic_partial import create_partial_model\\
" "$output_path" || { echo "Error: Failed to insert import in $output_path"; continue; }
            fi
        fi

        # Step 3: Extract model names (classes inheriting from BaseModel)
        model_names=()
        while IFS= read -r line; do
            if [[ $line =~ ^class\ ([A-Za-z_][A-Za-z0-9_]*)\(BaseModel\): ]]; then
                model_names+=("${BASH_REMATCH[1]}")
            fi
        done < "$output_path"

        # Step 4: Create partial model assignments using create_partial_model
        partial_lines=()
        for model in "${model_names[@]}"; do
            partial_lines+=("Partial${model} = create_partial_model(${model}, recursive=True)")
        done

        # Step 5: Append partial model lines to the file
        if [ ${#partial_lines[@]} -gt 0 ]; then
            printf "\n%s\n" "${partial_lines[@]}" >> "$output_path" || { echo "Error: Failed to append partial models to $output_path"; continue; }
        fi
    fi
done