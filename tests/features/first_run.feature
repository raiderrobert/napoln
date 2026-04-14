Feature: First run experience
  As a developer using Claude Code
  I want to install my first skill with minimal friction
  So that I can extend my agents' capabilities

  Scenario: First run bootstraps napoln and installs a skill
    Given Claude Code is installed
    And napoln has never been run
    When I run napoln add with a valid local skill
    Then the napoln home directory is created
    And the skill is stored in the content-addressed store
    And the skill is placed in the Claude Code skills directory
    And the exit code is 0

  Scenario: First run with no agents detected
    Given no agents are installed
    And napoln has never been run
    When I run napoln add with a valid local skill and no agents
    Then the output contains "No agents detected"
    And the exit code is 1
