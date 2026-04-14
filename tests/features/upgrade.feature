Feature: Upgrade with three-way merge
  As a developer who has customized a skill
  I want to upgrade without losing my changes
  So that I get upstream improvements while keeping my customizations

  # Case (a): OURS == BASE → fast-forward
  Scenario: Fast-forward when no local changes
    Given Claude Code is installed
    And a skill "test-skill" is installed at version "1.0.0"
    And the Claude Code placement is unmodified
    And upstream has released version "2.0.0" with a new section
    When I run napoln upgrade test-skill
    Then the Claude Code placement contains the new upstream content
    And the Claude Code placement does not contain conflict markers
    And the manifest version is "2.0.0"
    And the exit code is 0

  # Case (b): OURS != BASE, no conflicts with THEIRS → clean merge
  Scenario: Clean merge when local and upstream changes do not overlap
    Given Claude Code is installed
    And a skill "test-skill" is installed at version "1.0.0"
    And the Claude Code placement has local changes at the end
    And upstream has released version "2.0.0" with changes at the beginning
    When I run napoln upgrade test-skill
    Then the Claude Code placement contains both local and upstream changes
    And the Claude Code placement does not contain conflict markers
    And the exit code is 0

  # Case (c): OURS != BASE, conflicts with THEIRS → conflict markers
  Scenario: Conflict when local and upstream change the same lines
    Given Claude Code is installed
    And a skill "test-skill" is installed at version "1.0.0"
    And the Claude Code placement has local changes on line 5
    And upstream has released version "2.0.0" with different changes on line 5
    When I run napoln upgrade test-skill
    Then the Claude Code placement contains conflict markers
    And the manifest version is "1.0.0"
    And the output contains "Conflicts"
    And the exit code is 2

  # Case (d): non-SKILL.md files → replace if unchanged, warn if modified
  Scenario: Supporting files replaced if unchanged
    Given Claude Code is installed
    And a skill "test-skill" with a script is installed at version "1.0.0"
    And the script in the Claude Code placement is unmodified
    And upstream has released version "2.0.0" with an updated script
    When I run napoln upgrade test-skill
    Then the script in the Claude Code placement matches the new upstream
    And the exit code is 0

  Scenario: Supporting files kept when locally modified
    Given Claude Code is installed
    And a skill "test-skill" with a script is installed at version "1.0.0"
    And the script in the Claude Code placement has local changes
    And upstream has released version "2.0.0" with an updated script
    When I run napoln upgrade test-skill
    Then the script in the Claude Code placement retains local changes
    And the manifest version is "1.0.0"
    And the exit code is 2
