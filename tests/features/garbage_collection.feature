Feature: Garbage collection
  As a developer
  I want to clean up unused store entries
  So that I don't waste disk space

  Scenario: GC with nothing to collect
    Given Claude Code is installed
    And a skill "test-skill" is installed
    When I run napoln gc
    Then the output contains "No unreferenced"
    And the exit code is 0

  Scenario: GC dry run
    Given Claude Code is installed
    And a skill "test-skill" is installed
    When I run napoln gc with dry run
    Then the output contains "Dry run"
    And the exit code is 0
