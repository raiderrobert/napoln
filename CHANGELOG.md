# Changelog

## [0.3.0](https://github.com/raiderrobert/napoln/compare/v0.2.5...v0.3.0) (2026-04-16)


### ⚠ BREAKING CHANGES

* Removed commands: status, diff, resolve, sync, doctor, gc, telemetry.

### Features

* add --paths flag to list command ([0ba8cbe](https://github.com/raiderrobert/napoln/commit/0ba8cbefd7f7c7e5303e66650a17741b3dc5c45f))
* add --skill '*' for multi-skill repo installs ([d866edc](https://github.com/raiderrobert/napoln/commit/d866edcf3c885a77c2016dec6c290fcd031f570e))
* add `napoln setup` to choose default agents ([#16](https://github.com/raiderrobert/napoln/issues/16)) ([6c288a0](https://github.com/raiderrobert/napoln/commit/6c288a0f05ea67c5cf9de0a8f5e905666564a245))
* initial project structure and core modules ([10bcc86](https://github.com/raiderrobert/napoln/commit/10bcc861771f1cbef64f6dd67a1fa943d6fecec4))
* interactive skill picker for multi-skill repos ([e7b9522](https://github.com/raiderrobert/napoln/commit/e7b9522afba7b5484dc46ddcf2ef77a4e66a8fe3))
* mark already-installed skills as pre-checked in picker ([5655f78](https://github.com/raiderrobert/napoln/commit/5655f7862d3e5ff0913b3cd03990d1aad8e9bb7d))


### Bug Fixes

* catch ReflinkImpossibleError on Linux (ext4) ([9efff2d](https://github.com/raiderrobert/napoln/commit/9efff2d9b7b91811bc090a029073f41a5368050a))
* change bundled skill ([334b277](https://github.com/raiderrobert/napoln/commit/334b2778ed4931bd2e2769ccf5df5bd0ca15b91b))
* distinct color for checked skill picker indicator ([80e6ba6](https://github.com/raiderrobert/napoln/commit/80e6ba6ffcb50d7f966ca2e01db69e64a2744606))
* don't hardcode version in test_version assertion ([f37258f](https://github.com/raiderrobert/napoln/commit/f37258f4fb518dfa223dd9e46d975e0bbfba9472))
* don't update manifest/provenance when upgrade has conflicts ([5863ae4](https://github.com/raiderrobert/napoln/commit/5863ae4dbafd8141944c2f7948cd4093c793412d))
* improve interactive skill picker display ([9a589fc](https://github.com/raiderrobert/napoln/commit/9a589fc49b0d84a6e108320979882c0beeaedb14))
* list output formatting ([ee353f4](https://github.com/raiderrobert/napoln/commit/ee353f4d571a7d99a12f021eeee4c8756113f1d4))
* project-scope test needs explicit --agents on CI ([46abeaa](https://github.com/raiderrobert/napoln/commit/46abeaa49373b10b847d5e014911ecfe4a69bf59))
* rename --long to --verbose/-v for list command ([5aa6eb2](https://github.com/raiderrobert/napoln/commit/5aa6eb25246ac0c8f6851c2a611a8922848da2b4))
* rename --paths to --long/-l for list command ([189e02b](https://github.com/raiderrobert/napoln/commit/189e02b480688fe7c3de73d434d0c59c4d8a25ff))
* resolve git versions properly from tags, refs, or HEAD hash ([a2a6ba5](https://github.com/raiderrobert/napoln/commit/a2a6ba5a894357cbe23a2b09dd4ba9b69900c565))
* resolve test failures in CLI config and BDD agent detection ([bbf2dce](https://github.com/raiderrobert/napoln/commit/bbf2dceeabd776fa005d0828b9a76e93a08b0558))
* show agent dirs (.claude, .cursor, .agents) in list header ([7dc13f0](https://github.com/raiderrobert/napoln/commit/7dc13f070c519f514eff16598287a96dc9781399))
* show agent names instead of paths in list header ([1af3740](https://github.com/raiderrobert/napoln/commit/1af37408ab683936b84f966f8597aa714af55e6c))
* skill picker highlight no longer fills entire line ([d69a097](https://github.com/raiderrobert/napoln/commit/d69a0978f0222fda62595e459ab7f6cfa0dfdc49))
* skill picker indicators render cleanly across terminals ([6ac28bc](https://github.com/raiderrobert/napoln/commit/6ac28bc538bece3ab0663ac709a567db1058950a))
* **tests:** block PATH agent detection in upgrade tests ([05a0981](https://github.com/raiderrobert/napoln/commit/05a0981cf66df21a56e5c3185ae7ebfa96ea363c))
* **tests:** isolate cwd in CLI fixture to prevent project-scope leakage ([#15](https://github.com/raiderrobert/napoln/issues/15)) ([85f3129](https://github.com/raiderrobert/napoln/commit/85f3129a82029275ea07cbed68e967866a4332c5))
* use ASCII checkbox indicators in skill picker ([aed52b7](https://github.com/raiderrobert/napoln/commit/aed52b76c7f1b19513ef3f8b8ff93747e9f21450))


### Documentation

* add asciinema demo to README ([aed97a8](https://github.com/raiderrobert/napoln/commit/aed97a812b62050123ed8f73a0a047a623d18bf1))
* add GIF demo of agent installing skills ([837cf05](https://github.com/raiderrobert/napoln/commit/837cf056abcf83cc7c447cfec0b2c2d496d346bc))
* clean up ARCHITECTURE.md language ([6662024](https://github.com/raiderrobert/napoln/commit/66620244de40298d93340091979f0d3268aba80c))
* CLI redesign spec with BDD scenarios ([7cb4532](https://github.com/raiderrobert/napoln/commit/7cb453215538ea0c236233af9a8ac663b5a48713))
* move demo GIF to top of README ([fcad6bd](https://github.com/raiderrobert/napoln/commit/fcad6bdd1abfba142493d4a5c08ab379fbb1bcb0))
* move design principles and prior art to ARCHITECTURE.md ([548c300](https://github.com/raiderrobert/napoln/commit/548c3004265c7bee2047b8ff7630aa6697972483))
* remove closing quote ([1ad1e7f](https://github.com/raiderrobert/napoln/commit/1ad1e7f1622bf052346d1ae46d1e211baa798320))
* remove spec mention ([8576a81](https://github.com/raiderrobert/napoln/commit/8576a81ebcaf237c5f6a1d454939c8311c8db4c6))
* reorg ([eb3156a](https://github.com/raiderrobert/napoln/commit/eb3156a6076c520f1a943b0c9ad746b84ac9247e))
* restructure README like uv ([56baece](https://github.com/raiderrobert/napoln/commit/56baece381d13b7e7ad8084e599475879dbfd7e2))
* rewrite README per writing-readmes skill ([594dc68](https://github.com/raiderrobert/napoln/commit/594dc68db9dc9d823a3f3874a95f29e00ca272f4))
* rewrite README with real usage examples and Napoleon Dynamite quotes ([0cc78e7](https://github.com/raiderrobert/napoln/commit/0cc78e7277af76ebfc0728a8ed37dc4d66a5d27e))
* update README, ARCHITECTURE, CONTRIBUTING, AGENTS.md for 7-command CLI ([46c735b](https://github.com/raiderrobert/napoln/commit/46c735b6b5ac391a8073c32e19231539e3a5e3f0))


### Code Refactoring

* reduce CLI from 13 commands to 7 ([2128a5c](https://github.com/raiderrobert/napoln/commit/2128a5cc2eb0d03c3575013dd4c33377c6da97e5))

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
