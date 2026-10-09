# my-claude-plugin

Personal Claude Code plugin, published through its own marketplace (`nedelchev`).

## Install

```
/plugin marketplace add <github-user>/my-claude-plugin
/plugin install workbench@nedelchev
```

For local development, point the marketplace at the checkout instead:

```
/plugin marketplace add ~/my-claude-plugin
```

## Contents

| Path | What it does |
| --- | --- |
| `plugins/workbench/instructions/*.md` | Always-on instructions. A SessionStart hook concatenates every file here into the session context, like a global `CLAUDE.md`. |
| `plugins/workbench/hooks/` | The SessionStart hook (requires `jq`). |

## Extending

- **Always-on rule** — add a `.md` file to `instructions/`.
- **On-demand knowledge or workflow** — add `skills/<name>/SKILL.md` under `plugins/workbench/`.
- Bump `version` in both `plugin.json` and `marketplace.json`, then `/plugin marketplace update nedelchev`.
