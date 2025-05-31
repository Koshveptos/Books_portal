import os
import re


def fix_imports_in_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Заменяем импорты from app.core. на from app.core.
    modified_content = re.sub(r"from\s+core\.", "from app.core.", content)

    if content != modified_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(modified_content)
        print(f"Fixed imports in {file_path}")


def process_directory(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                fix_imports_in_file(file_path)


if __name__ == "__main__":
    # Путь к директории app
    app_dir = os.path.dirname(os.path.abspath(__file__))
    process_directory(app_dir)
    print("Finished fixing imports")
