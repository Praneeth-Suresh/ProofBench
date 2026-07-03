# Agents

This folder contains agent designs. `llm_baseline.py` performs one model call and is the control condition. `react_agent.py` adds a simple reasoning/action loop with Lean compiler feedback.

New agents should implement the `AgentResult` contract in `base.py` and be registered in `registry.py`.

