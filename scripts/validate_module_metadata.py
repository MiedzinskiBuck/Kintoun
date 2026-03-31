import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULES_DIR = ROOT / "modules"
REQUIRED_FIELDS = {
    "name",
    "display_name",
    "category",
    "description",
    "requires_region",
    "inputs",
    "output_type",
    "risk_level",
}


def load_metadata(module_file: Path):
    source = module_file.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "MODULE_METADATA":
                    value = ast.literal_eval(node.value)
                    if isinstance(value, dict):
                        return value
    return None


def validate():
    failures = []
    for module_file in MODULES_DIR.rglob("*.py"):
        if module_file.name == "__init__.py":
            continue
        metadata = load_metadata(module_file)
        if metadata is None:
            failures.append((module_file, "Missing MODULE_METADATA"))
            continue
        missing = REQUIRED_FIELDS.difference(metadata.keys())
        if missing:
            failures.append((module_file, f"Missing fields: {sorted(missing)}"))
        if not isinstance(metadata.get("inputs"), list):
            failures.append((module_file, "'inputs' must be a list"))

    if failures:
        print("Module metadata validation failed:")
        for file_path, message in failures:
            print(f"- {file_path}: {message}")
        return 1
    print("Module metadata validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(validate())
