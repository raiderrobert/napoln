Feature: Initialize a skill
  As a skill author
  I want to scaffold a new skill quickly
  So that I have the correct structure from the start

  Scenario: Init with a name creates a subdirectory
    When I run napoln init with name "my-skill"
    Then "my-skill/SKILL.md" exists
    And the SKILL.md contains "name: my-skill"
    And the exit code is 0

  Scenario: Init refuses to overwrite existing SKILL.md
    Given a SKILL.md already exists at "my-skill"
    When I run napoln init with name "my-skill"
    Then the output contains "already exists"
    And the exit code is 1
