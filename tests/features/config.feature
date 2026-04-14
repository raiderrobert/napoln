Feature: Configuration and housekeeping
  As a developer
  I want to view my napoln configuration and clean up storage
  So that I can understand and maintain my setup

  Scenario: Show config
    Given Claude Code is installed
    And napoln is initialized
    When I run napoln config
    Then the output contains "Home"
    And the exit code is 0

  Scenario: Doctor reports healthy state
    Given Claude Code is installed
    And a skill "test-skill" is installed
    When I run napoln config doctor
    Then the output contains checks passed
    And the exit code is 0

  Scenario: GC with nothing to collect
    Given Claude Code is installed
    And a skill "test-skill" is installed
    When I run napoln config gc
    Then the output contains "No unreferenced"
    And the exit code is 0

  Scenario: GC dry run
    Given Claude Code is installed
    And a skill "test-skill" is installed
    When I run napoln config gc --dry-run
    Then the output contains "Dry run"
    And the exit code is 0
