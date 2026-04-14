Feature: Status and diff
  As a developer
  I want to see what skills are installed and what I've changed
  So that I can manage my skills effectively

  Scenario: Status shows installed skills
    Given Claude Code is installed
    And a skill "test-skill" is installed
    When I run napoln status
    Then the output contains "test-skill"
    And the exit code is 0

  Scenario: Diff shows no changes for clean skill
    Given Claude Code is installed
    And a skill "test-skill" is installed
    When I run napoln diff test-skill
    Then the output contains "no local modifications"
    And the exit code is 0
