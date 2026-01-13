# CHANGELOG


## v6.2.8 (2026-01-13)

### Fixes

* fix: publishing error during actions ([`1f91491`](https://github.com/megalus/lamina/commit/1f91491762bd3a7fe1acd4da6ee2cc626b8896d4))


## v6.2.7 (2026-01-13)

### Fixes

* fix: add support for Pydantic Literal type and enhance OpenAPI schema representation ([`f7cdd14`](https://github.com/megalus/lamina/commit/f7cdd1401a85469ae5d12004a640680ada08501b))


## v6.2.6 (2026-01-13)

### Fixes

* fix: improve OpenAPI type representation for arrays and unions in schema ([`dcb3f43`](https://github.com/megalus/lamina/commit/dcb3f43eeb7f2fa783e2a7fa89425e5668c9e9e8))


## v6.2.5 (2026-01-09)

### Unknown

* Merge remote-tracking branch 'origin/main' ([`34783c6`](https://github.com/megalus/lamina/commit/34783c6c079e27a7661d6647e46dacd449396571))


## v6.2.4 (2026-01-09)

### Fixes

* fix: enhance Markdown output with horizontal rules and bold formatting for fields ([`f6a34c5`](https://github.com/megalus/lamina/commit/f6a34c510d8ccac9e540040bafbf1c6459f14eab))

### Unknown

* Merge remote-tracking branch 'origin/main' ([`61f31b1`](https://github.com/megalus/lamina/commit/61f31b151de84a96dd89ad36dcd5afb930b6de45))


## v6.2.3 (2026-01-09)

### Fixes

* fix: add field `doc_examples` and fix tests ([`cec7d27`](https://github.com/megalus/lamina/commit/cec7d27dd6d5cb38b4cc90fd12f13bd402ce0f39))

### Unknown

* Merge remote-tracking branch 'origin/main' ([`a53dee3`](https://github.com/megalus/lamina/commit/a53dee3db40fc990a600130235a341db5062b8a7))


## v6.2.2 (2026-01-09)

### Fixes

* fix: make horizontal line optional ([`fbcdb89`](https://github.com/megalus/lamina/commit/fbcdb89d1ff64c3e32c667646e4e9bc3142f3954))

* fix: add horizontal rule to Markdown conversion output ([`fa8ab71`](https://github.com/megalus/lamina/commit/fa8ab71ffab13d022b9e7298c9e7764901a1a115))


## v6.2.1 (2026-01-06)

### Fixes

* fix: parse of required and non-required fields in OpenAPI schema ([`ea4a3cb`](https://github.com/megalus/lamina/commit/ea4a3cbc00c358eb86f928d8b89de8a84dc41db7))


## v6.2.0 (2025-12-22)

### Features

* feat: add automatic generation of Markdown tables for Pydantic models in documentation ([`c12b7a4`](https://github.com/megalus/lamina/commit/c12b7a46d7e55f619b36e6ce3120d25242add6d0))


## v6.1.0 (2025-11-19)

### Features

* feat: enhance OpenAPI support with custom error responses and markdown conversion ([`12e9598`](https://github.com/megalus/lamina/commit/12e9598079d73a350db89f6ef2dc16718b12c22b))


## v6.0.1 (2025-09-26)

### Fixes

* fix: implement OpenAPI specification generation with enhanced decorator support ([`1a7300d`](https://github.com/megalus/lamina/commit/1a7300df6da32f71a3e6544546b557be6f1ab1a9))


## v6.0.0 (2025-09-23)

### Breaking

* feat!: add OpenAPI specification generation and support for query parameters.

This is a BREAKING CHANGE feature. ([`d6e0e7c`](https://github.com/megalus/lamina/commit/d6e0e7c14e0eb7689bca0a4492c737f2d6af322f))

### Unknown

* tests: add missing test ([`8b47d48`](https://github.com/megalus/lamina/commit/8b47d480c04b4420ce0320d037b88fb9398369df))


## v5.0.2 (2025-09-14)

### Fixes

* fix: missing schemas to wrapper ([`71c8f88`](https://github.com/megalus/lamina/commit/71c8f8872590abc130ed9469208eccfefe31523e))


## v5.0.1 (2025-09-12)

### Fixes

* fix: content type and dumping ([`06ac49b`](https://github.com/megalus/lamina/commit/06ac49be6d8fb7640be7582d7047fb655a0c4d59))


## v5.0.0 (2025-09-12)

### Breaking

* feat!: v.5.0 - BREAKING CHANGE

* Autodetect MIME type. Use `content_type` parameter to override.
* Add support to RootModel
* Refactor hooks logic ([`d279206`](https://github.com/megalus/lamina/commit/d2792069f332dbb46347693b165f10e13d50b504))


## v4.0.0 (2025-09-09)

### Breaking

* feat!: v.4.0 - BREAKING CHANGE ([`18fa561`](https://github.com/megalus/lamina/commit/18fa561dd0f34aeb3263334df720344aac36d23c))

### Chores

* chore: fix precommit ([`0cb1175`](https://github.com/megalus/lamina/commit/0cb117587a1d573ce572f6aaab6f3d92a26a225b))

### Continuous Integration

* ci: add edit runs ([`a8c3914`](https://github.com/megalus/lamina/commit/a8c3914633b694e2c4dd66a2fd2749482fae1d2d))

* ci: remove docs in actions ([`44cc5c6`](https://github.com/megalus/lamina/commit/44cc5c6ae364bbac68fefde3a68eff0640db8b54))

### Documentation

* docs: update coding guidelines and README formatting ([`fa8f4e6`](https://github.com/megalus/lamina/commit/fa8f4e68eed1660a2cf9e43f13212432b02e5cf4))

* docs: enhance README and add project guidelines

Updated the README to include detailed usage examples, installation steps, and project architecture with a mermaid diagram. Added a `guidelines.md` file for contributor instructions and coding standards. ([`77db480`](https://github.com/megalus/lamina/commit/77db480c68ea220da9ffead9300bcb53c531fa44))


## v3.0.0 (2024-10-09)

### Breaking

* ci!: Add support to Python 3.13

This is a BREAKING CHANGE commit. ([`6204f77`](https://github.com/megalus/lamina/commit/6204f7769709d6b4713ad4a50dd1bb1ba72c3e3f))


## v2.3.2 (2024-10-04)

### Fixes

* fix: event in step function ([`f743f03`](https://github.com/megalus/lamina/commit/f743f03efc7dd44f9bd67ad0b5a2987656e3254f))


## v2.3.1 (2024-10-04)

### Fixes

* fix: error in logs ([`0a276f1`](https://github.com/megalus/lamina/commit/0a276f120be87b07234692a4b68aa13e1c556bf9))


## v2.3.0 (2024-10-03)

### Features

* feat: add step functions arg ([`c254e07`](https://github.com/megalus/lamina/commit/c254e0765aa1a26331c388d98cb0d1d39dbcf146))


## v2.2.0 (2024-10-03)

### Features

* feat: add step functions arg ([`bca06e6`](https://github.com/megalus/lamina/commit/bca06e6fd5167e845f9b1120e06e074a2eb53ddc))

* feat: add step functions arg ([`3a9b73f`](https://github.com/megalus/lamina/commit/3a9b73fe4d8568de434f03ea9348d44046dc34b7))


## v2.1.1 (2024-09-02)

### Fixes

* fix: return generic error message as json ([`ebfc19c`](https://github.com/megalus/lamina/commit/ebfc19c03175218783609a0ab58dd974300c61d0))


## v2.1.0 (2024-09-02)

### Features

* feat: logger internal server error exception ([`0b259e4`](https://github.com/megalus/lamina/commit/0b259e449da29895444c267f3c3646e90967a5b6))


## v2.0.2 (2023-10-03)

### Fixes

* fix: pyproject.toml python versions ([`d4b9894`](https://github.com/megalus/lamina/commit/d4b989475140d91c9f13b45fd895c456c7f95f44))


## v2.0.1 (2023-10-03)

### Fixes

* fix: fix pyproject.toml python versions ([`ad798ad`](https://github.com/megalus/lamina/commit/ad798ad6f9e00e23e306b71a9be53b2680677c22))


## v2.0.0 (2023-10-03)

### Breaking

* feat!: Update Python version support

This is a BREAKING CHANGE commit:

* Remove Python 3.9
* Add Python 3.12 ([`960848c`](https://github.com/megalus/lamina/commit/960848c8cb79b846938a73064520148dfb9100f5))

### Continuous Integration

* ci: fix pre-commit issues ([`65a4b87`](https://github.com/megalus/lamina/commit/65a4b87103f3a860c99d8926c64e3d1949b019d2))

### Unknown

* Merge pull request #1 from megalus/develop

Update Python Versions ([`30dfcd8`](https://github.com/megalus/lamina/commit/30dfcd87a32c59b87ece3d899b04fcfe7d475d63))


## v1.2.1 (2023-09-21)

### Fixes

* fix: normalize import method from package ([`e64a404`](https://github.com/megalus/lamina/commit/e64a40435d1b3f9a85c76fd74ac62da84e5886ec))


## v1.2.0 (2023-09-21)

### Unknown

* Merge remote-tracking branch 'origin/main' ([`ef7959d`](https://github.com/megalus/lamina/commit/ef7959dc4a9add8ad94c56621bbe2607d8e0b12a))


## v1.1.0 (2023-09-21)

### Features

* feat: Add custom headers support and content type updates for lamina

Custom header support has been added to the "lamina" decorator. Now, on returning a dictionary consisting of headers in the tuple, it gets merged with the existing headers. This will provide users with the ability to add custom values to the response headers.

In addition, updates were made to the content type handling. Content type can now be optionally defined for the decorated functions. Changes were made to the return statement of the response.

New tests were added to validate these changes and updates to the README were made to document the new feature and changes. ([`9cec3b6`](https://github.com/megalus/lamina/commit/9cec3b6dd9fe2792d7f99a16fff2941bbfe42e2b))

### Unknown

* Merge remote-tracking branch 'origin/main' ([`1abaea9`](https://github.com/megalus/lamina/commit/1abaea9b7803a6b4375ae580e85d6553293bd5e4))


## v1.0.4 (2023-08-30)

### Features

* feat: Add support for content type declaration in lamina decorator

This commit introduces a new optional parameter `content_type` in the `lamina` decorator, which allows selecting the desired content type (JSON, HTML, or TEXT). Previously, the content type was hard-coded as "application/json; charset=utf-8".

The new `Lamina` enum was introduced in the `helpers.py` file to manage content-type options.

Additionally, new unit tests were added to the `test_content_type.py` for testing the newly introduced feature. ([`15f4dfb`](https://github.com/megalus/lamina/commit/15f4dfbca6a9e6385cd61e2c52e94aa90198a22e))

### Fixes

* fix: remove poetry.lock from lib ([`779db8e`](https://github.com/megalus/lamina/commit/779db8e6607caf01df5ed8c55a5876551f22a6b5))

### Unknown

* Merge remote-tracking branch 'origin/main' ([`cea8573`](https://github.com/megalus/lamina/commit/cea8573126749a0038a9d6e7308455da3d03d4c7))


## v1.0.3 (2023-08-29)

### Continuous Integration

* ci: update pre-commit ([`1ac6f02`](https://github.com/megalus/lamina/commit/1ac6f02d371468472f8de9621f03a4ff78b3f049))

### Fixes

* fix: return Validation Errors during response serialization as an Internal Server Error ([`ee9eef6`](https://github.com/megalus/lamina/commit/ee9eef63fc53a4c8365abcaa0bed74a317899930))


## v1.0.2 (2023-08-28)

### Unknown

* Merge remote-tracking branch 'origin/main' ([`28603e4`](https://github.com/megalus/lamina/commit/28603e40614961e5cb72cae45fa4d8052377ac88))


## v1.0.1 (2023-08-28)

### Continuous Integration

* ci: change package name to avoid duplication error ([`95eb3c0`](https://github.com/megalus/lamina/commit/95eb3c0797c3a80e6f7ff6649a083587f4a27878))

### Fixes

* fix: add missing asyncio helper for running sync methods in asynchronous code. ([`f9ae6f2`](https://github.com/megalus/lamina/commit/f9ae6f2c7c30b77205b96c61d63665214ea0667d))

* fix: Change Pypi package name to `py-lamina` ([`75ccf12`](https://github.com/megalus/lamina/commit/75ccf126b55027b634582741d3140385ebd9505c))


## v1.0.0 (2023-08-28)

### Breaking

* feat!: Add first public version

BREAKING CHANGE: Please check README.md for installing and usage this library. ([`cc2aca7`](https://github.com/megalus/lamina/commit/cc2aca7c788be9fddbe80aaeb5bf6df363880252))

### Continuous Integration

* ci: normalize initial version ([`dff3b69`](https://github.com/megalus/lamina/commit/dff3b69d84b62a1f38c07b62e0d6df98c6e9a9d9))

### Unknown

* Initial commit ([`4d1e58a`](https://github.com/megalus/lamina/commit/4d1e58afae69b6e9bb1e0b21a27e7cb38a42fc00))
