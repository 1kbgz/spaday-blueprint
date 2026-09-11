"""Assemble the static Pyodide example from locally built and downloaded wheels."""

import json
import shutil
import sys
import zipfile
from pathlib import Path


def copy_wheel(wheel: Path, output: Path) -> str:
    target = output / "pypi" / wheel.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(wheel, target)
    return f"pypi/{wheel.name}"


def extract_assets(wheel: Path, package: str, output: Path) -> None:
    prefix = f"{package}/extension/"
    with zipfile.ZipFile(wheel) as archive:
        assets = [name for name in archive.namelist() if name.startswith(prefix) and not name.endswith("/")]
        if not assets:
            raise RuntimeError(f"{wheel.name} contains no browser assets")
        for name in assets:
            target = output / name.removeprefix(prefix)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(name))


def one_wheel(directory: Path, distribution: str) -> Path:
    wheels = list(directory.glob(f"{distribution}-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"expected one {distribution} wheel in {directory}, found {len(wheels)}")
    return wheels[0]


def write_index(output: Path) -> None:
    imports_file = output / "components" / "blueprint" / "vendor" / "imports.json"
    imports = {specifier: f"./components/blueprint/{target}" for specifier, target in json.loads(imports_file.read_text(encoding="utf-8")).items()}
    importmap = f'<script type="importmap">\n{json.dumps({"imports": imports}, indent=2)}\n    </script>'
    template = Path(__file__).with_name("pyodide.html").read_text(encoding="utf-8")
    output.joinpath("index.html").write_text(template.replace("<!-- importmap -->", importmap), encoding="utf-8")


def main(output: Path, blueprint_wheel: Path, dependency_dir: Path) -> None:
    spaday_wheel = one_wheel(dependency_dir, "spaday")
    transports_wheel = one_wheel(dependency_dir, "transports")
    wheels = {
        "blueprint": copy_wheel(blueprint_wheel, output),
        "spaday": copy_wheel(spaday_wheel, output),
        "transports": copy_wheel(transports_wheel, output),
    }
    extract_assets(blueprint_wheel, "spaday_blueprint", output / "components" / "blueprint")
    extract_assets(spaday_wheel, "spaday", output / "runtime" / "spaday")
    output.joinpath("wheels.json").write_text(json.dumps(wheels, indent=2) + "\n", encoding="utf-8")
    write_index(output)


if __name__ == "__main__":
    main(*(Path(value) for value in sys.argv[1:]))
