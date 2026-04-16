# Changelog

## [0.3.0](https://github.com/raiderrobert/napoln/compare/v0.2.5...v0.3.0) (2026-04-16)


### ⚠ BREAKING CHANGES

* Removed commands: status, diff, resolve, sync, doctor, gc, telemetry.

### Features

* add --paths flag to list command ([f08ef25](https://github.com/raiderrobert/napoln/commit/f08ef255b8a44d2dc6601b51b309fce65a3f1040))
* add --skill '*' for multi-skill repo installs ([9307e57](https://github.com/raiderrobert/napoln/commit/9307e574a04957fb83a1846d6318b18cc38deff3))
* add `napoln setup` to choose default agents ([#16](https://github.com/raiderrobert/napoln/issues/16)) ([173f581](https://github.com/raiderrobert/napoln/commit/173f58179af7bd8b459f8db326977c3c448c4c00))
* initial project structure and core modules ([16cbc5e](https://github.com/raiderrobert/napoln/commit/16cbc5ec4ae4a850ad8eed00e8c1909b54463b69))
* interactive skill picker for multi-skill repos ([4292b16](https://github.com/raiderrobert/napoln/commit/4292b16ad7a6d2958dfce6f08be8e08b749646e8))
* mark already-installed skills as pre-checked in picker ([6596b0c](https://github.com/raiderrobert/napoln/commit/6596b0cd090af703bdf1c3dcee6536354f404e97))


### Bug Fixes

* catch ReflinkImpossibleError on Linux (ext4) ([d1988d0](https://github.com/raiderrobert/napoln/commit/d1988d0204baa7e7e2c216788ac85df2a61b10eb))
* change bundled skill ([1ea7e2d](https://github.com/raiderrobert/napoln/commit/1ea7e2d1a270ba84f5dd922f0c0390006c0a153d))
* distinct color for checked skill picker indicator ([882b242](https://github.com/raiderrobert/napoln/commit/882b242f53cf8d772259e5903fa43f80c7df6981))
* don't hardcode version in test_version assertion ([263a3c9](https://github.com/raiderrobert/napoln/commit/263a3c9b5ba2f58970a0d91561e677d3db716d7a))
* don't update manifest/provenance when upgrade has conflicts ([0a1d780](https://github.com/raiderrobert/napoln/commit/0a1d780e02712a177a9a3b92acceb0168353b603))
* improve interactive skill picker display ([9e04865](https://github.com/raiderrobert/napoln/commit/9e0486578a1260b9fd8d6f57683953e99e9effad))
* list output formatting ([3e576d2](https://github.com/raiderrobert/napoln/commit/3e576d2995d813d9d60c37671eeafb92e58085e3))
* project-scope test needs explicit --agents on CI ([b4ddc3d](https://github.com/raiderrobert/napoln/commit/b4ddc3daebb59ab7a5da6d5c5eab4cb68aa9251b))
* rename --long to --verbose/-v for list command ([36351e7](https://github.com/raiderrobert/napoln/commit/36351e73433c08956455bb83f95447831cea3253))
* rename --paths to --long/-l for list command ([490c9ca](https://github.com/raiderrobert/napoln/commit/490c9caf5b01e83bb35185dc5fbea85f195f77ca))
* resolve git versions properly from tags, refs, or HEAD hash ([c97cb9a](https://github.com/raiderrobert/napoln/commit/c97cb9a00f1d8e0b1389ce5d03519efbc405ac6e))
* resolve test failures in CLI config and BDD agent detection ([0678308](https://github.com/raiderrobert/napoln/commit/06783088a15ac2577a5bd1716e962121e8d8620f))
* show agent dirs (.claude, .cursor, .agents) in list header ([72519b1](https://github.com/raiderrobert/napoln/commit/72519b1afd365e0cedb179bb4ec09d9c1c149703))
* show agent names instead of paths in list header ([c444690](https://github.com/raiderrobert/napoln/commit/c4446903babb8599369f63dc3df1ba713b11a225))
* skill picker highlight no longer fills entire line ([dabafec](https://github.com/raiderrobert/napoln/commit/dabafecb219c62a26689df4f6f95b2bd7b45e110))
* skill picker indicators render cleanly across terminals ([6a9cdb7](https://github.com/raiderrobert/napoln/commit/6a9cdb7f9b73b2ab2707fce845943c1353826117))
* **tests:** block PATH agent detection in upgrade tests ([79bb0f7](https://github.com/raiderrobert/napoln/commit/79bb0f7f4ca3beb005adce22ff1ecb659a9a741d))
* **tests:** isolate cwd in CLI fixture to prevent project-scope leakage ([#15](https://github.com/raiderrobert/napoln/issues/15)) ([6808ce9](https://github.com/raiderrobert/napoln/commit/6808ce90370f3668156d620905c41a2ca09cf66f))
* use ASCII checkbox indicators in skill picker ([8ddebd3](https://github.com/raiderrobert/napoln/commit/8ddebd3c2ea492795e630b361b8737243b5f4063))


### Documentation

* add asciinema demo to README ([cf1876b](https://github.com/raiderrobert/napoln/commit/cf1876bcd031535cf430d922951d780d5e39a66e))
* add GIF demo of agent installing skills ([41fc29a](https://github.com/raiderrobert/napoln/commit/41fc29afff326a7191ea6c9c040e88a40abc96a1))
* clean up ARCHITECTURE.md language ([9da32e2](https://github.com/raiderrobert/napoln/commit/9da32e28fefac742e8a39095d26d7df8048fb573))
* CLI redesign spec with BDD scenarios ([053b929](https://github.com/raiderrobert/napoln/commit/053b929c3a19b2c082b628c997d3b5d26cbe1ff9))
* move demo GIF to top of README ([6f7392d](https://github.com/raiderrobert/napoln/commit/6f7392d3f8aacbe358a454121001477a9cdf7646))
* move design principles and prior art to ARCHITECTURE.md ([4836725](https://github.com/raiderrobert/napoln/commit/4836725dd9a57ec5907e64c0dd8347a89aecbc8b))
* remove closing quote ([2165696](https://github.com/raiderrobert/napoln/commit/216569645ee296c883b4c91d9b2874d750d5dffa))
* remove spec mention ([2a44f93](https://github.com/raiderrobert/napoln/commit/2a44f933605a06f04e356263b0bb95b2fcb0ce53))
* reorg ([ef371b1](https://github.com/raiderrobert/napoln/commit/ef371b1a82b00973b39fe8c1905b01d1ebb7d5b5))
* restructure README like uv ([d3c93a5](https://github.com/raiderrobert/napoln/commit/d3c93a5437cdda67ef7da0c1bb3c9e2e8b271219))
* rewrite README per writing-readmes skill ([6d9bbe4](https://github.com/raiderrobert/napoln/commit/6d9bbe4b9105b3ec8bdbe9745ea48ac3a85d0783))
* rewrite README with real usage examples and Napoleon Dynamite quotes ([4179966](https://github.com/raiderrobert/napoln/commit/41799668a2f7255184b9e504453389a4871e701c))
* update README, ARCHITECTURE, CONTRIBUTING, AGENTS.md for 7-command CLI ([94f1e62](https://github.com/raiderrobert/napoln/commit/94f1e62f00ae0898763a364a6121ad8685a78e93))


### Code Refactoring

* reduce CLI from 13 commands to 7 ([56a8906](https://github.com/raiderrobert/napoln/commit/56a890659624875ee98fc74ad848de32d6001e74))

## [0.2.5](https://github.com/raiderrobert/napoln/compare/v0.2.4...v0.2.5) (2026-04-16)


### Bug Fixes

* change bundled skill ([dff4f1d](https://github.com/raiderrobert/napoln/commit/dff4f1d25b4dd2a0241f29b31507117a62a3620b))
* **tests:** block PATH agent detection in upgrade tests ([f656f33](https://github.com/raiderrobert/napoln/commit/f656f333ff1817e9218029b78b6c75f8faabe357))


### Documentation

* remove spec mention ([3c3386b](https://github.com/raiderrobert/napoln/commit/3c3386ba46d3eaf6893cdf2a1c002f734be460d8))

## [0.2.4](https://github.com/raiderrobert/napoln/compare/v0.2.3...v0.2.4) (2026-04-15)


### Features

* add `napoln setup` to choose default agents ([#16](https://github.com/raiderrobert/napoln/issues/16)) ([e8d78a6](https://github.com/raiderrobert/napoln/commit/e8d78a6f74c3c2dfa6fb02d422b594bbb324645b))

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
