"""
This module has been refactored to use the Supervisor Multi-Agent pattern
as defined in app/agents/sub_agents/supervisor.py
"""

from app.agents.sub_agents.supervisor import get_onboarding_supervisor

# Expose the new graph orchestrator
# Currently `get_onboarding_supervisor()` returns a CompiledStateGraph (from `create_agent()`)
# allowing compatibility with endpoints running `onboarding_graph.stream()` or `.invoke()`
onboarding_graph = get_onboarding_supervisor()
