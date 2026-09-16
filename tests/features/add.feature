Feature: Add a skill
  As a developer
  I want to install skills from local paths and git sources
  So that I can use them in my agents

  Scenario: Add from local path
    Given Claude Code is installed
    And a local skill exists at a test path
    When I run napoln add with the local skill
    Then the skill is stored in the content-addressed store
    And the skill is placed in the Claude Code skills directory
    And the manifest contains the skill
    And the exit code is 0

  Scenario: Add with dry run
    Given Claude Code is installed
    And a local skill exists at a test path
    When I run napoln add with dry run
    Then no skills are stored
    And no placements are created
    And the output contains "Dry run"
    And the exit code is 0

  Scenario: Add the same skill twice is idempotent
    Given Claude Code is installed
    And a skill "test-skill" is already installed
    When I run napoln add with the same skill again
    Then the output contains "already installed"
    And the exit code is 0

  Scenario: Add with explicit agent flag
    Given Claude Code is installed
    And a local skill exists at a test path
    When I run napoln add with --agents claude-code
    Then the skill is placed in the Claude Code skills directory
    And the exit code is 0

  Scenario: Add a registry identifier before registry is available
    Given Claude Code is installed
    When I run napoln add with a bare name "my-skill"
    Then the output contains "not yet available"
    And the exit code is 1

  Scenario: Add with project scope
    Given Claude Code is installed
    And a local skill exists at a test path
    When I run napoln add with --project --agents claude-code
    Then the project manifest contains the skill
    And the exit code is 0

  Scenario: Add all skills from a subdirectory of a multi-bundle repo
    Given Claude Code is installed
    And a cached git repo "owner/repo" with bundles "bundle-a:alpha,beta" and "bundle-b:gamma"
    When I run napoln add "owner/repo/bundle-a/skills" with --all
    Then the manifest contains skills "alpha,beta"
    And the manifest does not contain skills "gamma"
    And the manifest source for "alpha" is "github.com/owner/repo/bundle-a/skills/alpha"
    And the exit code is 0

  Scenario: Add a named skill from a subdirectory of a multi-bundle repo
    Given Claude Code is installed
    And a cached git repo "owner/repo" with bundles "bundle-a:alpha,beta" and "bundle-b:gamma"
    When I run napoln add "owner/repo/bundle-a/skills" with --skill "beta"
    Then the manifest contains skills "beta"
    And the manifest does not contain skills "alpha,gamma"
    And the exit code is 0

  Scenario: Add from a subdirectory that has no skills
    Given Claude Code is installed
    And a cached git repo "owner/repo" with bundles "bundle-a:alpha,beta" and "bundle-b:gamma"
    When I run napoln add "owner/repo/docs" with --all
    Then the output contains "does not exist"
    And the exit code is 1
