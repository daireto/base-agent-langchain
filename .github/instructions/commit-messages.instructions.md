---
applyTo: '**'
---

Generate a conventional commit message in English following this exact format:

<format>
type(scope): subject in imperative mood, lowercase, no period, max 48 chars

Detailed description of changes made, including context,
reason for changes, and any important implementation details.
This can be multiple lines and much more comprehensive.

(OPTIONAL) BREAKING CHANGE: Describe any breaking changes that were introduced by this commit.
</format>

TYPES:
- build: Changes that affect the build system or external dependencies
- chore: Other changes that don't fit into the above categories. For example, changes to configuration files, updating dependencies, etc
- ci: Changes to the CI/CD configuration files and scripts
- docs: Documentation only changes. This can omit the scope if not applicable
- feat: A new feature
- fix: A bug fix
- perf: A code change that improves performance
- refactor: A code change that neither fixes a bug nor adds a feature
- style: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc)
- test: Adding missing tests or correcting existing tests

SCOPES:
- build: Changes related to build system and external dependencies
- ci: Changes related to CI/CD configuration and scripts
- core: Changes related to the code in `src/core/` folder
- docs: Changes related to documentation
- general: Changes that don't fit into the above scopes
- <module_name>: Changes related to a specific module in `src/modules/` folder, where `<module_name>` is the name of the module
- shared: Changes related to shared code in `src/shared/` folder
- tests: Changes related to tests in `tests/` folder

EXAMPLES:
<example>
feat(core): add user authentication middleware

Added a new middleware to handle user authentication using JWT tokens. This middleware checks for the presence of a valid token in the Authorization header of incoming requests and verifies it before allowing access to protected routes.
</example>
<example>
fix(ci): resolve issue with GitHub Actions workflow

Fixed a bug in the GitHub Actions workflow that was causing the build to fail due to incorrect environment variable names. Updated the workflow file to use the correct variable names and added a step to validate the environment variables before running the build.
</example>
<example>
refactor(shared): extract common utility functions

Extracted common utility functions from various modules into a new `utils` module in the `src/shared/` folder. This includes functions for data validation, formatting, and error handling. This refactor improves code reuse and maintainability across the codebase.
</example>

Analyze the staged changes and generate ONE commit message in English following these rules exactly.
Commit message: