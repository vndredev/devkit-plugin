# Changelog

## [v0.32.0] - 2026-01-18

### Added

- **Statusline**: Support devkit_plugin_dir environment variable (#20)
- **Hook**: Enforce /dk dev workflow on protected branches (#23)
- **Validate**: Enforce /dk commands instead of raw gh/vercel (#22)
- **Plugin**: Add logging/observability service detection (#21)
- **Session**: Warn when https remote used with workflow files (#19)
- **Plugin**: Styled markdown output for all reports (#16)
- **Skill**: Add /dk analyze command for opus deep analysis (#13)

### Fixed

- **Sync**: Correct workflow yaml indentation (#18)
- **Plugin**: Address 13 issues from system audit (#14)
- **Plugin**: Address 23 issues from opus analysis (#12)
- **Config**: Detect missing schema file referenced by $schema
- **Hook**: Improve status line detail and branch pattern validation
- **Arch**: Resolve typeerror in format.py and sync issues

## [v0.25.0] - 2026-01-17

### Fixed

- **Statusline**: Use semver sort for plugin version detection
- Release pending changes (schema sync, auto-merge)

### Added

- **Plugin**: Add --plugin-dir detection and dev mode indicator (#11)
- **Git**: Add GitHub branch protection based on repo type (#10)
- Add project consistency validation system (#7)
- Add /dk webhooks command for local webhook management (#5)

## [v0.21.0] - 2026-01-16

### Changed

- **Events**: Use correct hook response format

### Fixed

- **Arch**: Extract message from violation dicts in format_compact
- **Events**: Ensure all hooks output valid json
- **Events**: Always output json in validate.py hook

### Added

- Template-based generation and version sync
- **Statusline**: Add devmode with commit-id versioning
- Add automatic managed entry upgrades and claude_config_dir support
- **Events**: Use additionalcontext in enterplanmode hook

## [v0.16.0] - 2026-01-15

### Fixed

- **Events**: Add pythonpath=src to uv run commands
- **Events**: Use uv run for hook commands

### Changed

- **Plan**: Restructure plan hook config
- **Events**: Move all hook prompts to config for transparency

### Added

- **Events**: Add pretooluse:enterplanmode hook
- **Config**: Add project identity and improve config upgrade
- **Plugin**: Add smart comments to config sections
- **Plugin**: Expand recommended_defaults with all hook prompts
- **Plugin**: Add config upgrade and completeness check
- **Docs**: Update /dk docs to manage all documentation
- **Events**: Auto-create architecture.md when missing
- **Events**: Add statusline script with devkit integration
- **Events**: Always show systemmessage in user terminal
- **Events**: Add systemmessage for user-visible warnings
- **Docs**: Add auto-generated architecture.md
- **Arch**: Add ports/protocols and runtime layer guard
- **Arch**: Add config-driven architecture docs and visualization
- **Config**: Restructure config with jsonc support and docs templates
- **Changelog**: Add config-driven changelog with audience support

## [v0.1.0] - 2026-01-15

### Added

- Initial release
- Claude Code plugin for automated dev workflows
- PR workflows with GitHub integration
- Linter sync (ruff, markdownlint)
- Environment management
- `/dk` command system
