import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "test.sh"


def test_integration_script_has_valid_shell_syntax(bash_executable):
    subprocess.run([bash_executable, "-n", SCRIPT.name], check=True, cwd=ROOT)


def test_integration_script_exercises_the_current_cli_contract():
    text = SCRIPT.read_text(encoding="utf-8")

    assert 'pip install --quiet -c "$REPO_ROOT/constraints.txt"' in text
    assert 'TEST_DIR=$(cd "$TEST_DIR" && pwd -P)' in text
    assert 'export HOME="$TEST_DIR/home"' in text
    assert "sys.version_info >= (3, 10)" in text
    assert 'PYTHON_CMD=("$REPO_ROOT/.venv/bin/python")' in text
    assert 'venv/Scripts/activate' in text
    assert "factreach install --env=auto --safe" in text
    assert "factreach install --env=auto --system --dry-run" in text
    assert "factreach doctor --json" in text
    assert 'pytest "$REPO_ROOT/tests" -q' in text

    nonexistent_commands = (
        "factreach read ",
        "factreach search ",
        "factreach search-github ",
        "factreach search-twitter ",
        "factreach search-reddit ",
        "factreach search-youtube ",
        "factreach search-bilibili ",
        "factreach search-xhs ",
    )
    assert not any(command in text for command in nonexistent_commands)
