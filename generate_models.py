import os
import subprocess
import re
import argparse

def generate_models(folder_path):
    # Create a 'models' directory inside the given folder
    models_dir = os.path.join(folder_path, 'models')
    os.makedirs(models_dir, exist_ok=True)

    # Iterate over each JSON file in the folder
    for filename in os.listdir(folder_path):
        if filename.endswith('.json'):
            schema_path = os.path.join(folder_path, filename)
            base_name = os.path.splitext(filename)[0]
            output_path = os.path.join(models_dir, base_name + '.py')

            # Step 1: Generate standard Pydantic models using datamodel-code-generator
            subprocess.run([
                'datamodel-codegen',
                '--input', schema_path,
                '--input-file-type', 'jsonschema',
                '--output', output_path
            ], check=True)

            # Step 2: Read the generated code
            with open(output_path, 'r') as f:
                code = f.read()

            # Step 3: Check if create_partial_model import is already present
            if "from pydantic_partial import create_partial_model" not in code:
                lines = code.split('\n')
                last_import_index = -1
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped.startswith('import') or stripped.startswith('from'):
                        last_import_index = i
                if last_import_index != -1:
                    new_import = "from pydantic_partial import create_partial_model"
                    lines.insert(last_import_index + 1, new_import)
                    code_with_import = '\n'.join(lines)
                else:
                    code_with_import = "from pydantic_partial import create_partial_model\n" + code
            else:
                code_with_import = code

            # Step 4: Extract model names (classes inheriting from BaseModel)
            model_names = re.findall(r"class (\w+)\(BaseModel\):", code_with_import)

            # Step 5: Create partial model assignments using create_partial_model
            partial_definitions = [
                f"Partial{model_name} = create_partial_model({model_name} , recursive = True)\n"
                for model_name in model_names
            ]

            # Step 6: Combine standard models with partial model assignments
            final_code = code_with_import + '\n' + ''.join(partial_definitions)

            # Step 7: Write the final code back to the output file
            with open(output_path, 'w') as f:
                f.write(final_code)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Pydantic models and partial models from JSON schemas.")
    parser.add_argument("folder", help="Path to the folder containing JSON schemas")
    args = parser.parse_args()

    generate_models(args.folder)