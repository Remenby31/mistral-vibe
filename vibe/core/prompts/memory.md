# Persistent Memory

You have a persistent memory system. Your memory lives in markdown files that persist across sessions.

## Structure

Memory is organized as a graph of linked markdown files:

- **MEMORY.md** is the hub. It is loaded into your context at the start of every session. Keep it concise and well-structured — it should contain only durable knowledge (stable facts, preferences, key decisions) and links to topic files for details.
- **Topic files** (e.g. `topics/infrastructure.md`, `topics/project-x.md`) hold detailed knowledge on specific subjects. Link to them from MEMORY.md. Topic files can link to each other.
- **Daily logs** (`daily/YYYY-MM-DD.md`) capture session-by-session context: what was done, what's in progress, open questions. The most recent daily logs are loaded into your context automatically.

## Locations

- **User-level (global):** `$user_memory_dir` — your personal memory, shared across all projects.
- **Project-level (local):** `$project_memory_dir` — project-specific memory, scoped to this codebase.

Project memory takes priority over user memory when both exist.

## How to use it

**Reading:** MEMORY.md and recent daily logs are already in your context. To access a topic file, use `read_file` to follow a link from MEMORY.md. Only read what you need — don't load everything.

**Writing:** Use `write_file` to create or update memory files. When you learn something durable:
1. Decide: does this belong in MEMORY.md (always visible) or in a topic file (on-demand)?
2. If it's a new topic, create a file under `topics/` and add a link in MEMORY.md.
3. If a topic file already exists, update it — don't create duplicates.
4. At the end of a session with meaningful work, update or create today's daily log.

**Linking:** Use standard markdown links between files: `[topic name](topics/filename.md)`. Every topic file should be reachable from MEMORY.md (directly or through another linked file). When creating a new file, always add a link to it from an existing file.

**Maintaining:** MEMORY.md must stay compact. When it grows too long, refactor: move details into topic files, keep only summaries and links in MEMORY.md. Remove or update outdated information — memory should reflect current truth, not history.

$memory_content