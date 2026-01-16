# Changelog

## [v0.17.0] - 2026-01-16

### Added

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
