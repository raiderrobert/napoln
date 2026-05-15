Feature: Remove installed skills
  As a developer
  I want to remove skills I no longer need
  So that my agents only have relevant capabilities

  Scenario: Remove an installed skill
    Given Claude Code is installed
    And a skill "test-skill" is installed
    When I run napoln remove test-skill
    Then the output contains "Removed"
    And the skill is no longer placed for Claude Code
    And the exit code is 0

  Scenario: Remove a skill that is not installed
    Given Claude Code is installed
    And no skills are installed
    When I run napoln remove nonexistent
    Then the output contains "not installed"
    And the exit code is 0

  Scenario: Remove with dry run
    Given Claude Code is installed
    And a skill "test-skill" is installed
    When I run napoln remove test-skill --dry-run
    Then the output contains "Dry run"
    And the skill is still placed for Claude Code
    And the exit code is 0

  Scenario: Remove multiple skills at once
    Given Claude Code is installed
    And a skill "skill-one" is installed
    And a skill "skill-two" is installed
    When I run napoln remove skill-one skill-two
    Then "skill-one" is no longer placed for Claude Code
    And "skill-two" is no longer placed for Claude Code
    And the exit code is 0

  Scenario: Remove by source with --from-source
    Given Claude Code is installed
    And a skill "design-audit" is installed from "https://github.com/raiderrobert/flow"
    When I run napoln remove --from-source raiderrobert/flow
    Then "design-audit" is no longer placed for Claude Code
    And the exit code is 0
