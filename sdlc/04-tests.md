# 04 — Tests

**SDLC stage:** Implementation + Testing
**Implements:** [03-plan.md](03-plan.md)

## Unit tests — `tests/test_skills.py`

All tests use `FakeModelClient`, so they run without Ollama.

| Test | Criterion |
|------|-----------|
| `test_parse_skill_file_reads_front_matter_and_body` | S1 |
| `test_parse_skill_file_defaults_name_to_folder` | S1 |
| `test_discover_finds_skill_folders_and_skips_invalid` (uses `skill/` singular) | S1 |
| `test_discover_first_root_wins_on_duplicate_names` | S1 |
| `test_default_roots_include_skills_and_skill_folders` | S1 |
| `test_repo_ships_lab5_skill` | S5 |
| `test_tokenize_drops_stop_words_and_stems` | S2 |
| `test_match_selects_best_skill` | S2 |
| `test_match_returns_none_below_threshold` | S2 |
| `test_scores_are_sorted_and_explainable` | S2, S4 |
| `test_auto_trigger_injects_skill_instructions_into_prompt` | S2 |
| `test_unrelated_prompt_does_not_activate_skill` | S2 |
| `test_explicit_skill_command` | S2 |
| `test_model_can_trigger_skill_during_execution` | S3 |
| `test_use_skill_unknown_name_returns_error` | S3 |
| `test_use_skill_xml_form_is_parsed` | S3 |
| `test_active_skill_resets_on_next_request` | spec §5 |
| `test_agent_without_skills_has_no_skill_tool` | S7 (no behaviour change when no skills) |
| `test_log_records_prompt_similarity_and_executed_skill` | S4 |
| `test_log_records_tool_trigger` | S4 |
| `test_cli_flags_build_registry` | spec §7 |
| `test_skill_context_and_resources_are_loaded_into_prompt` | spec §1 (`context`/`resources`), S4 (`loaded_files`) |

## Regression

The original `tests/test_mini_coding_agent.py` is unchanged and must keep
passing (S7). `pyproject.toml` now sets `testpaths = ["tests"]` so the lab
sub-folders' own tests are not collected by accident.

## Run

```bash
uv run --with pytest python -m pytest -q
```

Result at time of writing: **41 passed** (19 original + 22 new).
