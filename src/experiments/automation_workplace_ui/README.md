# τ Workplace manual test lab

This local visual workplace replaces the benchmark agent with a human while
preserving the standard τ user simulator, environment mutations, trajectory,
and exact-state grading. It is intended for manually verifying that the task is
coherent from the AI employee's point of view. The environment appears as a
small work computer with app icons, human-readable records, chat, and a Drive
containing current policies, technical documentation, and archived guidance.

From the repository root:

```bash
PYTHONPATH=src .venv/bin/uvicorn \
  experiments.automation_workplace_ui.server:app \
  --host 127.0.0.1 --port 8765
```

Then open `http://127.0.0.1:8765`. The server loads the repository `.env`; API
keys never enter the browser. Choose a task and user-simulator model, start a
fresh run, then act as the AI employee. Read technical documentation in Drive
to enable the matching action inside its fake application; app action forms call
the same simulated operations used by the benchmark. The exact-state checks
update after every action. The prompt inspector shows the complete agent system
prompt and, separately, the complete user-simulator prompt hidden from the agent.

Every run is recorded under
`data/simulations/automation_workplace_human/<session-id>/`. `events.jsonl`
contains ordered human UI events, submitted chat messages, tool calls, tool
results, and simulator messages. `trajectory.json` is an updated replay artifact
containing the task metadata, complete transcript, final world state, assertions,
and score. The Grade app also exposes a trajectory download link.
