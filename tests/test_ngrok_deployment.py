"""
Test suite for ngrok deployment configuration.

This module tests all components of the ngrok deployment setup:
- ngrok configuration file
- Streamlit configuration file
- Environment variable templates
- Makefile targets
- Documentation updates

All tests ensure the deployment is properly configured and ready to use.
"""

import re
from pathlib import Path

import pytest
import toml
import yaml


# Test fixtures
@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def ngrok_config_path() -> Path:
    """Return the path to the ngrok configuration file."""
    return Path.home() / ".config" / "ngrok" / "ngrok.yml"


@pytest.fixture
def streamlit_config_path(project_root: Path) -> Path:
    """Return the path to the Streamlit configuration file."""
    return project_root / ".streamlit" / "config.toml"


@pytest.fixture
def env_example_path(project_root: Path) -> Path:
    """Return the path to the .env.example file."""
    return project_root / ".env.example"


@pytest.fixture
def gitignore_path(project_root: Path) -> Path:
    """Return the path to the .gitignore file."""
    return project_root / ".gitignore"


@pytest.fixture
def makefile_path(project_root: Path) -> Path:
    """Return the path to the Makefile."""
    return project_root / "Makefile"


@pytest.fixture
def readme_path(project_root: Path) -> Path:
    """Return the path to README.md."""
    return project_root / "README.md"


@pytest.fixture
def claude_md_path(project_root: Path) -> Path:
    """Return the path to CLAUDE.md."""
    return project_root / "CLAUDE.md"


# ngrok Configuration Tests
class TestNgrokConfiguration:
    """Test ngrok configuration file."""

    def test_ngrok_config_exists(self, ngrok_config_path: Path) -> None:
        """Test that ngrok configuration file exists."""
        assert ngrok_config_path.exists(), f"ngrok config not found at {ngrok_config_path}"

    def test_ngrok_config_is_valid_yaml(self, ngrok_config_path: Path) -> None:
        """Test that ngrok config is valid YAML."""
        with open(ngrok_config_path) as f:
            config = yaml.safe_load(f)
        assert isinstance(config, dict), "ngrok config must be a valid YAML dictionary"

    def test_ngrok_config_version(self, ngrok_config_path: Path) -> None:
        """Test that ngrok config has correct version."""
        with open(ngrok_config_path) as f:
            config = yaml.safe_load(f)
        assert "version" in config, "ngrok config must have version field"
        assert config["version"] == "3", "ngrok config version must be '3'"

    def test_ngrok_config_has_authtoken(self, ngrok_config_path: Path) -> None:
        """Test that ngrok config has authtoken configured."""
        with open(ngrok_config_path) as f:
            config = yaml.safe_load(f)
        assert "agent" in config, "ngrok config must have agent section"
        assert "authtoken" in config["agent"], "ngrok config must have authtoken"
        assert config["agent"]["authtoken"], "authtoken must not be empty"

    def test_ngrok_config_has_tunnel(self, ngrok_config_path: Path) -> None:
        """Test that ngrok config has base-agent-ui tunnel defined."""
        with open(ngrok_config_path) as f:
            config = yaml.safe_load(f)
        assert "tunnels" in config, "ngrok config must have tunnels section"
        assert "base-agent-ui" in config["tunnels"], "Must have base-agent-ui tunnel"

    def test_ngrok_tunnel_configuration(self, ngrok_config_path: Path) -> None:
        """Test that base-agent-ui tunnel has correct configuration."""
        with open(ngrok_config_path) as f:
            config = yaml.safe_load(f)

        tunnel = config["tunnels"]["base-agent-ui"]
        assert tunnel["proto"] == "http", "Tunnel protocol must be http"
        assert tunnel["addr"] == 8501, "Tunnel must point to port 8501"
        assert "domain" in tunnel, "Tunnel must have domain configured"
        assert tunnel["inspect"] is True, "Tunnel inspection should be enabled"


# Streamlit Configuration Tests
class TestStreamlitConfiguration:
    """Test Streamlit configuration for ngrok."""

    def test_streamlit_config_exists(self, streamlit_config_path: Path) -> None:
        """Test that Streamlit config file exists."""
        assert (
            streamlit_config_path.exists()
        ), f"Streamlit config not found at {streamlit_config_path}"

    def test_streamlit_config_is_valid_toml(self, streamlit_config_path: Path) -> None:
        """Test that Streamlit config is valid TOML."""
        with open(streamlit_config_path) as f:
            config = toml.load(f)
        assert isinstance(config, dict), "Streamlit config must be valid TOML"

    def test_streamlit_server_config(self, streamlit_config_path: Path) -> None:
        """Test that Streamlit server is configured correctly for ngrok."""
        with open(streamlit_config_path) as f:
            config = toml.load(f)

        assert "server" in config, "Streamlit config must have server section"
        server = config["server"]

        assert server["port"] == 8501, "Server port must be 8501"
        assert server["address"] == "0.0.0.0", "Server must bind to 0.0.0.0"  # nosec B104 - Required for ngrok tunnel access
        assert server["headless"] is True, "Server must be headless"
        assert server["enableCORS"] is False, "CORS should be disabled (ngrok handles)"
        assert (
            server["enableXsrfProtection"] is False
        ), "XSRF protection should be disabled (ngrok handles)"

    def test_streamlit_browser_config(self, streamlit_config_path: Path) -> None:
        """Test that Streamlit browser config is set for ngrok."""
        with open(streamlit_config_path) as f:
            config = toml.load(f)

        assert "browser" in config, "Streamlit config must have browser section"
        browser = config["browser"]

        assert "serverAddress" in browser, "Browser must have serverAddress"
        assert browser["serverPort"] == 443, "Browser serverPort must be 443 (HTTPS)"
        assert browser["gatherUsageStats"] is False, "Usage stats should be disabled"

    def test_streamlit_client_config(self, streamlit_config_path: Path) -> None:
        """Test that Streamlit client config is set."""
        with open(streamlit_config_path) as f:
            config = toml.load(f)

        assert "client" in config, "Streamlit config must have client section"
        assert config["client"]["toolbarMode"] == "minimal", "Toolbar mode should be minimal"


# Environment Configuration Tests
class TestEnvironmentConfiguration:
    """Test environment variable configuration."""

    def test_env_example_exists(self, env_example_path: Path) -> None:
        """Test that .env.example file exists."""
        assert env_example_path.exists(), f".env.example not found at {env_example_path}"

    def test_env_example_has_ngrok_section(self, env_example_path: Path) -> None:
        """Test that .env.example has ngrok deployment section."""
        with open(env_example_path) as f:
            content = f.read()

        assert "NGROK DEPLOYMENT" in content, ".env.example must have NGROK section"

    def test_env_example_has_ngrok_authtoken(self, env_example_path: Path) -> None:
        """Test that .env.example has NGROK_AUTHTOKEN variable."""
        with open(env_example_path) as f:
            content = f.read()

        assert "NGROK_AUTHTOKEN=" in content, ".env.example must have NGROK_AUTHTOKEN"
        # Check for template value or comment
        assert (
            "your_ngrok_authtoken_here" in content or "dashboard.ngrok.com" in content
        ), "NGROK_AUTHTOKEN should have template or help text"

    def test_env_example_has_ngrok_domain(self, env_example_path: Path) -> None:
        """Test that .env.example has NGROK_DOMAIN variable."""
        with open(env_example_path) as f:
            content = f.read()

        assert "NGROK_DOMAIN=" in content, ".env.example must have NGROK_DOMAIN"

    def test_env_example_has_ngrok_enabled(self, env_example_path: Path) -> None:
        """Test that .env.example has NGROK_ENABLED variable."""
        with open(env_example_path) as f:
            content = f.read()

        assert "NGROK_ENABLED=" in content, ".env.example must have NGROK_ENABLED"


# Git Configuration Tests
class TestGitConfiguration:
    """Test Git configuration."""

    def test_gitignore_exists(self, gitignore_path: Path) -> None:
        """Test that .gitignore file exists."""
        assert gitignore_path.exists(), f".gitignore not found at {gitignore_path}"

    def test_gitignore_includes_streamlit(self, gitignore_path: Path) -> None:
        """Test that .gitignore includes .streamlit/ directory."""
        with open(gitignore_path) as f:
            content = f.read()

        assert ".streamlit/" in content, ".gitignore must include .streamlit/"


# Makefile Tests
class TestMakefileConfiguration:
    """Test Makefile ngrok targets."""

    def test_makefile_exists(self, makefile_path: Path) -> None:
        """Test that Makefile exists."""
        assert makefile_path.exists(), f"Makefile not found at {makefile_path}"

    def test_makefile_has_ngrok_section(self, makefile_path: Path) -> None:
        """Test that Makefile has ngrok deployment section."""
        with open(makefile_path) as f:
            content = f.read()

        assert "ngrok Deployment" in content, "Makefile must have ngrok section"

    def test_makefile_has_deploy_ngrok_target(self, makefile_path: Path) -> None:
        """Test that Makefile has deploy-ngrok target."""
        with open(makefile_path) as f:
            content = f.read()

        assert "deploy-ngrok:" in content, "Makefile must have deploy-ngrok target"

    def test_makefile_has_ngrok_start_target(self, makefile_path: Path) -> None:
        """Test that Makefile has ngrok-start target."""
        with open(makefile_path) as f:
            content = f.read()

        assert "ngrok-start:" in content, "Makefile must have ngrok-start target"

    def test_makefile_has_ngrok_ui_target(self, makefile_path: Path) -> None:
        """Test that Makefile has ngrok-ui target."""
        with open(makefile_path) as f:
            content = f.read()

        assert "ngrok-ui:" in content, "Makefile must have ngrok-ui target"

    def test_makefile_has_ngrok_status_target(self, makefile_path: Path) -> None:
        """Test that Makefile has ngrok-status target."""
        with open(makefile_path) as f:
            content = f.read()

        assert "ngrok-status:" in content, "Makefile must have ngrok-status target"

    def test_makefile_has_ngrok_logs_target(self, makefile_path: Path) -> None:
        """Test that Makefile has ngrok-logs target."""
        with open(makefile_path) as f:
            content = f.read()

        assert "ngrok-logs:" in content, "Makefile must have ngrok-logs target"

    def test_makefile_phony_includes_ngrok_targets(self, makefile_path: Path) -> None:
        """Test that .PHONY includes all ngrok targets."""
        with open(makefile_path) as f:
            content = f.read()

        # Find .PHONY line
        phony_match = re.search(r"\.PHONY:(.+)", content)
        assert phony_match, "Makefile must have .PHONY declaration"

        phony_targets = phony_match.group(1)

        # Check all ngrok targets are in .PHONY
        required_targets = [
            "deploy-ngrok",
            "ngrok-start",
            "ngrok-ui",
            "ngrok-status",
            "ngrok-logs",
        ]

        for target in required_targets:
            assert target in phony_targets, f".PHONY must include {target}"

    def test_deploy_ngrok_target_starts_streamlit(self, makefile_path: Path) -> None:
        """Test that deploy-ngrok target starts Streamlit."""
        with open(makefile_path) as f:
            content = f.read()

        # Find deploy-ngrok target definition
        deploy_match = re.search(r"deploy-ngrok:.*?(?=\n\n|\n[a-z]|\Z)", content, re.DOTALL)
        assert deploy_match, "deploy-ngrok target definition not found"

        deploy_content = deploy_match.group(0)
        assert "streamlit run" in deploy_content, "deploy-ngrok must start Streamlit"
        assert "8501" in deploy_content, "deploy-ngrok must use port 8501"

    def test_deploy_ngrok_target_starts_ngrok(self, makefile_path: Path) -> None:
        """Test that deploy-ngrok target starts ngrok tunnel."""
        with open(makefile_path) as f:
            content = f.read()

        deploy_match = re.search(r"deploy-ngrok:.*?(?=\n\n|\n[a-z]|\Z)", content, re.DOTALL)
        assert deploy_match, "deploy-ngrok target definition not found"

        deploy_content = deploy_match.group(0)
        assert "ngrok start" in deploy_content, "deploy-ngrok must start ngrok"
        assert "base-agent-ui" in deploy_content, "deploy-ngrok must start base-agent-ui tunnel"


# Documentation Tests
class TestDocumentation:
    """Test documentation updates."""

    def test_readme_exists(self, readme_path: Path) -> None:
        """Test that README.md exists."""
        assert readme_path.exists(), f"README.md not found at {readme_path}"

    def test_readme_has_ngrok_section(self, readme_path: Path) -> None:
        """Test that README.md has ngrok deployment section."""
        with open(readme_path) as f:
            content = f.read()

        assert "ngrok" in content.lower(), "README.md must mention ngrok"
        assert (
            "Remote Deployment" in content or "ngrok Deployment" in content
        ), "README.md must have deployment section"

    def test_readme_has_deploy_ngrok_command(self, readme_path: Path) -> None:
        """Test that README.md documents deploy-ngrok command."""
        with open(readme_path) as f:
            content = f.read()

        assert "make deploy-ngrok" in content, "README.md must document deploy-ngrok command"

    def test_readme_has_ngrok_prerequisites(self, readme_path: Path) -> None:
        """Test that README.md mentions ngrok prerequisites."""
        with open(readme_path) as f:
            content = f.read()

        assert "authtoken" in content.lower(), "README.md must mention authtoken"
        assert (
            "NGROK_AUTHTOKEN" in content or "ngrok account" in content.lower()
        ), "README.md must explain how to get authtoken"

    def test_claude_md_exists(self, claude_md_path: Path) -> None:
        """Test that CLAUDE.md exists."""
        assert claude_md_path.exists(), f"CLAUDE.md not found at {claude_md_path}"

    def test_claude_md_has_ngrok_commands(self, claude_md_path: Path) -> None:
        """Test that CLAUDE.md documents ngrok commands."""
        with open(claude_md_path) as f:
            content = f.read()

        assert "ngrok" in content.lower(), "CLAUDE.md must mention ngrok"
        assert "make deploy-ngrok" in content, "CLAUDE.md must document deploy-ngrok"
        assert "make ngrok-start" in content, "CLAUDE.md must document ngrok-start"


# Integration Tests
class TestNgrokIntegration:
    """Integration tests for ngrok deployment."""

    def test_streamlit_directory_exists(self, project_root: Path) -> None:
        """Test that .streamlit directory exists."""
        streamlit_dir = project_root / ".streamlit"
        assert streamlit_dir.exists(), ".streamlit directory must exist"
        assert streamlit_dir.is_dir(), ".streamlit must be a directory"

    def test_all_required_files_exist(
        self,
        ngrok_config_path: Path,
        streamlit_config_path: Path,
        env_example_path: Path,
        gitignore_path: Path,
        makefile_path: Path,
        readme_path: Path,
        claude_md_path: Path,
    ) -> None:
        """Test that all required deployment files exist."""
        required_files = [
            ngrok_config_path,
            streamlit_config_path,
            env_example_path,
            gitignore_path,
            makefile_path,
            readme_path,
            claude_md_path,
        ]

        missing_files = [f for f in required_files if not f.exists()]
        assert not missing_files, f"Missing required files: {missing_files}"

    def test_ngrok_command_available(self) -> None:
        """Test that ngrok command is available in the system."""
        import subprocess  # nosec B404 - Required for testing ngrok CLI availability

        try:
            result = subprocess.run(  # nosec B607 - Testing ngrok command availability, not user input
                ["ngrok", "version"],
                check=False, capture_output=True,
                text=True,
                timeout=5,
            )
            assert result.returncode == 0, "ngrok command must be available"
            assert "ngrok version" in result.stdout.lower(), "ngrok must report version"
        except FileNotFoundError:
            pytest.fail("ngrok command not found in PATH")
        except subprocess.TimeoutExpired:
            pytest.fail("ngrok version command timed out")

    def test_ngrok_config_validation(self) -> None:
        """Test that ngrok accepts the configuration."""
        import subprocess  # nosec B404 - Required for testing ngrok config validation

        try:
            result = subprocess.run(  # nosec B607 - Testing ngrok config validation, not user input
                ["ngrok", "config", "check"],
                check=False, capture_output=True,
                text=True,
                timeout=10,
            )
            assert result.returncode == 0, f"ngrok config invalid: {result.stderr}"
            assert "Valid configuration" in result.stdout, "ngrok config check must pass"
        except subprocess.TimeoutExpired:
            pytest.fail("ngrok config check timed out")


# Summary Test
class TestDeploymentReadiness:
    """High-level tests to verify deployment is ready."""

    def test_deployment_configuration_complete(
        self,
        ngrok_config_path: Path,
        streamlit_config_path: Path,
        makefile_path: Path,
    ) -> None:
        """Test that all deployment configuration is complete."""
        # This is a summary test that checks if deployment is ready
        checks = []

        # Check ngrok config
        if ngrok_config_path.exists():
            with open(ngrok_config_path) as f:
                ngrok_config = yaml.safe_load(f)
            checks.append("tunnels" in ngrok_config and "base-agent-ui" in ngrok_config["tunnels"])

        # Check Streamlit config
        if streamlit_config_path.exists():
            with open(streamlit_config_path) as f:
                streamlit_config = toml.load(f)
            checks.append("server" in streamlit_config and "browser" in streamlit_config)

        # Check Makefile targets
        if makefile_path.exists():
            with open(makefile_path) as f:
                makefile_content = f.read()
            checks.append("deploy-ngrok:" in makefile_content)

        assert all(checks), "Not all deployment components are configured correctly"

    def test_documentation_complete(self, readme_path: Path, claude_md_path: Path) -> None:
        """Test that documentation is complete."""
        doc_checks = []

        if readme_path.exists():
            with open(readme_path) as f:
                readme_content = f.read()
            doc_checks.append("make deploy-ngrok" in readme_content)

        if claude_md_path.exists():
            with open(claude_md_path) as f:
                claude_content = f.read()
            doc_checks.append("make deploy-ngrok" in claude_content)

        assert all(doc_checks), "Documentation is not complete"
