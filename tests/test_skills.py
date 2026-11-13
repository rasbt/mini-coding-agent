import json
from pathlib import Path

from mini_coding_agent import (
    FakeModelClient,
    MiniAgent,
    SessionStore,
    SkillLogger,
    SkillRegistry,
    WorkspaceContext,
    build_arg_parser,
    build_skills,
    parse_skill_file,
    tokenize,
)

REPO_SKILLS = Path(__file__).resolve().parent.parent / "skills"


def write_skill(root, folder, name, description, triggers="", body="Do the thing."):
    path = root / folder
    path.mkdir(parents=True, exist_ok=True)
    lines = ["---"]
    if name:
        lines.append(f"name: {name}")
    if description:
        lines.append(f"description: {description}")
    if triggers:
        lines.append(f"triggers: {triggers}")
    lines += ["---", "", body, ""]
    (path / "SKILL.md").write_text("\n".join(lines), encoding="utf-8")
    return path / "SKILL.md"


def make_registry(tmp_path, echo=False):
    root = tmp_path / "skills"
    write_skill(
        root, "pr-review", "pr-review",
        "Review a pull request or git diff for bugs and missing tests.",
        "pull request, code review, review my diff",
        body="1. Run git diff.\n2. Write the review.",
    )
    write_skill(
        root, "vacuum-world-agent", "vacuum-world-agent",
        "Implement a Python agent for the AIMA vacuum world from a spec.md file.",
        "vacuum world, spec.md, persistent memory agent",
        body="1. Read spec.md.\n2. Write the agent.\n3. Run pytest.",
    )
    logger = SkillLogger(tmp_path / ".mini-coding-agent" / "logs" / "skills.jsonl", echo=echo)
    return SkillRegistry.discover([root], logger=logger)


def build_agent(tmp_path, outputs, registry=None, **kwargs):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    workspace = WorkspaceContext.build(tmp_path)
    store = SessionStore(tmp_path / ".mini-coding-agent" / "sessions")
    return MiniAgent(
        model_client=FakeModelClient(outputs),
        workspace=workspace,
        session_store=store,
        approval_policy="auto",
        skills=registry if registry is not None else make_registry(tmp_path),
        **kwargs,
    )


def read_log(tmp_path):
    path = tmp_path / ".mini-coding-agent" / "logs" / "skills.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


# --- S1: discovery and parsing -------------------------------------------------

def test_parse_skill_file_reads_front_matter_and_body(tmp_path):
    path = write_skill(tmp_path, "demo", "demo-skill", "A demo skill.", "alpha, beta gamma", body="Step 1.")
    skill = parse_skill_file(path)
    assert skill.name == "demo-skill"
    assert skill.description == "A demo skill."
    assert skill.triggers == ["alpha", "beta gamma"]
    assert skill.body == "Step 1."
    assert skill.directory == tmp_path / "demo"


def test_parse_skill_file_defaults_name_to_folder(tmp_path):
    path = write_skill(tmp_path, "folder-name", None, "Desc.")
    assert parse_skill_file(path).name == "folder-name"


def test_discover_finds_skill_folders_and_skips_invalid(tmp_path):
    root = tmp_path / "skill"  # singular folder name is also supported
    write_skill(root, "good", "good", "Good skill.")
    write_skill(root, "bad", "bad", "")  # no description
    (root / "empty").mkdir()  # no SKILL.md
    logger = SkillLogger(echo=False)
    registry = SkillRegistry.discover([root, tmp_path / "missing"], logger=logger)
    assert list(registry.skills) == ["good"]
    event = logger.events[-1]
    assert event["event"] == "discover"
    assert event["skills"] == ["good"]
    assert len(event["skipped"]) == 1


def test_discover_first_root_wins_on_duplicate_names(tmp_path):
    write_skill(tmp_path / "a", "x", "same", "From A.")
    write_skill(tmp_path / "b", "x", "same", "From B.")
    registry = SkillRegistry.discover([tmp_path / "a", tmp_path / "b"])
    assert registry.get("same").description == "From A."


def test_default_roots_include_skills_and_skill_folders(tmp_path):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    workspace = WorkspaceContext.build(tmp_path)
    roots = SkillRegistry.default_roots(workspace, [tmp_path / "extra"])
    assert roots[0] == (tmp_path / "extra").resolve()
    assert (tmp_path / "skills").resolve() in roots
    assert (tmp_path / "skill").resolve() in roots
    assert REPO_SKILLS in roots


def test_repo_ships_lab5_skill():
    registry = SkillRegistry.discover([REPO_SKILLS])
    assert "vacuum-world-agent" in registry.skills
    assert "pr-review" in registry.skills
    assert (registry.get("vacuum-world-agent").directory / "reference.md").is_file()


# --- S2: similarity check -------------------------------------------------------

def test_tokenize_drops_stop_words_and_stems():
    assert tokenize("Reviewing the tests for agents") == ["review", "test", "agent"]


def test_match_selects_best_skill(tmp_path):
    registry = make_registry(tmp_path)
    skill, score = registry.match("Implement the persistent memory agent in spec.md for the vacuum world")
    assert skill.name == "vacuum-world-agent"
    assert score >= registry.threshold
    skill, _ = registry.match("Can you do a code review of my pull request?")
    assert skill.name == "pr-review"


def test_match_returns_none_below_threshold(tmp_path):
    registry = make_registry(tmp_path)
    skill, score = registry.match("Write a binary search function")
    assert skill is None and score is None


def test_scores_are_sorted_and_explainable(tmp_path):
    registry = make_registry(tmp_path)
    results = registry.scores("review my diff please")
    assert [item["skill"] for item in results][0] == "pr-review"
    assert results[0]["trigger_hits"] == ["review my diff"]
    assert results == sorted(results, key=lambda item: item["score"], reverse=True)
    assert all(0.0 <= item["score"] <= 1.0 for item in results)


# --- S2/S3: triggering and execution -------------------------------------------

def test_auto_trigger_injects_skill_instructions_into_prompt(tmp_path):
    agent = build_agent(tmp_path, ["<final>ok</final>"])
    agent.ask("Implement the vacuum world agent from spec.md")
    prompt = agent.model_client.prompts[0]
    assert "Active skill: vacuum-world-agent" in prompt
    assert "1. Read spec.md." in prompt
    assert agent.session["active_skill"]["trigger"] == "auto"
    assert any(item["role"] == "skill" for item in agent.session["history"])


def test_unrelated_prompt_does_not_activate_skill(tmp_path):
    agent = build_agent(tmp_path, ["<final>ok</final>"])
    agent.ask("Write a binary search function")
    assert agent.session["active_skill"] is None
    assert "Active skill:" not in agent.model_client.prompts[0]


def test_explicit_skill_command(tmp_path):
    agent = build_agent(tmp_path, ["<final>ok</final>"])
    agent.ask("/skill pr-review check the latest change")
    prompt = agent.model_client.prompts[0]
    assert "Active skill: pr-review" in prompt
    assert prompt.rstrip().endswith("check the latest change")
    assert agent.session["active_skill"]["trigger"] == "explicit"


def test_model_can_trigger_skill_during_execution(tmp_path):
    agent = build_agent(
        tmp_path,
        [
            '<tool>{"name":"use_skill","args":{"name":"vacuum-world-agent"}}</tool>',
            "<final>done</final>",
        ],
    )
    agent.ask("build the thing for lab 4")
    first, second = agent.model_client.prompts
    assert "Active skill:" not in first
    assert "use_skill(name: str)" in first  # tool advertised
    assert "- vacuum-world-agent: Implement a Python agent" in first  # catalogue in prefix
    assert "Active skill: vacuum-world-agent" in second
    assert agent.session["active_skill"]["trigger"] == "tool"


def test_use_skill_unknown_name_returns_error(tmp_path):
    agent = build_agent(
        tmp_path,
        ['<tool>{"name":"use_skill","args":{"name":"nope"}}</tool>', "<final>done</final>"],
    )
    agent.ask("anything")
    tool_events = [item for item in agent.session["history"] if item["role"] == "tool"]
    assert "unknown skill 'nope'" in tool_events[0]["content"]


def test_use_skill_xml_form_is_parsed():
    kind, payload = MiniAgent.parse('<tool name="use_skill"><name>pr-review</name></tool>')
    assert kind == "tool"
    assert payload == {"name": "use_skill", "args": {"name": "pr-review"}}


def test_active_skill_resets_on_next_request(tmp_path):
    agent = build_agent(tmp_path, ["<final>a</final>", "<final>b</final>"])
    agent.ask("Implement the vacuum world agent from spec.md")
    agent.ask("Write a binary search function")
    assert agent.session["active_skill"] is None


def test_agent_without_skills_has_no_skill_tool(tmp_path):
    agent = build_agent(tmp_path, ["<final>ok</final>"], registry=SkillRegistry([]))
    assert "use_skill" not in agent.tools
    agent.ask("Implement the vacuum world agent from spec.md")
    assert "Agent skills" not in agent.model_client.prompts[0]


# --- S4: logging ----------------------------------------------------------------

def test_log_records_prompt_similarity_and_executed_skill(tmp_path, capsys):
    agent = build_agent(tmp_path, ["<final>ok</final>"], registry=make_registry(tmp_path, echo=True))
    agent.ask("Implement the vacuum world agent from spec.md")
    events = read_log(tmp_path)
    kinds = [event["event"] for event in events]
    assert kinds == ["discover", "prompt", "similarity_check", "skill_executed"]
    prompt_event, check, executed = events[1:]
    assert prompt_event["prompt"] == "Implement the vacuum world agent from spec.md"
    assert check["selected"] == "vacuum-world-agent"
    assert {item["skill"] for item in check["scores"]} == {"pr-review", "vacuum-world-agent"}
    assert executed["skill"] == "vacuum-world-agent"
    assert executed["trigger"] == "auto"
    assert executed["session_id"] == agent.session["id"]
    err = capsys.readouterr().err
    assert "[skills] prompt:" in err
    assert "[skills] similarity" in err
    assert "[skills] executing skill 'vacuum-world-agent'" in err


def test_log_records_tool_trigger(tmp_path):
    agent = build_agent(
        tmp_path,
        ['<tool>{"name":"use_skill","args":{"name":"pr-review"}}</tool>', "<final>done</final>"],
    )
    agent.ask("look at stuff")
    events = read_log(tmp_path)
    assert events[-1]["event"] == "skill_executed"
    assert events[-1]["trigger"] == "tool"
    assert any(event["event"] == "similarity_check" and event["selected"] is None for event in events)


# --- CLI ------------------------------------------------------------------------

def test_cli_flags_build_registry(tmp_path):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    write_skill(tmp_path / "custom", "mine", "mine", "My custom skill.")
    workspace = WorkspaceContext.build(tmp_path)
    args = build_arg_parser().parse_args(["--skills-dir", str(tmp_path / "custom"), "--skill-threshold", "0.5"])
    registry = build_skills(args, workspace)
    assert "mine" in registry.skills
    assert registry.threshold == 0.5
    assert (tmp_path / ".mini-coding-agent" / "logs" / "skills.jsonl").is_file()
    args = build_arg_parser().parse_args(["--no-skills"])
    assert build_skills(args, workspace) is None


# --- skill context files and resources -----------------------------------------

def test_skill_context_and_resources_are_loaded_into_prompt(tmp_path):
    root = tmp_path / "skills"
    write_skill(root, "ctx", "ctx", "Context demo skill for widgets.", "widget")
    skill_md = root / "ctx" / "SKILL.md"
    skill_md.write_text(
        skill_md.read_text(encoding="utf-8").replace(
            "triggers: widget", "triggers: widget\ncontext: spec.md, Test/*.py, missing.md, ../outside.md\nresources: ref.md"
        ),
        encoding="utf-8",
    )
    (root / "ctx" / "ref.md").write_text("REFERENCE BODY", encoding="utf-8")
    (tmp_path / "spec.md").write_text("SPEC BODY", encoding="utf-8")
    (tmp_path / "Test").mkdir()
    (tmp_path / "Test" / "test_a.py").write_text("TEST BODY", encoding="utf-8")
    (tmp_path.parent / "outside.md").write_text("OUTSIDE", encoding="utf-8")
    logger = SkillLogger(tmp_path / ".mini-coding-agent" / "logs" / "skills.jsonl", echo=False)
    registry = SkillRegistry.discover([root], logger=logger)
    agent = build_agent(tmp_path, ["<final>ok</final>"], registry=registry)
    agent.ask("build a widget")
    prompt = agent.model_client.prompts[0]
    assert '<file path="spec.md">\nSPEC BODY' in prompt
    assert '<file path="Test/test_a.py">\nTEST BODY' in prompt
    assert '<file path="ctx/ref.md">\nREFERENCE BODY' in prompt
    assert "OUTSIDE" not in prompt  # workspace path validation still applies
    executed = [event for event in read_log(tmp_path) if event["event"] == "skill_executed"][0]
    assert executed["loaded_files"] == ["spec.md", "Test/test_a.py", "ctx/ref.md"]
