Feature: Skill installation
  As a developer
  I want to install skills from local paths
  So that I can use them in my agents

  Scenario: Install from local path
    Given Claude Code is installed
    And a local skill exists at a test path
    When I run napoln add with the local skill
    Then the skill is stored in the content-addressed store
    And the skill is placed in the Claude Code skills directory
    And the manifest contains the skill
    And the exit code is 0

  Scenario: Install with dry run
    Given Claude Code is installed
    And a local skill exists at a test path
    When I run napoln add with dry run
    Then no skills are stored
    And no placements are created
    And the output contains "Dry run"
    And the exit code is 0
