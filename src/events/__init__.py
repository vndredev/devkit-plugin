"""Events module - Hook handlers.

TIER 3: Entry points, may import from all layers.

Handlers:
- session.py: SessionStart hook
- validate.py: PreToolUse:Bash hook (git + gh validation)
- enter_plan.py: PreToolUse:EnterPlanMode hook (shows planning structure)
- format.py: PostToolUse:Write|Edit hook
- plan.py: PostToolUse:ExitPlanMode hook (implementation instructions)
"""
