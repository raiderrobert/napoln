Feature: Choose default agents
  As a developer with multiple AI coding tools installed
  I want to pick which agents napoln installs to by default
  So that `napoln add` does not spray skills across every detected tool

  Scenario: Setup persists default agents to config
    Given Claude Code and Cursor are installed
    When I run napoln setup with selection "claude-code"
    Then the config contains default_agents "claude-code"
    And the exit code is 0

  Scenario: Add respects configured default agents
    Given Claude Code and Cursor are installed
    And default_agents is configured to "claude-code"
    When I run napoln add with a valid local skill
    Then the skill is placed only for Claude Code
    And the exit code is 0

  Scenario: Add hints at setup when defaults are unset and multiple agents detected
    Given Claude Code and Cursor are installed
    And default_agents is not configured
    When I run napoln add with a valid local skill
    Then the output contains "napoln setup"
    And the exit code is 0

  Scenario: Setup with no agents detected fails with guidance
    Given no agents are installed
    When I run napoln setup non-interactively
    Then the output contains "No agents detected"
    And the exit code is 1
