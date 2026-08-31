"""Fail-closed policy for the Python client's dependency audit toolchain."""

import re
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import tomllib
import yaml

CLIENT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = CLIENT_ROOT.parents[1]
PYPROJECT = CLIENT_ROOT / "pyproject.toml"
LOCKFILE = CLIENT_ROOT / "uv.lock"
REQUIRED_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "_required.yml"
AUDIT_COMMAND = "cd clients/python && uv run --only-group lint pip-audit --skip-editable"
_SPECIFIER = re.compile(r"^(>=|<=|==|!=|>|<)([0-9]+(?:\.[0-9]+)*)$")


def _requirement(group: list[str], package: str) -> str:
    matches = [item for item in group if re.match(rf"^{re.escape(package)}(?:[<>=!~;]|$)", item)]
    assert len(matches) == 1, f"expected one {package} requirement, found {matches}"
    return matches[0]


def _release(version: str) -> tuple[int, ...]:
    """Parse the numeric release subset used by pip's locked stable versions."""
    assert re.fullmatch(r"[0-9]+(?:\.[0-9]+)*", version), (
        f"unsupported non-release version: {version}"
    )
    release = [int(part) for part in version.split(".")]
    while len(release) > 1 and release[-1] == 0:
        release.pop()
    return tuple(release)


def _compare_release(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    width = max(len(left), len(right))
    padded_left = left + (0,) * (width - len(left))
    padded_right = right + (0,) * (width - len(right))
    return (padded_left > padded_right) - (padded_left < padded_right)


def _parse_specifiers(value: str) -> tuple[tuple[str, tuple[int, ...]], ...]:
    parsed: list[tuple[str, tuple[int, ...]]] = []
    for raw_specifier in value.split(","):
        match = _SPECIFIER.fullmatch(raw_specifier.strip())
        assert match is not None, f"unsupported pip specifier: {raw_specifier}"
        parsed.append((match.group(1), _release(match.group(2))))
    assert parsed, "pip must declare a version specifier"
    return tuple(parsed)


def _parse_requirement(
    value: str,
) -> tuple[str, tuple[tuple[str, tuple[int, ...]], ...], str]:
    declaration, separator, marker = value.partition(";")
    match = re.fullmatch(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)(.*?)\s*", declaration)
    assert match is not None, f"unsupported requirement: {value}"
    return (
        match.group(1),
        _parse_specifiers(match.group(2)),
        marker.strip() if separator else "",
    )


def _specifier_accepts(
    version: tuple[int, ...], specifiers: tuple[tuple[str, tuple[int, ...]], ...]
) -> bool:
    def accepts(operator: str, candidate: tuple[int, ...]) -> bool:
        comparison = _compare_release(version, candidate)
        return {
            ">=": comparison >= 0,
            "<=": comparison <= 0,
            "==": comparison == 0,
            "!=": comparison != 0,
            ">": comparison > 0,
            "<": comparison < 0,
        }[operator]

    return all(accepts(operator, candidate) for operator, candidate in specifiers)


def _assert_pip_security_floor(project: dict[str, Any], lock: dict[str, Any]) -> None:
    lint = project["dependency-groups"]["lint"]
    pip_name, pip_specifiers, pip_marker = _parse_requirement(_requirement(lint, "pip"))
    assert pip_name == "pip"
    assert pip_marker == "python_version >= '3.10'", "pip must retain the Python 3.10 marker"

    lower_bounds = [version for operator, version in pip_specifiers if operator == ">="]
    fixed_release = _release("26.2")
    assert lower_bounds and any(
        _compare_release(lower_bound, fixed_release) >= 0 for lower_bound in lower_bounds
    ), "pip lower bound must be at least 26.2"

    locked_pip = [package for package in lock["package"] if package["name"] == "pip"]
    assert len(locked_pip) == 1
    locked_version = _release(locked_pip[0]["version"])
    assert _compare_release(locked_version, fixed_release) >= 0
    assert _specifier_accepts(locked_version, pip_specifiers), (
        "pip requirement must accept locked version"
    )

    client = next(
        package for package in lock["package"] if package["name"] == "homericintelligence-agamemnon"
    )
    lint_metadata = client["metadata"]["requires-dev"]["lint"]
    pip_metadata = [item for item in lint_metadata if item["name"] == "pip"]
    assert len(pip_metadata) == 1
    assert pip_metadata[0]["marker"] == "python_full_version >= '3.10'"
    assert set(_parse_specifiers(pip_metadata[0]["specifier"])) == set(pip_specifiers)


def test_pip_security_floor_is_declared_and_locked() -> None:
    """The audit environment must never resolve the vulnerable pip release."""
    with PYPROJECT.open("rb") as stream:
        project = tomllib.load(stream)
    with LOCKFILE.open("rb") as stream:
        lock = tomllib.load(stream)

    _assert_pip_security_floor(project, lock)


def _project_and_lock() -> tuple[dict[str, Any], dict[str, Any]]:
    with PYPROJECT.open("rb") as stream:
        project = tomllib.load(stream)
    with LOCKFILE.open("rb") as stream:
        lock = tomllib.load(stream)
    return project, lock


def _replace_pip_requirement(
    project: dict[str, Any], lock: dict[str, Any], requirement: str, specifier: str
) -> None:
    lint = project["dependency-groups"]["lint"]
    index = lint.index(_requirement(lint, "pip"))
    lint[index] = requirement

    client = next(
        package for package in lock["package"] if package["name"] == "homericintelligence-agamemnon"
    )
    pip_metadata = next(
        item for item in client["metadata"]["requires-dev"]["lint"] if item["name"] == "pip"
    )
    pip_metadata["specifier"] = specifier


@pytest.mark.parametrize(
    ("requirement", "specifier"),
    [
        pytest.param(
            "pip>=26.2.1; python_version >= '3.10'",
            ">=26.2.1",
            id="stronger-floor",
        ),
        pytest.param(
            "pip>=26.2,<27; python_version >= '3.10'",
            ">=26.2,<27",
            id="compatible-ceiling",
        ),
    ],
)
def test_pip_security_policy_accepts_safe_requirement_updates(
    requirement: str, specifier: str
) -> None:
    """A safe future floor or compatible ceiling must not break the policy test."""
    project, lock = _project_and_lock()
    _replace_pip_requirement(project, lock, requirement, specifier)

    _assert_pip_security_floor(project, lock)


def test_pip_security_policy_rejects_a_floor_below_the_fixed_release() -> None:
    """A lower bound that permits the vulnerable pip release must fail."""
    project, lock = _project_and_lock()
    _replace_pip_requirement(
        project,
        lock,
        "pip>=26.1.2; python_version >= '3.10'",
        ">=26.1.2",
    )

    with pytest.raises(AssertionError, match="pip lower bound must be at least 26.2"):
        _assert_pip_security_floor(project, lock)


def test_pip_security_policy_rejects_a_marker_that_expands_the_audit_runtime() -> None:
    """The pip audit tool must retain its Python 3.10 runtime boundary."""
    project, lock = _project_and_lock()
    _replace_pip_requirement(
        project,
        lock,
        "pip>=26.2; python_version >= '3.9'",
        ">=26.2",
    )

    with pytest.raises(AssertionError, match="pip must retain the Python 3.10 marker"):
        _assert_pip_security_floor(project, lock)


def test_pip_security_policy_rejects_a_ceiling_that_excludes_the_lock() -> None:
    """The complete pip specifier must accept the locked release."""
    project, lock = _project_and_lock()
    _replace_pip_requirement(
        project,
        lock,
        "pip>=26.2,<26.2.1; python_version >= '3.10'",
        ">=26.2,<26.2.1",
    )

    with pytest.raises(AssertionError, match="pip requirement must accept locked version"):
        _assert_pip_security_floor(project, lock)


def test_policy_parser_adds_no_public_development_dependency() -> None:
    """The policy parser must use the stdlib rather than expand the public dev API."""
    project, lock = _project_and_lock()
    client = next(
        package for package in lock["package"] if package["name"] == "homericintelligence-agamemnon"
    )

    groups = [
        project["project"]["optional-dependencies"]["dev"],
        project["dependency-groups"]["dev"],
        client["metadata"]["requires-dist"],
        client["metadata"]["requires-dev"]["dev"],
    ]
    for group in groups:
        assert not any(
            (item if isinstance(item, str) else item["name"]).split(";")[0].startswith("packaging")
            for item in group
        )


def _required_workflow() -> dict[str, Any]:
    return yaml.safe_load(REQUIRED_WORKFLOW.read_text())


def _security_scan_job(workflow: dict[str, Any]) -> dict[str, Any]:
    return workflow["jobs"]["security-dependency-scan"]


def _audit_step(workflow: dict[str, Any]) -> dict[str, Any]:
    matches = [
        item
        for item in _security_scan_job(workflow)["steps"]
        if any(line.strip() == AUDIT_COMMAND for line in item.get("run", "").splitlines())
    ]
    assert len(matches) == 1, "expected one exact audit command"
    return matches[0]


def _assert_outer_shell_propagates_failure(run: str) -> None:
    controlled_run = "podman() { return 97; }\n" + run
    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", controlled_run],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 97, "outer shell must propagate controlled podman failure"


def _assert_required_workflow_runs_fail_closed(workflow: dict[str, Any]) -> None:
    workflow_run_defaults = workflow.get("defaults", {}).get("run", {})
    assert "shell" not in workflow_run_defaults, "workflow must not override audit shell"

    job = _security_scan_job(workflow)
    assert "continue-on-error" not in job, "job must not set continue-on-error"
    assert "if" not in job, "job must not set if"
    job_run_defaults = job.get("defaults", {}).get("run", {})
    assert "shell" not in job_run_defaults, "job must not override audit shell"

    step = _audit_step(workflow)
    assert "continue-on-error" not in step, "step must not set continue-on-error"
    assert "if" not in step, "step must not set if"
    assert "shell" not in step, "step must not override audit shell"

    run = step["run"]
    assert "--ignore-vuln" not in run

    lines = [line.strip() for line in run.splitlines() if line.strip()]
    audit_indexes = [index for index, line in enumerate(lines) if line == AUDIT_COMMAND]
    assert len(audit_indexes) == 1, "expected one exact audit command"

    assert "||" not in run, "composite step must not suppress failures"

    audit_index = audit_indexes[0]

    strict_indexes = [
        index for index, line in enumerate(lines[:audit_index]) if line == "set -euo pipefail"
    ]
    assert strict_indexes, "expected set -euo pipefail before audit"

    disables_errexit = re.compile(r"\bset\s+(?:\+e\b|\+o\s+errexit\b)")
    assert not disables_errexit.search(run), "composite step must not disable errexit"

    _assert_outer_shell_propagates_failure(run)

    disables_pipefail = re.compile(r"\bset\s+\+o\s+pipefail\b")
    assert not disables_pipefail.search(run), "composite step must not disable pipefail"


def test_required_workflow_runs_the_exact_unsuppressed_audit() -> None:
    """Required Checks must execute one exact pip-audit command and fail on its status."""
    _assert_required_workflow_runs_fail_closed(_required_workflow())


@pytest.mark.parametrize("scope", ["job", "step"])
def test_required_workflow_rejects_continue_on_error(scope: str) -> None:
    """The audit must reject job-level and step-level failure suppression."""
    workflow = deepcopy(_required_workflow())
    target = _security_scan_job(workflow) if scope == "job" else _audit_step(workflow)
    target["continue-on-error"] = True

    with pytest.raises(AssertionError, match=f"{scope} must not set continue-on-error"):
        _assert_required_workflow_runs_fail_closed(workflow)


@pytest.mark.parametrize(
    ("prefix", "suffix"),
    [
        pytest.param("echo ", "", id="not-an-executed-command"),
        pytest.param("", " || :", id="shell-no-op-fallback"),
        pytest.param("", " || true", id="shell-true-fallback"),
    ],
)
def test_required_workflow_rejects_non_exact_or_suppressed_audit(prefix: str, suffix: str) -> None:
    """The audit command must be one exact shell command without a fallback."""
    workflow = deepcopy(_required_workflow())
    step = _audit_step(workflow)
    step["run"] = step["run"].replace(
        AUDIT_COMMAND,
        f"{prefix}{AUDIT_COMMAND}{suffix}",
    )

    with pytest.raises(AssertionError, match="exact audit command"):
        _assert_required_workflow_runs_fail_closed(workflow)


def test_required_workflow_requires_strict_shell_mode_before_audit() -> None:
    """The audit must run after the script enables strict shell failure handling."""
    workflow = deepcopy(_required_workflow())
    step = _audit_step(workflow)
    step["run"] = step["run"].replace("set -euo pipefail", "set -uo pipefail", 1)

    with pytest.raises(AssertionError, match="set -euo pipefail before audit"):
        _assert_required_workflow_runs_fail_closed(workflow)


@pytest.mark.parametrize(
    "disable",
    [
        pytest.param("set +e", id="short-form"),
        pytest.param("set +o errexit", id="option-form"),
        pytest.param("if set +e; then :; fi", id="short-form-in-condition"),
        pytest.param("if set +o errexit; then :; fi", id="option-form-in-condition"),
        pytest.param("set +e&& :", id="short-form-before-operator"),
        pytest.param("set +o errexit>/dev/null", id="option-form-before-redirection"),
    ],
)
def test_required_workflow_rejects_errexit_disable_before_audit(disable: str) -> None:
    """The audit must reject a later command that disables shell errexit."""
    workflow = deepcopy(_required_workflow())
    step = _audit_step(workflow)
    step["run"] = step["run"].replace(AUDIT_COMMAND, f"{disable}\n{AUDIT_COMMAND}")

    with pytest.raises(AssertionError, match="composite step must not disable errexit"):
        _assert_required_workflow_runs_fail_closed(workflow)


@pytest.mark.parametrize(
    "fallback",
    [
        pytest.param("|| :", id="no-op"),
        pytest.param("|| true", id="true"),
        pytest.param("|| exit 0", id="zero-exit"),
        pytest.param("|| echo audit-failure-ignored", id="successful-command"),
    ],
)
def test_required_workflow_rejects_outer_shell_fallback(fallback: str) -> None:
    """The outer container command must propagate the inner shell status."""
    workflow = deepcopy(_required_workflow())
    step = _audit_step(workflow)
    step["run"] = f"{step['run'].rstrip()} {fallback}\n"

    with pytest.raises(AssertionError, match="composite step must not suppress failures"):
        _assert_required_workflow_runs_fail_closed(workflow)


@pytest.mark.parametrize(
    "disable",
    [
        pytest.param("set +e", id="short-form"),
        pytest.param("set +o errexit", id="option-form"),
        pytest.param("if set +e; then :; fi", id="short-form-in-condition"),
        pytest.param("if set +o errexit; then :; fi", id="option-form-in-condition"),
        pytest.param("set +e&& :", id="short-form-before-operator"),
        pytest.param("set +o errexit>/dev/null", id="option-form-before-redirection"),
    ],
)
def test_required_workflow_rejects_errexit_disable_after_audit(disable: str) -> None:
    """Strict mode must stay active for the complete inner scanner script."""
    workflow = deepcopy(_required_workflow())
    step = _audit_step(workflow)
    step["run"] = step["run"].replace(AUDIT_COMMAND, f"{AUDIT_COMMAND}\n{disable}")

    with pytest.raises(AssertionError, match="composite step must not disable errexit"):
        _assert_required_workflow_runs_fail_closed(workflow)


@pytest.mark.parametrize("scope", ["job", "step"])
def test_required_workflow_rejects_skipped_audit(scope: str) -> None:
    """The required audit must not have a condition that can skip it."""
    workflow = deepcopy(_required_workflow())
    target = _security_scan_job(workflow) if scope == "job" else _audit_step(workflow)
    target["if"] = "${{ false }}"

    with pytest.raises(AssertionError, match=f"{scope} must not set if"):
        _assert_required_workflow_runs_fail_closed(workflow)


@pytest.mark.parametrize("scope", ["workflow", "job", "step"])
def test_required_workflow_rejects_audit_shell_override(scope: str) -> None:
    """The controlled proof must use the same fail-fast shell flags as Actions."""
    workflow = deepcopy(_required_workflow())
    if scope == "workflow":
        workflow["defaults"] = {"run": {"shell": "bash {0}"}}
    elif scope == "job":
        _security_scan_job(workflow)["defaults"] = {"run": {"shell": "bash {0}"}}
    else:
        _audit_step(workflow)["shell"] = "bash {0}"

    with pytest.raises(AssertionError, match=f"{scope} must not override audit shell"):
        _assert_required_workflow_runs_fail_closed(workflow)


def test_required_workflow_allows_audit_step_rename() -> None:
    """The policy must bind audit behavior, not the step's display name."""
    workflow = deepcopy(_required_workflow())
    _audit_step(workflow)["name"] = "Dependency audit"

    _assert_required_workflow_runs_fail_closed(workflow)


@pytest.mark.parametrize(
    ("prefix", "suffix"),
    [
        pytest.param("if ", "\nthen\n  :\nfi", id="if-condition"),
        pytest.param("! ", "", id="negation"),
        pytest.param("", " &", id="background"),
        pytest.param("set +o pipefail\n", " | true", id="disabled-pipefail-pipeline"),
        pytest.param("while ", "\ndo\n  :\n  break\ndone", id="loop-condition"),
    ],
)
def test_required_workflow_rejects_outer_status_masking(prefix: str, suffix: str) -> None:
    """The complete Actions shell must propagate a controlled podman failure."""
    workflow = deepcopy(_required_workflow())
    step = _audit_step(workflow)
    step["run"] = f"{prefix}{step['run'].rstrip()}{suffix}\n"

    with pytest.raises(
        AssertionError,
        match="outer shell must propagate controlled podman failure",
    ):
        _assert_required_workflow_runs_fail_closed(workflow)


def test_required_workflow_observes_the_controlled_podman_status() -> None:
    """An unrelated earlier failure must not masquerade as audit-status propagation."""
    workflow = deepcopy(_required_workflow())
    step = _audit_step(workflow)
    step["run"] = f"false\n{step['run']}"

    with pytest.raises(
        AssertionError,
        match="outer shell must propagate controlled podman failure",
    ):
        _assert_required_workflow_runs_fail_closed(workflow)


def _inner_audit_payload(workflow: dict[str, Any]) -> str:
    run_lines = _audit_step(workflow)["run"].splitlines()
    start = next(index for index, line in enumerate(run_lines) if line.strip() == "bash -c '")
    end = next(
        index
        for index, line in enumerate(run_lines[start + 1 :], start=start + 1)
        if line.strip() == "'"
    )
    return "\n".join(run_lines[start + 1 : end])


def test_controlled_workflow_payload_propagates_audit_failure() -> None:
    """A failing audit in the reviewed inner script must make that script fail."""
    payload = _inner_audit_payload(_required_workflow())
    assert payload.count(AUDIT_COMMAND) == 1
    controlled_payload = """
cd() { :; }
trivy() { :; }
conan() { :; }
syft() { :; }
grype() { :; }
""" + payload.replace(AUDIT_COMMAND, "false")
    result = subprocess.run(
        ["bash", "-c", controlled_payload],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
