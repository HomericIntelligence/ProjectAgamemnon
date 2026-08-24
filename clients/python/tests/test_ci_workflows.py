"""Regression smoke tests for required CI workflow contracts."""

from pathlib import Path

import pytest
import yaml

GITHUB_DIR = Path(__file__).parents[3] / ".github"
WORKFLOW_DIR = GITHUB_DIR / "workflows"
WORKFLOW_PATH = WORKFLOW_DIR / "_required.yml"
SETUP_CI_CONTAINER_ACTION_PATH = (
    GITHUB_DIR / "actions" / "setup-ci-container" / "action.yml"
)
# Jobs sharing the byte-identical release prelude (Conan Release cache +
# podman container-storage cache + CI image build) unified into the
# setup-ci-container composite action.
RELEASE_PRELUDE_JOBS = (
    "unit-tests",
    "integration-tests",
    "security-dependency-scan",
    "build",
    "package",
    "install",
)
CONAN_RELEASE_KEY_PREFIX = "conan-${{ runner.os }}-release-"

REQUIRED_WORKFLOWS = ("_required.yml", "build-test.yml", "static-analysis.yml")
SMOKE_WORKFLOW = "merge-queue-smoke.yml"
REQUIRED_CONTEXT_JOBS = {
    "lint": ("_required.yml", "lint"),
    "unit-tests": ("_required.yml", "unit-tests"),
    "integration-tests": ("_required.yml", "integration-tests"),
    "security/dependency-scan": ("_required.yml", "security-dependency-scan"),
    "security/secrets-scan": ("_required.yml", "security-secrets-scan"),
    "build": ("_required.yml", "build"),
    "schema-validation": ("_required.yml", "schema-validation"),
    "deps/version-sync": ("_required.yml", "deps-version-sync"),
    "test": ("_required.yml", "test"),
    "package": ("_required.yml", "package"),
    "install": ("_required.yml", "install"),
    "release": ("_required.yml", "release"),
    "All Build/Test Checks": ("build-test.yml", "check-all"),
    "All Static Analysis Checks": ("static-analysis.yml", "check-all"),
}


def _load_workflow(path: Path = WORKFLOW_PATH) -> dict:
    """Load a workflow as a parsed YAML dict."""
    return yaml.safe_load(path.read_text())


def _workflow_triggers(workflow: dict) -> dict:
    """Return triggers despite PyYAML 1.1 parsing the unquoted `on` key as true."""
    return workflow.get("on", workflow.get(True, {}))


def test_merge_group_runs_only_the_smoke_workflow() -> None:
    """The merge queue must run exactly one fast smoke job (one runner slot).

    The full workflows must NOT re-run for merge_group — that starved the
    runner pool and pushed queue merges to 70-90 min. merge-queue-smoke.yml
    owns the merge_group event and emits the single `merge-queue-smoke`
    context; PR-side CI is untouched.
    """
    for filename in REQUIRED_WORKFLOWS:
        triggers = _workflow_triggers(_load_workflow(WORKFLOW_DIR / filename))
        assert triggers["push"]["branches"] == ["main"]
        assert triggers["pull_request"]["branches"] == ["main"]
        assert "merge_group" not in triggers, (
            f"{filename} must not trigger on merge_group — merge-queue-smoke.yml "
            "owns that event"
        )

    smoke = _load_workflow(WORKFLOW_DIR / SMOKE_WORKFLOW)
    assert _workflow_triggers(smoke) == {"merge_group": {"types": ["checks_requested"]}}
    assert list(smoke["jobs"]) == ["merge-queue-smoke"]
    assert smoke["jobs"]["merge-queue-smoke"]["name"] == "merge-queue-smoke"
    assert smoke["jobs"]["merge-queue-smoke"]["timeout-minutes"] == 5


def test_live_required_context_names_remain_exact() -> None:
    """Required job names must continue to match the live ruleset contexts exactly."""
    workflows = {
        filename: _load_workflow(WORKFLOW_DIR / filename) for filename in REQUIRED_WORKFLOWS
    }
    actual_contexts = {
        workflows[filename]["jobs"][job_id]["name"]
        for filename, job_id in REQUIRED_CONTEXT_JOBS.values()
    }

    matrix_job = workflows["build-test.yml"]["jobs"]["build-test"]
    assert matrix_job["name"] == "${{ matrix.os }}-${{ matrix.compiler }}-${{ matrix.build_type }}"
    matrix = matrix_job["strategy"]["matrix"]
    actual_contexts.update(
        f"{os_name}-{compiler}-{build_type}"
        for os_name in matrix["os"]
        for compiler in matrix["compiler"]
        for build_type in matrix["build_type"]
    )

    assert actual_contexts == set(REQUIRED_CONTEXT_JOBS) | {
        "ubuntu-24.04-clang-debug",
        "ubuntu-24.04-clang-release",
        "ubuntu-24.04-gcc-debug",
        "ubuntu-24.04-gcc-release",
    }


def test_merge_queue_regression_runs_in_required_job() -> None:
    """The required workflow must execute this regression on every queue run."""
    workflow = _load_workflow()
    steps = workflow["jobs"]["lint"]["steps"]
    regression = next(
        step for step in steps if step.get("name") == "Run merge-queue workflow regression"
    )

    # Runs podman-by-default inside the CI container, mounting the workspace.
    assert regression["run"].startswith("podman run")
    assert "--userns=keep-id" in regression["run"]
    assert "-w /workspace agamemnon-ci:local" in regression["run"]
    assert "uv run python -m pytest tests/test_ci_workflows.py -v" in regression["run"]


def _find_gitleaks_scan_step(workflow: dict) -> dict:
    """Return the 'Run Gitleaks' step from the security-secrets-scan job."""
    steps = workflow["jobs"]["security-secrets-scan"]["steps"]
    for step in steps:
        if step.get("name") == "Run Gitleaks":
            return step
    raise AssertionError("Could not find 'Run Gitleaks' step in security-secrets-scan job")


def _find_gitleaks_upload_step(workflow: dict) -> dict:
    """Return the 'Upload Gitleaks SARIF' step from the security-secrets-scan job."""
    steps = workflow["jobs"]["security-secrets-scan"]["steps"]
    for step in steps:
        if step.get("name") == "Upload Gitleaks SARIF":
            return step
    raise AssertionError("Could not find 'Upload Gitleaks SARIF' step in security-secrets-scan job")


def test_gitleaks_scan_step_is_blocking() -> None:
    """The Run Gitleaks step must not have continue-on-error set."""
    workflow = _load_workflow()
    step = _find_gitleaks_scan_step(workflow)
    assert "continue-on-error" not in step, (
        "Run Gitleaks step has continue-on-error — secrets scan is not a blocking gate"
    )


def test_gitleaks_uses_exit_code_1() -> None:
    """The Run Gitleaks step must use --exit-code 1, not --exit-code 0."""
    workflow = _load_workflow()
    step = _find_gitleaks_scan_step(workflow)
    run_block: str = step["run"]

    assert "--exit-code 0" not in run_block, (
        "Run Gitleaks step still uses --exit-code 0 — scan result is informational-only"
    )
    assert "--exit-code 1" in run_block, (
        "Run Gitleaks step does not use --exit-code 1 — scan is not blocking on secrets"
    )


def test_gitleaks_sarif_upload_step_not_affected() -> None:
    """The SARIF upload step must still use if: always() so reports are uploaded even on failure."""
    workflow = _load_workflow()
    step = _find_gitleaks_upload_step(workflow)
    condition: str = step.get("if", "")
    assert "always()" in condition, (
        "Upload Gitleaks SARIF step lost its 'always()' condition — "
        "SARIF reports will not be uploaded when the scan fails"
    )


def _load_composite_action() -> dict:
    """Load the setup-ci-container composite action as a parsed YAML dict."""
    return yaml.safe_load(SETUP_CI_CONTAINER_ACTION_PATH.read_text())


def test_release_cache_keys_live_only_in_composite_action() -> None:
    """The duplicated conan-release cache key must not remain in _required.yml.

    Issue #241: the key is now declared exactly once, inside the
    setup-ci-container composite action.
    """
    workflow_text = WORKFLOW_PATH.read_text()
    assert CONAN_RELEASE_KEY_PREFIX not in workflow_text, (
        "conan release cache key reappeared inline in _required.yml — "
        "it must live only in .github/actions/setup-ci-container/action.yml"
    )
    action = _load_composite_action()
    action_text = SETUP_CI_CONTAINER_ACTION_PATH.read_text()
    assert action["runs"]["using"] == "composite"
    assert action_text.count(f"key: {CONAN_RELEASE_KEY_PREFIX}") == 1


def test_composite_action_restores_expected_caches_in_order() -> None:
    """The composite action must keep the exact pre-existing step sequence.

    Byte-for-byte key parity with the pre-refactor jobs (plan Decision 6):
    existing main-branch caches must keep hitting after the extraction.
    """
    steps = _load_composite_action()["runs"]["steps"]
    names = [step["name"] for step in steps]
    assert names == [
        "Prune stale podman storage (self-hosted disk pressure)",
        "Restore Conan cache",
        "Cache podman container storage",
        "Build CI image (podman)",
    ]

    conan = next(step for step in steps if step["name"] == "Restore Conan cache")
    with_block = conan["with"]
    assert with_block["path"] == "~/.conan2"
    assert (
        with_block["key"]
        == "conan-${{ runner.os }}-release-${{ hashFiles('conanfile.py') }}"
    )
    assert with_block["restore-keys"] == (
        "conan-${{ runner.os }}-release-\nconan-${{ runner.os }}-\n"
    )

    podman_cache = next(
        step for step in steps if step["name"] == "Cache podman container storage"
    )
    assert podman_cache["with"]["path"] == "~/.local/share/containers/storage"
    assert (
        podman_cache["with"]["key"]
        == "podman-agamemnon-${{ runner.os }}-${{ hashFiles('pyproject.toml', 'uv.lock') }}"
    )

    image_build = next(
        step for step in steps if step["name"] == "Build CI image (podman)"
    )
    assert image_build["run"].endswith("podman build -f ci/Containerfile -t agamemnon-ci:local .")


@pytest.mark.parametrize("job_id", RELEASE_PRELUDE_JOBS)
def test_release_prelude_jobs_use_the_composite_action(job_id: str) -> None:
    """Every release-pattern job must call the shared composite action once,
    after checkout (local actions resolve from the checked-out workspace)."""
    workflow = _load_workflow()
    steps = workflow["jobs"][job_id]["steps"]

    uses_steps = [
        step for step in steps if step.get("uses") == "./.github/actions/setup-ci-container"
    ]
    assert len(uses_steps) == 1, f"{job_id} must call the composite action exactly once"

    action_index = steps.index(uses_steps[0])
    assert steps[0].get("uses", "").startswith("actions/checkout@"), (
        f"{job_id} must check out the repo before resolving the local composite action"
    )
    assert action_index > 0


def test_lint_keeps_debug_conan_cache_inline() -> None:
    """lint uses a Debug-scoped conan key and stays out of the unified action."""
    workflow = _load_workflow()
    steps = workflow["jobs"]["lint"]["steps"]
    assert all(
        step.get("uses") != "./.github/actions/setup-ci-container" for step in steps
    ), "lint must not use the release-scoped composite action"
    conan_step = next(
        step for step in steps if step.get("name") == "Restore Conan cache"
    )
    assert conan_step["with"]["key"].startswith(
        "conan-${{ runner.os }}-debug-"
    )
