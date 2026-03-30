"""Tests for no-env-vars rule."""

import ast
from pathlib import Path

from rivt.models import RivtConfig
from rivt.rules.no_env_vars import NoEnvVarsRule

rule = NoEnvVarsRule()


def _check(source: str, file_path: str, config: RivtConfig) -> list[str]:
    tree = ast.parse(source)
    return [v.message for v in rule.check(tree, Path(file_path), config)]


class TestNoEnvVars:
    def test_os_getenv(self, fastapi_config: RivtConfig) -> None:
        source = "import os\nval = os.getenv('KEY')"
        violations = _check(source, "app/services/email.py", fastapi_config)
        assert len(violations) == 1
        assert "config module" in violations[0].lower()

    def test_os_environ_get(self, fastapi_config: RivtConfig) -> None:
        source = "import os\nval = os.environ.get('KEY')"
        violations = _check(source, "app/services/email.py", fastapi_config)
        assert len(violations) == 1

    def test_os_environ_subscript(self, fastapi_config: RivtConfig) -> None:
        source = "import os\nval = os.environ['KEY']"
        violations = _check(source, "app/services/email.py", fastapi_config)
        assert len(violations) == 1

    def test_config_module_allowed(self, fastapi_config: RivtConfig) -> None:
        source = "import os\nval = os.getenv('KEY')"
        assert _check(source, "app/core/config.py", fastapi_config) == []

    def test_no_config_module_still_reports(self) -> None:
        config = RivtConfig()
        source = "import os\nval = os.getenv('KEY')"
        violations = _check(source, "app/services/email.py", config)
        assert len(violations) == 1

    def test_config_module_list(self) -> None:
        config = RivtConfig(
            config_module=["app/core/config.py", "app/core/settings.py"]
        )
        source = "import os\nval = os.getenv('KEY')"
        assert _check(source, "app/core/settings.py", config) == []
        violations = _check(source, "app/services/email.py", config)
        assert len(violations) == 1

    def test_config_module_glob(self) -> None:
        config = RivtConfig(config_module=["app/core/*.py"])
        source = "import os\nval = os.getenv('KEY')"
        assert _check(source, "app/core/settings.py", config) == []
        violations = _check(source, "app/services/email.py", config)
        assert len(violations) == 1

    def test_message_includes_config_path(self, fastapi_config: RivtConfig) -> None:
        source = "import os\nval = os.getenv('KEY')"
        violations = _check(source, "app/services/email.py", fastapi_config)
        assert "app/core/config.py" in violations[0]
