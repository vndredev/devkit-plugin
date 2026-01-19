# Changelog

## [v0.50.0] - 2026-01-19

### Fixed

- **Sync**: Auto-sync user files when outdated (#60)
- **Lib**: Add timeouts to subprocess calls in tools.py (#59)
- **Mcp**: Use env var defaults and restore neon api key mode (#57)
- **Mcp**: Use neon remote mcp with oauth (#56)
- **Statusline**: Use claude_plugin_root for version detection (#53)
- **Hook**: Use correct tool_input key in plan_guard (#52)

### Changed

- **Serv**: Use native claude background tasks (#51)

### Added

- **Statusline**: Remove plan-guard enforcement and improve sync messaging (#63)
- **Skill**: Add livekit skill for real-time communication (#61)
- **Mcp**: Add mcp health check for env vars (#58)
- **Hook**: Add userpromptsubmit hook for workflow enforcement (#55)
- **Mcp**: Add mcp server management via plugin (#54)
- **Serv**: Background service start with scripts (#48)
- **Hook**: Add stop hook for plugin update check (#47)
- **Serv**: Unified /dk serv command for dev services (#46)

## [v0.42.2] - 2026-01-18

### Added

- **Hook**: Add plan_guard to block edits until plan approved (#42)
- **Skill**: Enforce explicit enterplanmode for feat/refactor workflows (#40)
- **Session**: Auto-commit managed files on main after sync (#37)
- **Hook**: Complete workflow enforcement across all touchpoints (#35)
- **Hook**: Enforce /dk dev workflow on protected branches (#34)
- **Docs**: Add auto-generated development.md guide (#33)
- **Config**: Add config upgrade for missing sections (#32)
- **Config**: Add project-type based logging strategy (#31)
- **Skill**: Add axiom and browser skills with schema improvements (#30)
- **Session**: Auto-sync outdated files on session start (#27)
- **Statusline**: Support devkit_plugin_dir environment variable (#20)
- **Hook**: Enforce /dk dev workflow on protected branches (#23)
- **Validate**: Enforce /dk commands instead of raw gh/vercel (#22)
- **Plugin**: Add logging/observability service detection (#21)
- **Session**: Warn when https remote used with workflow files (#19)
- **Plugin**: Styled markdown output for all reports (#16)
- **Skill**: Add /dk analyze command for opus deep analysis (#13)

### Fixed

- **Skill**: Enforce auto-merge step with you must keywords (#44)
- **Hook**: Check actual env var existence for logging credentials (#43)
- **Skill**: Update axiom docs for next.js 16+ compatibility (#39)
- **Schema**: Add missing hook definitions (#38)
- **Git**: Auto-return to main after /dk git pr (#36)
- **Logging**: Update axiom detection and add enabled flags to schema (#29)
- **Validate**: Use claude_project_dir for self-development check (#26)
- **Release**: Sync uv.lock after version bump (#25)
- **Validate**: Skip dk enforcement in self-development mode (#24)
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
