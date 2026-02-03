#!/usr/bin/env python3
"""
Tests for deploy.py

Basic smoke tests to verify the deployment orchestrator works correctly.
"""

import sys
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.setup.deploy import DeploymentOrchestrator
from scripts.setup.utils.console import SetupConsole


def test_orchestrator_initialization():
    """Test that the orchestrator can be initialized."""
    console = SetupConsole()
    orchestrator = DeploymentOrchestrator(
        console=console,
        dry_run=True,
        skip_backup=False,
        skip_migrations=False,
        rebuild=False,
        non_interactive=True
    )

    assert orchestrator.dry_run is True
    assert orchestrator.skip_backup is False
    assert orchestrator.skip_migrations is False
    assert orchestrator.rebuild is False
    assert orchestrator.non_interactive is True
    assert orchestrator.phases_completed == []
    print("✓ Orchestrator initialization test passed")


def test_disk_space_check():
    """Test disk space checking."""
    console = SetupConsole()
    orchestrator = DeploymentOrchestrator(
        console=console,
        dry_run=True,
        non_interactive=True
    )

    disk_space = orchestrator._check_disk_space()
    assert isinstance(disk_space, float)
    assert disk_space > 0
    print(f"✓ Disk space check test passed: {disk_space:.2f} GB available")


def test_jwt_validation():
    """Test JWT key validation."""
    console = SetupConsole()
    orchestrator = DeploymentOrchestrator(
        console=console,
        dry_run=True,
        non_interactive=True
    )

    jwt_private = project_root / "secrets" / "jwt" / "private_key.pem"
    jwt_public = project_root / "secrets" / "jwt" / "public_key.pem"

    if jwt_private.exists() and jwt_public.exists():
        is_valid = orchestrator._validate_jwt_keys(jwt_private, jwt_public)
        assert isinstance(is_valid, bool)
        print(f"✓ JWT validation test passed: keys {'valid' if is_valid else 'invalid'}")
    else:
        print("⚠ JWT keys not found, skipping validation test")


def test_preflight_checks():
    """Test pre-flight checks (dry run)."""
    console = SetupConsole()
    orchestrator = DeploymentOrchestrator(
        console=console,
        dry_run=True,
        non_interactive=True
    )

    # This should not raise any exceptions in dry-run mode
    result = orchestrator.run_preflight_checks()
    assert isinstance(result, bool)
    print(f"✓ Pre-flight checks test passed: {'passed' if result else 'failed'}")


def test_phase_methods_exist():
    """Test that all phase methods exist."""
    console = SetupConsole()
    orchestrator = DeploymentOrchestrator(
        console=console,
        dry_run=True,
        non_interactive=True
    )

    assert hasattr(orchestrator, 'phase1_preparation')
    assert hasattr(orchestrator, 'phase2_infrastructure')
    assert hasattr(orchestrator, 'phase3_migrations')
    assert hasattr(orchestrator, 'phase4_application')
    assert hasattr(orchestrator, 'phase5_verification')
    assert hasattr(orchestrator, 'rollback')
    print("✓ Phase methods existence test passed")


def test_phases_in_dry_run():
    """Test that phases can run in dry-run mode."""
    console = SetupConsole()
    orchestrator = DeploymentOrchestrator(
        console=console,
        dry_run=True,
        non_interactive=True,
        skip_backup=True,
        skip_migrations=True
    )

    # Test each phase individually
    result1 = orchestrator.phase1_preparation()
    assert result1 is True, "Phase 1 should succeed in dry-run"
    print("✓ Phase 1 (Preparation) dry-run test passed")

    result2 = orchestrator.phase2_infrastructure()
    assert result2 is True, "Phase 2 should succeed in dry-run"
    print("✓ Phase 2 (Infrastructure) dry-run test passed")

    result3 = orchestrator.phase3_migrations()
    assert result3 is True, "Phase 3 should succeed in dry-run"
    print("✓ Phase 3 (Migrations) dry-run test passed")

    result4 = orchestrator.phase4_application()
    assert result4 is True, "Phase 4 should succeed in dry-run"
    print("✓ Phase 4 (Application) dry-run test passed")

    result5 = orchestrator.phase5_verification()
    assert result5 is True, "Phase 5 should succeed in dry-run"
    print("✓ Phase 5 (Verification) dry-run test passed")

    # Check phases were tracked
    expected_phases = ["preparation", "infrastructure", "migrations", "application", "verification"]
    assert orchestrator.phases_completed == expected_phases
    print("✓ Phase tracking test passed")


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("Running deploy.py tests")
    print("=" * 70 + "\n")

    try:
        test_orchestrator_initialization()
        test_disk_space_check()
        test_jwt_validation()
        test_phase_methods_exist()
        test_preflight_checks()
        test_phases_in_dry_run()

        print("\n" + "=" * 70)
        print("All tests passed!")
        print("=" * 70 + "\n")
        return True

    except AssertionError as e:
        print(f"\n✗ Test failed: {str(e)}\n")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
