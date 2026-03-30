"""Tests for config loading — default can_import, library restrictions, overrides."""

from pathlib import Path

from rivt.config import load_config


def _write_config(tmp_path: Path, toml: str) -> Path:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(toml, encoding="utf-8")
    return tmp_path


class TestCanImport:
    def test_omitted_can_import_defaults_to_empty(self, tmp_path: Path) -> None:
        _write_config(
            tmp_path,
            '[tool.rivt]\n[tool.rivt.layers.routers]\npaths = ["app/routers"]\n',
        )
        config = load_config(tmp_path)
        assert config.layers["routers"].can_import == []

    def test_explicit_can_import_is_used(self, tmp_path: Path) -> None:
        _write_config(
            tmp_path,
            "[tool.rivt]\n"
            "[tool.rivt.layers.routers]\n"
            'paths = ["app/routers"]\n'
            'can_import = ["services", "schemas", "models"]\n',
        )
        config = load_config(tmp_path)
        assert config.layers["routers"].can_import == ["services", "schemas", "models"]


class TestLibraryRestrictions:
    def test_fastapi_always_restricted(self, tmp_path: Path) -> None:
        _write_config(tmp_path, "[tool.rivt]\n")
        config = load_config(tmp_path)
        assert "fastapi" in config.libraries
        assert config.libraries["fastapi"].allowed_in == ["routers"]

    def test_orm_generates_restriction(self, tmp_path: Path) -> None:
        _write_config(tmp_path, '[tool.rivt]\norm = "sqlalchemy"\n')
        config = load_config(tmp_path)
        assert "sqlalchemy" in config.libraries
        assert config.libraries["sqlalchemy"].allowed_in == ["repositories", "models"]

    def test_http_client_generates_restriction(self, tmp_path: Path) -> None:
        _write_config(tmp_path, '[tool.rivt]\nhttp_client = "httpx"\n')
        config = load_config(tmp_path)
        assert "httpx" in config.libraries
        assert config.libraries["httpx"].allowed_in == ["clients"]

    def test_user_override_wins(self, tmp_path: Path) -> None:
        _write_config(
            tmp_path,
            "[tool.rivt]\n"
            "[tool.rivt.libraries.fastapi]\n"
            'allowed_in = ["routers", "services"]\n',
        )
        config = load_config(tmp_path)
        assert config.libraries["fastapi"].allowed_in == ["routers", "services"]


class TestConfigModule:
    def test_string_normalized_to_list(self, tmp_path: Path) -> None:
        _write_config(tmp_path, '[tool.rivt]\nconfig_module = "app/config.py"\n')
        config = load_config(tmp_path)
        assert config.config_module == ["app/config.py"]

    def test_list_preserved(self, tmp_path: Path) -> None:
        _write_config(tmp_path, '[tool.rivt]\nconfig_module = ["a.py", "b.py"]\n')
        config = load_config(tmp_path)
        assert config.config_module == ["a.py", "b.py"]


class TestLayerPaths:
    def test_string_path_normalized_to_list(self, tmp_path: Path) -> None:
        _write_config(
            tmp_path,
            '[tool.rivt]\n[tool.rivt.layers.models]\npaths = "app/models.py"\n',
        )
        config = load_config(tmp_path)
        assert config.layers["models"].paths == ["app/models.py"]

    def test_layer_without_paths_skipped(self, tmp_path: Path) -> None:
        _write_config(
            tmp_path,
            "[tool.rivt]\n[tool.rivt.layers.routers]\n",
        )
        config = load_config(tmp_path)
        assert "routers" not in config.layers
