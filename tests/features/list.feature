Feature: List installed skills
  As a developer
  I want to see what skills are installed and where
  So that I can understand what my agents have access to

  Scenario: List with no skills installed
    Given Claude Code is installed
    When I run napoln list
    Then the output contains "No skills installed"
    And the exit code is 0

  Scenario: List shows installed skills
    Given Claude Code is installed
    And a skill "test-skill" is installed
    When I run napoln list
    Then the output contains "test-skill"
    And the exit code is 0

  Scenario: List with --json produces valid JSON
    Given Claude Code is installed
    And a skill "test-skill" is installed
    When I run napoln list --json
    Then the output is valid JSON with "test-skill" in global
    And the exit code is 0
