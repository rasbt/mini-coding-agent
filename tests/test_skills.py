import json
from mini_coding_agent import FakeModelClient, MiniAgent, SessionStore, SkillLibrary, WorkspaceContext, build_arg_parser


def skill(root, name="grid-validation", valid=True):
    path = root / ".claude" / "skills" / name / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text((f"---\nname: {name}\ndescription: Validate grid dimensions and terminal states\nkeywords: grid, dimensions, terminal, states\n---\nCheck the 4x4 grid.\n" if valid else "bad frontmatter"), encoding="utf-8")
    return path


def agent(root, outputs, **kwargs):
    workspace = WorkspaceContext.build(root)
    return MiniAgent(FakeModelClient(outputs), workspace, SessionStore(root / ".mini-coding-agent" / "sessions"), **kwargs)


def events(root):
    return [json.loads(x) for x in (root / ".mini-coding-agent" / "skill_log.jsonl").read_text().splitlines()]


def test_discovery_and_invalid_skills(tmp_path):
    skill(tmp_path)
    skill(tmp_path, "broken", False)
    library = SkillLibrary(tmp_path)
    assert list(library.skills) == ["grid-validation"]
    assert len(library.warnings) == 1


def test_automatic_activation_prompt_and_logging(tmp_path):
    skill(tmp_path)
    a = agent(tmp_path, ["<final>Checked.</final>"])
    assert a.ask("Validate grid dimensions and terminal states") == "Checked."
    assert "Check the 4x4 grid." in a.model_client.prompts[0]
    assert list(a.active_skills) == ["grid-validation"]
    assert [e["event"] for e in events(tmp_path)] == ["similarity_check", "skill_executed"]
    assert events(tmp_path)[0]["prompt"] == "Validate grid dimensions and terminal states"
    assert any(e["role"] == "skill" for e in a.session["history"])


def test_load_skill_and_idempotency(tmp_path):
    skill(tmp_path)
    a = agent(tmp_path, [])
    assert "activated grid-validation" in a.run_tool("load_skill", {"name": "grid-validation"})
    assert "already active" in a.run_tool("load_skill", {"name": "grid-validation"})
    assert len(events(tmp_path)) == 1
    assert "valid names" in a.run_tool("load_skill", {"name": "unknown"})


def test_no_skills_keeps_existing_behavior(tmp_path):
    a = agent(tmp_path, ["<final>ok</final>"])
    assert "load_skill" not in a.tools
    assert "Available skills" not in a.prefix
    assert a.ask("Validate grid dimensions") == "ok"
    assert not (tmp_path / ".mini-coding-agent" / "skill_log.jsonl").exists()


def test_cli_options():
    args = build_arg_parser().parse_args(["--skill-threshold", "0.4", "--max-skills", "2"])
    assert args.skill_threshold == 0.4
    assert args.max_skills == 2
