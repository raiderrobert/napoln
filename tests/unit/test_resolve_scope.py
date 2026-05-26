"""Tests for scope resolution in napoln.core.project."""

from __future__ import annotations


from napoln.core.project import resolve_scope


class TestResolveScope:
    """Scope resolution: explicit flags → config → project detection."""

    def test_explicit_global_flag(self, tmp_path):
        assert resolve_scope(global_flag=True, project_flag=False, cwd=tmp_path) == "global"

    def test_explicit_project_flag(self, tmp_path):
        assert resolve_scope(global_flag=False, project_flag=True, cwd=tmp_path) == "project"

    def test_both_flags_explicit_global_wins(self, tmp_path):
        """If both flags are passed, global takes precedence."""
        assert resolve_scope(global_flag=True, project_flag=True, cwd=tmp_path) == "global"

    def test_no_flags_inside_project(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        assert resolve_scope(global_flag=False, project_flag=False, cwd=repo) == "project"

    def test_no_flags_outside_project(self, tmp_path):
        outside = tmp_path / "outside"
        outside.mkdir()
        assert resolve_scope(global_flag=False, project_flag=False, cwd=outside) == "global"

    def test_config_default_global_overrides_detection(self, tmp_path):
        """If config says global and no explicit flags, use global even in a project."""
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        assert (
            resolve_scope(global_flag=False, project_flag=False, cwd=repo, config_default="global")
            == "global"
        )

    def test_config_default_project_outside_project(self, tmp_path):
        """If config says project but we're outside a project, fall back to global."""
        outside = tmp_path / "outside"
        outside.mkdir()
        assert (
            resolve_scope(
                global_flag=False, project_flag=False, cwd=outside, config_default="project"
            )
            == "global"
        )

    def test_explicit_flag_overrides_config(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        assert (
            resolve_scope(global_flag=False, project_flag=True, cwd=repo, config_default="global")
            == "project"
        )
