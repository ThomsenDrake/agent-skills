"""Load every shipping skill through Hermes. Never perform inference or render templates."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def verify(package: Path, home: Path) -> dict:
    if home.exists():
        raise ValueError("native verification requires a new isolated home")
    destination = home / "skills/pstack-hermes"
    shutil.copytree(package, destination, ignore=shutil.ignore_patterns(
        "automation", "tests", "node_modules", "__pycache__", ".pytest_cache", ".DS_Store"))
    # No active-profile credentials, plugins, sessions, or shell configuration.
    allowed = {key: value for key, value in os.environ.items()
               if key in {"PATH", "PYTHONPATH", "LANG", "LC_ALL", "TERM", "TMPDIR"}}
    allowed.update(HOME=str(home), HERMES_HOME=str(home), COLUMNS="240")
    os.environ.clear()
    os.environ.update(allowed)
    os.chdir(home)

    cli = subprocess.run([sys.executable, "-m", "hermes_cli.main", "skills", "list"],
                         env=allowed, cwd=home, capture_output=True, text=True, timeout=90)
    if cli.returncode != 0 or not cli.stdout.strip():
        raise ValueError("native Hermes skills-list command did not return a catalog")

    from ruamel.yaml import YAML
    from tools.skills_tool import clear_skills_cache, skill_view, skills_list
    yaml = YAML(typ="safe")
    roots = {}
    for path in sorted(destination.rglob("SKILL.md")):
        text = path.read_text()
        frontmatter = yaml.load(text.split("---", 2)[1])
        if frontmatter.get("deps"):
            raise ValueError("native loader check does not authorize dependency installation")
        roots[frontmatter["name"]] = path.parent
    clear_skills_cache()
    catalog = json.loads(skills_list())
    if catalog.get("success") is not True:
        raise ValueError("native Hermes catalog failed")
    listed = {entry["name"] for entry in catalog["skills"]}
    if not set(roots) <= listed:
        raise ValueError("native Hermes catalog omitted expected shipping skills")
    for name, directory in roots.items():
        result = json.loads(skill_view(name, preprocess=False))
        if result.get("success") is not True or result.get("content") != (directory / "SKILL.md").read_text():
            raise ValueError("native skill loading did not preserve the installed document")
        if Path(result["_source_path"]).resolve() != (directory / "SKILL.md").resolve():
            raise ValueError("native skill resolved outside its isolated installation")

    support_count = 0
    for path in sorted(destination.rglob("*.md")):
        if path.name == "SKILL.md":
            continue
        owner = max((name for name, directory in roots.items()
                     if path.is_relative_to(directory)), key=lambda name: len(roots[name].parts))
        relative = path.relative_to(roots[owner]).as_posix()
        result = json.loads(skill_view(owner, file_path=relative, preprocess=False))
        if result.get("success") is not True or result.get("content") != path.read_text():
            raise ValueError("native supporting-file loading failed")
        support_count += 1
    return {"loaded_skills": len(roots), "loaded_support_files": support_count,
            "cli_passed": True, "inference_performed": False,
            "template_preprocessing": False, "home": str(home)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--home", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.package.resolve(), args.home.resolve()), sort_keys=True))


if __name__ == "__main__":
    main()
