---
applyTo: '**'
---

Generate a conventional commit message in English following this exact format:

<format>
type(scope if applicable): subject in imperative mood, lowercase, no period, max 48 chars

Detailed description of changes made, including context,
reason for changes, and any important implementation details.
This can be multiple lines and much more comprehensive.

(OPTIONAL) BREAKING CHANGE: Describe any breaking changes that were introduced by this commit.
</format>

## TYPES:

### With scopes:
- feat: A new feature
- fix: A bug fix
- perf: A code change that improves performance
- refactor: A code change that neither fixes a bug nor adds a feature
- style: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc)
- test: Adding missing tests or correcting existing tests

### Without scopes:
- build: Changes that affect the build system or external dependencies
- ci: Changes to the CI/CD configuration files and scripts
- docs: Documentation only changes
- chore: Other changes that don't fit into the above categories. For example, changes to configuration files, updating dependencies, etc

## SCOPES:

- <package_name>: Changes related to a specific package in `src/<package_name>/` folder
- tests: Changes related to tests in `tests/` folder
- general: Changes that don't fit into the above scopes

## EXAMPLES:

<example>
feat(core): add user authentication middleware

Added a new middleware to handle user authentication using JWT tokens. This middleware checks for the presence of a valid token in the Authorization header of incoming requests and verifies it before allowing access to protected routes.
</example>
<example>
fix(agents): fix issue with uefa agent initialization

Fixed a bug that caused UEFA agent to fail during initialization due to incorrect configuration parameters. Updated the initialization logic to correctly handle the configuration parameters and ensure proper setup of the agent.
</example>
<example>
refactor(services): extract common utility functions

Extracted common utility functions from various service modules into a separate utility module to promote code reuse and maintainability. This change simplifies the service modules and makes it easier to manage shared functionality.
</example>

Analyze the staged changes and generate ONE commit message in English following these rules exactly.
Commit message: