Feature: Health check
  As a developer
  I want to verify my napoln installation is healthy
  So that I can trust my skills are properly managed

  Scenario: Doctor reports healthy state
    Given Claude Code is installed
    And a skill "test-skill" is installed
    When I run napoln doctor
    Then the output contains checks passed
    And the exit code is 0
