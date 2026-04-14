Feature: Upgrade with three-way merge
  As a developer who has customized a skill
  I want to upgrade without losing my changes
  So that I get upstream improvements while keeping my customizations

  Scenario: Fast-forward when no local changes
    Given Claude Code is installed
    And a skill "test-skill" is installed
    And the placement is unmodified
    And a new version of the skill exists locally
    When I run napoln upgrade test-skill
    Then the placement is updated with the new version
    And the exit code is 0
