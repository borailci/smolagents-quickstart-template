# Knowledge Base Plan
## Task 1: DeepAgents Core
- Role: analyzer
- Files:
  - libs/deepagents/deepagents/graph.py
  - libs/deepagents/deepagents/middleware/filesystem.py
  - libs/deepagents/deepagents/middleware/patch_tool_calls.py
  - libs/deepagents/deepagents/middleware/subagents.py

## Task 2: DeepAgents Backends
- Role: analyzer
- Files:
  - libs/deepagents/deepagents/backends/composite.py
  - libs/deepagents/deepagents/backends/filesystem.py
  - libs/deepagents/deepagents/backends/protocol.py
  - libs/deepagents/deepagents/backends/sandbox.py
  - libs/deepagents/deepagents/backends/state.py

## Task 3: DeepAgents CLI Core
- Role: analyzer
- Files:
  - libs/deepagents-cli/deepagents_cli/main.py
  - libs/deepagents-cli/deepagents_cli/agent.py
  - libs/deepagents-cli/deepagents_cli/agent_memory.py
  - libs/deepagents-cli/deepagents_cli/commands.py
  - libs/deepagents-cli/deepagents_cli/execution.py

## Task 4: DeepAgents CLI Integrations
- Role: analyzer
- Files:
  - libs/deepagents-cli/deepagents_cli/integrations/daytona.py
  - libs/deepagents-cli/deepagents_cli/integrations/modal.py
  - libs/deepagents-cli/deepagents_cli/integrations/runloop.py
  - libs/deepagents-cli/deepagents_cli/integrations/sandbox_factory.py

## Task 5: DeepAgents CLI Skills and Tools
- Role: analyzer
- Files:
  - libs/deepagents-cli/deepagents_cli/skills/commands.py
  - libs/deepagents-cli/deepagents_cli/skills/load.py
  - libs/deepagents-cli/deepagents_cli/skills/middleware.py
  - libs/deepagents-cli/deepagents_cli/tools.py
  - libs/deepagents-cli/deepagents_cli/ui.py

## Task 6: Harbor
- Role: analyzer
- Files:
  - libs/harbor/deepagents_harbor/backend.py
  - libs/harbor/deepagents_harbor/deepagents_wrapper.py
  - libs/harbor/deepagents_harbor/tracing.py
