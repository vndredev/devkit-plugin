"""Events module - Hook handlers.

TIER 3: Entry points, may import from all layers.

Handlers:
- session.py: SessionStart hook
- validate.py: PreToolUse hook (git + gh validation)
- format.py: PostToolUse hook
- plan.py: PostToolUse hook (ExitPlanMode)
"""
