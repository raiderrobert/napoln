# Changelog

## [0.2.3](https://github.com/raiderrobert/napoln/compare/v0.2.2...v0.2.3) (2026-04-15)


### Features

* mark already-installed skills as pre-checked in picker ([d615b58](https://github.com/raiderrobert/napoln/commit/d615b5814d3d13f56aeaff2ecacb4df1ce67c991))


### Bug Fixes

* distinct color for checked skill picker indicator ([3e0a0d6](https://github.com/raiderrobert/napoln/commit/3e0a0d6e560606a9a0c9b8ec0d0e1c2166b166bf))
* skill picker indicators render cleanly across terminals ([d257369](https://github.com/raiderrobert/napoln/commit/d257369fc15a97bb37afd4bf9137499e1ddebf61))
* **tests:** isolate cwd in CLI fixture to prevent project-scope leakage ([#15](https://github.com/raiderrobert/napoln/issues/15)) ([5b9c2e4](https://github.com/raiderrobert/napoln/commit/5b9c2e4321b81950d9e1ae89cf49a2de53d7ac4b))
* use ASCII checkbox indicators in skill picker ([c3c862a](https://github.com/raiderrobert/napoln/commit/c3c862afae8fc3b03ba5d406513c8ea8a23563e7))

## [0.2.2](https://github.com/raiderrobert/napoln/compare/v0.2.1...v0.2.2) (2026-04-14)


### Bug Fixes

* improve interactive skill picker display ([9cae2e7](https://github.com/raiderrobert/napoln/commit/9cae2e7aea70f7f70235b77e6174b925b0f4f679))
* skill picker highlight no longer fills entire line ([1492f43](https://github.com/raiderrobert/napoln/commit/1492f4344aa7f4f131dec0476a78c7425f6e2d61))

## [0.2.1](https://github.com/raiderrobert/napoln/compare/v0.2.0...v0.2.1) (2026-04-14)


### Bug Fixes

* don't hardcode version in test_version assertion ([443d4cc](https://github.com/raiderrobert/napoln/commit/443d4cc6dbcdc6cbe32b47a2e00e5ee95bd3b369))


### Documentation

* update README, ARCHITECTURE, CONTRIBUTING, AGENTS.md for 7-command CLI ([9d0ad9c](https://github.com/raiderrobert/napoln/commit/9d0ad9c26e200c89bdfe53afe6d18f987278e922))

## [0.2.0](https://github.com/raiderrobert/napoln/compare/v0.1.0...v0.2.0) (2026-04-14)


### ⚠ BREAKING CHANGES

* Removed commands: status, diff, resolve, sync, doctor, gc, telemetry.

### Features

* add --paths flag to list command ([90f2d86](https://github.com/raiderrobert/napoln/commit/90f2d8666cdcb7ef7bde13f72b0b5c7f2460134c))
* add --skill '*' for multi-skill repo installs ([a0ab2d4](https://github.com/raiderrobert/napoln/commit/a0ab2d4e0787ac3a9fca309826aef55375cd17f9))
* initial project structure and core modules ([27bb6b0](https://github.com/raiderrobert/napoln/commit/27bb6b0494305926964ef5fa54defbecaf409443))
* interactive skill picker for multi-skill repos ([aa8b14f](https://github.com/raiderrobert/napoln/commit/aa8b14f741e2ebc9db1b03f3ef1ee9d82d4a6f68))


### Bug Fixes

* catch ReflinkImpossibleError on Linux (ext4) ([094161c](https://github.com/raiderrobert/napoln/commit/094161cd18b800b8666be4e9879225118019cb17))
* don't update manifest/provenance when upgrade has conflicts ([2c62303](https://github.com/raiderrobert/napoln/commit/2c62303919c9e67fba450ef5d346c2cff22a09d0))
* list output formatting ([cf32983](https://github.com/raiderrobert/napoln/commit/cf329832b5edf220809bb241d62d21031475cb89))
* project-scope test needs explicit --agents on CI ([b22a9de](https://github.com/raiderrobert/napoln/commit/b22a9ded623d1b06326eaa1aee71fabde3cbbdea))
* rename --long to --verbose/-v for list command ([f9b203b](https://github.com/raiderrobert/napoln/commit/f9b203b2a932f9071be1e383d04033f4757e84e7))
* rename --paths to --long/-l for list command ([34c2ba5](https://github.com/raiderrobert/napoln/commit/34c2ba5d088c8aed9bb73c787ce4a1e9d1a45182))
* resolve git versions properly from tags, refs, or HEAD hash ([f0c161c](https://github.com/raiderrobert/napoln/commit/f0c161c33b6e2551bc4bbb242eb722af7a7cae2e))
* resolve test failures in CLI config and BDD agent detection ([6db5c26](https://github.com/raiderrobert/napoln/commit/6db5c263b28b6040edc4bf7f4e67f3e8a976bcce))
* show agent dirs (.claude, .cursor, .agents) in list header ([a8b9693](https://github.com/raiderrobert/napoln/commit/a8b9693607323027ccc90b06eac93a6abffff9e9))
* show agent names instead of paths in list header ([62ecd30](https://github.com/raiderrobert/napoln/commit/62ecd30f9330f50fa05200a10b208b3bdc6e7c3a))


### Documentation

* add brainstorm context prompt for resuming later ([36e24af](https://github.com/raiderrobert/napoln/commit/36e24afaf67b0cb67fd3e3570ae7a8bff881b222))
* clean up ARCHITECTURE.md language ([693221d](https://github.com/raiderrobert/napoln/commit/693221def9ca98185f1a889ca80b17a15b8fdc09))
* CLI redesign spec with BDD scenarios ([f7a3c4e](https://github.com/raiderrobert/napoln/commit/f7a3c4ee204edcf30d5fed50f92e872bc1880fa2))
* initial project vision and design principles ([8daaf93](https://github.com/raiderrobert/napoln/commit/8daaf9393937f499bd64ae18f5ac9c3f25386893))
* move design principles and prior art to ARCHITECTURE.md ([0608221](https://github.com/raiderrobert/napoln/commit/06082216d9559ae43c78c28e292bdd6e96720f5f))
* remove closing quote ([d5d32b2](https://github.com/raiderrobert/napoln/commit/d5d32b25b0d2f8b5b1e7d1cc4d43896dc55cab9b))
* rewrite README per writing-readmes skill ([de74e72](https://github.com/raiderrobert/napoln/commit/de74e72a1352749feba5a28cb81191e4c63381e9))
* rewrite README with real usage examples and Napoleon Dynamite quotes ([34629cb](https://github.com/raiderrobert/napoln/commit/34629cbb4cd1f2bf8ba087340dac3b688435c121))


### Code Refactoring

* reduce CLI from 13 commands to 7 ([3ab63e1](https://github.com/raiderrobert/napoln/commit/3ab63e185005cd676da2284b01e6bf2006a7c500))
