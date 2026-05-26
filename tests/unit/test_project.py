"""Tests for napoln.core.project — project detection."""

from __future__ import annotations


from napoln.core.project import is_inside_project, load_config_default_scope


class TestIsInsideProject:
    def test_inside_git_repo(self, tmp_path):
        project = tmp_path / "repo"
        project.mkdir()
        (project / ".git").mkdir()
        assert is_inside_project(project) is True

    def test_inside_git_submodule(self, tmp_path):
        project = tmp_path / "repo"
        project.mkdir()
        (project / ".git").write_text("gitdir: ../.git/modules/repo")
        assert is_inside_project(project) is True

    def test_inside_napoln_project(self, tmp_path):
        project = tmp_path / "my-project"
        project.mkdir()
        (project / ".napoln").mkdir()
        assert is_inside_project(project) is True

    def test_inside_claude_project(self, tmp_path):
        project = tmp_path / "repo"
        project.mkdir()
        (project / ".claude").mkdir()
        assert is_inside_project(project) is True

    def test_inside_nested_git_repo(self, tmp_path):
        project = tmp_path / "repo" / "src"
        project.mkdir(parents=True)
        (tmp_path / "repo" / ".git").mkdir()
        assert is_inside_project(project) is True

    def test_outside_any_project(self, tmp_path):
        outside = tmp_path / "outside"
        outside.mkdir()
        assert is_inside_project(outside) is False

    def test_empty_directory(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        assert is_inside_project(empty) is False


class TestLoadConfigDefaultScope:
    def test_reads_project_default(self, tmp_path):
        napoln_home = tmp_path / ".napoln"
        napoln_home.mkdir()
        (napoln_home / "config.toml").write_text('[napoln]\ndefault_scope = "project"\n')
        assert load_config_default_scope(napoln_home) == "project"

    def test_reads_global_default(self, tmp_path):
        napoln_home = tmp_path / ".napoln"
        napoln_home.mkdir()
        (napoln_home / "config.toml").write_text('[napoln]\ndefault_scope = "global"\n')
        assert load_config_default_scope(napoln_home) == "global"

    def test_returns_none_when_missing(self, tmp_path):
        napoln_home = tmp_path / ".napoln"
        napoln_home.mkdir()
        assert load_config_default_scope(napoln_home) is None

    def test_returns_none_when_invalid(self, tmp_path):
        napoln_home = tmp_path / ".napoln"
        napoln_home.mkdir()
        (napoln_home / "config.toml").write_text('[napoln]\ndefault_scope = "invalid"\n')
        assert load_config_default_scope(napoln_home) is None
