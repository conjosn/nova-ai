# Nova v2 open-source feature map

Nova v2 uses original Python implementations informed by public feature patterns
from established open-source assistants. This document records what influenced the
design and prevents “inspired by” from quietly turning into unreviewed code copying.

| Project | Public pattern | Nova v2 implementation |
|---|---|---|
| [Open WebUI](https://github.com/open-webui/open-webui) | Offline operation, RAG, extensible pipelines, multiple model backends | Local Ollama routing, document RAG, and a central assistant-session boundary |
| [Khoj](https://github.com/khoj-ai/khoj) | Custom agents, personal knowledge, automations, voice | Agent profiles, document knowledge, persistent reminders, shared voice/text context |
| [AnythingLLM](https://github.com/Mintplex-Labs/anything-llm) | Dynamic routing, managed memories, scheduled tasks, skill selection | Installed-model router, ChromaDB memories, reminder queue, deterministic local skills |
| [Leon](https://github.com/leon-ai/leon) | Smart/controlled/agent execution, layered memory, skills and tools, proactive pulse | Smart/Controlled/Chat modes, recent plus retrieval memory, allowlisted skills, due-reminder polling |
| [OpenVoiceOS](https://github.com/OpenVoiceOS/ovos-core) | Installable skills and persona fallback | Explicit skill-first routing and selectable General/Analyst/Engineer/Operator personas |
| [Open Interpreter](https://github.com/openinterpreter/openinterpreter) | Local state, sandboxing, permissions, skills, MCP | Permission boundaries influence Controlled mode; arbitrary execution and MCP are intentionally not enabled yet |

## Safety boundary

Nova v2 does not execute model-authored shell commands, click through native apps,
or mutate external systems. Those capabilities need a sandbox, explicit proposals,
per-action approval, audit logs, and a deny-by-default permission model before they
belong in a personal assistant.

## Next compatible extensions

- signed Python skill packages with declarative permissions
- an approval inbox for proposed filesystem, process, browser, and smart-home actions
- MCP clients isolated behind the same permission gate
- named knowledge workspaces and source-cited retrieval results
- recurring schedules and missed-task recovery
- multimodal camera/screenshot input with an explicit capture indicator
- Home Assistant integration with entity allowlists and confirmation for security devices
