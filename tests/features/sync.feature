Feature: Sync skill placements from manifests
  As a developer joining a project
  I want to run napoln install to restore skills from the manifest
  So that I get the same skill setup as my teammates

  Scenario: Install when everything is in sync
    Given Claude Code is installed
    And a skill "test-skill" is installed
    When I run napoln install --global
    Then the output contains "up to date"
    And the exit code is 0

  Scenario: Install with no manifests
    Given Claude Code is installed
    And napoln home exists but has no manifest
    When I run napoln install --global
    Then the output contains "No manifests"
    And the exit code is 0

  Scenario: Install with dry run
    Given Claude Code is installed
    And a skill "test-skill" is installed
    When I run napoln install --global --dry-run
    Then the output contains "Dry run"
    And the exit code is 0

  Scenario: Install restores skills from project manifest
    Given Claude Code is installed
    And a project manifest references "test-skill" from a local source
    And the store is empty
    And no placements exist
    When I run napoln install --project
    Then the output contains "Restored"
    And the skill is placed in the Claude Code skills directory
    And the exit code is 0
