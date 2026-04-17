# Agent Skill Bridge

Agent Skill Bridge is a CLI for managing AI agent skills across different
harnesses such as Codex, Claude Code, Crush, and DeepAgents.

It keeps a shared skill store, copies or links skills into harness-level global
and project-level skill folders, tracks project usage, and can sync skills
between harnesses.

Features:
- skill list/remove
- skill install
- skill link/copy
- skill sync
- usage output
- harness config management
- shell completion

Operation output uses:

```text
[<op>][<level>] <skill-name> -> <path>
```

The manager files are stored under:

```python
~/.agents
```

The shared skill store is:

```python
~/.agents/skills
```

A harness is an agent tool that consumes skills, such as Codex or Claude Code.
Global and project storage are the harness's own global-level and project-level
configuration paths.

Agent Skill Bridge maintains the skills folder and a usage file for tracking:

```python
~/.agents/asb-usage.json
```

Usage tracking (the <harness> must exist in the [mapper](#config)):
```text
<owner-harness>: {
    "projects": {
        <proj>: {
            <skill>: <mode>
        }
    },
    "globals": {
        <target-harness>: {
            <skill>: <mode>
        }
    }
}
```

Global usage is grouped by skill origin. Skills that already exist in the
shared store are recorded under `default.globals.<target-harness>`. Source-only
skills imported during `sync --all` are recorded under
`<src-harness>.globals.<target-harness>`.

## Install

```sh
uv sync --python 3.10 --link-mode copy
```

The package name is `agent-skill-bridge`. Run the CLI with `asb`:

```sh
uv run --python 3.10 asb --help
```

The long command `agent-skill-bridge` is also available.

## List

Show skills of the current project.

By default, `list` detects harnesses used by the current project. A harness is
considered used when its project prefix exists in the current project; the
`skills` folder does not need to exist yet. It then shows both project and
global levels for those harnesses. Be quiet if there is nothing to show.

```sh
asb list [<harness>] [--global | --project]
```

- `-g`/`--global`: global only (any folder)
- `-p`/`--project`: project only
- By default, we list project level and global level with level title
- `list -g` shows global skills for the detected project harnesses and the
  default global skills

Example:
```
Project (<harness>):
- <skill-name>
...

Global (<harness>):
- <skill-name>
```

## Remove

```sh
asb remove [<harness>] [<skill-name>...] [--global] [--link] [--all]
```

For <skill-name>
- `-g`/`--global`: global only
- `-l`/`--link`: remove the symlink and its linked shared-store skill
- `-a`/`--all`: requires a skill name, removes it from the default global store
  and from project paths recorded in usage
  by first running `npx skills remove <skill-name> -g -a universal -y`, then
  falling back to direct deletion if that command fails
- By default, we just remove the skill from current project
- no harness: open a terminal UI picker for harness first, then skills
- skill picker controls: Arrow moves, Space selects, Enter confirms
- first positional argument: harness name
- project-level remove deletes the project prefix too when it only contains an
  empty `skills` folder

For unknown skill name, just show error message

## Install

```sh
asb install <skill-ref> [-y]
```

Install a skill into the default global store by running:

```sh
npx skills add <skill-ref> -a universal -g -y
```

Without `-y`, Agent Skill Bridge asks whether to run the install. With `-y`, it
runs immediately. The `npx` command always receives `-y`.

## Link/Copy

```sh
asb copy [<harness>] [<skill-names>...] [-p | -g]
asb link [<harness>] [<skill-names>...] [-p | -g]
```

Copy/Link skill from the shared skill store into a harness global or project
path.

- no argument: open a terminal UI picker for harness first, then skills
- copy/link harness picker does not show `default`
- harness only: open a terminal UI picker for skills
- harness picker controls: Arrow moves, Enter confirms
- skill picker controls: Arrow moves, Space selects, Enter confirms
- `-p`/`--project`: operation on project level
- `-g`/`--global`: operation on global level
- By default, operation on project level
- first positional argument: harness name

## Sync

```sh
asb sync <src_harness> <dst_harness> [--copy] [--all] [-p | -g]
```

Sync all skills from the Agent Skill Bridge shared store into another harness
global or project path. The source harness is used to detect skills that exist
in the source global path but are missing from the shared store.

- By default, sync in link mode from the shared store
- `-c`/`--copy`: sync in copy mode
- `-a`/`--all`: copy source-only skills into the shared store before syncing
- Without `-a`, source-only skills are reported as warnings and are not synced
- If the source harness has no global skills, sync completes without changing
  the destination and reports that the source has no skills
- When sync runs, it reports the number of skills synced to the destination
- `-p`/`--project`: operation on project level
- `-g`/`--global`: operation on global level
- By default, operation on project level

## Completion

```sh
asb completion zsh
asb completion bash
```

Output the completion script in stdout

## Usage

```sh
asb usage
```

Print `asb-usage.json` as globals first, then projects.

Global usage:
```text
[global]:
<harness>
  - <skill>
  - <skill>
```

Project usage:
```text
[project]:
<harness>
  <project-path>
    - <skill>
    - <skill>
```

## Config

```sh
asb config list
asb config add <harness> [-p <project>] [-g <global>]
asb config remove <harness> [-p | -g] [-a]
```

`config list` shows every harness config except `default`.

`config add` adds the fields that are provided. If neither `-p` nor `-g` is
provided, the harness is stored as an empty object. If the harness already
exists, Agent Skill Bridge asks whether to overwrite it and defaults to no.

`config remove` removes the whole harness config by default. With `-p` or `-g`,
it removes only that field. By default, Agent Skill Bridge asks whether to
delete the related global and recorded project skill folders. With `-a`, it
deletes them without asking.

Default storage:
- project: .agents/skills
- global: ~/.agents/skills

For different harness, the mapper file is:

```python
~/.agents/asb-mapper.json
```

The `default` entry is always provided by Agent Skill Bridge and is not shown by
`config list`.

```json
<harness> : {
    "project": <prefix>,
    "global": <prefix>
}
```

Then we get the folder by:
```python
harness = mapper.get(name, mapper["default"])
project_folder = harness.get("project", mapper["default"]["project"]) / "skills"
global_folder = harness.get("global", mapper["default"]["global"]) / "skills"
```
