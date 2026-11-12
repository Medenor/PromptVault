# Quickstart & Validation: Skill Packages

**Feature**: 011-skill-packages

These are runnable scenarios that show the feature works from start to finish. Endpoints are in [contracts/skills-api.md](contracts/skills-api.md), tables in [data-model.md](data-model.md).

## Prerequisites

- On branch `011-skill-packages`, with dependencies installed (PyYAML, `markdown-it-py` and `nh3` are added to `pyproject.toml`).
- The migration is applied to the dev database:

```bash
alembic upgrade head
```

- The dev servers are running. Never start uvicorn or the root `docker-compose.yml` by hand.

```bash
make dev
```

- Test fixtures are in `tests/fixtures/skills/`: valid skills, malformed skills, and malicious archives built by `tests/fixtures/skills/build_fixtures.py`, so no binary fixtures are committed.

## Automated gates

```bash
make test    # backend + frontend suites, ≥ 85 % coverage on both (Constitution II)
make lint    # Black, ESLint, tsc, Prettier, print() check, SW cache-version check
```

Run the skill suites on their own:

```bash
python3 -m pytest tests/unit/test_skill_archive_reader.py tests/unit/test_skill_frontmatter.py tests/unit/test_skill_service.py tests/integration/test_skills_api*.py tests/integration/test_skills_upload_limits.py tests/integration/test_skills_auth_modes.py -v
```

Run the PostgreSQL leg of the migration and repository tests against a local container, not the production compose file:

```bash
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:55432/promptvault_test python3 -m pytest tests/integration/test_skills_api*.py tests/integration/test_skill_search.py tests/integration/test_skill_migration.py -v
```

## Scenario 1 — Import and browse (Stories 1 and 2, SC-001)

1. Build a skill in the standard layout and import it:

```bash
mkdir -p /tmp/pv-skill/pdf-tools/scripts /tmp/pv-skill/pdf-tools/references
printf -- '---\nname: pdf-tools\ndescription: Fill PDF forms and extract tables.\n---\n# PDF tools\nRun `python3 ${CLAUDE_SKILL_DIR}/scripts/fill.py`.\n' > /tmp/pv-skill/pdf-tools/SKILL.md
echo 'print("hi")' > /tmp/pv-skill/pdf-tools/scripts/fill.py
head -c 2048 /dev/urandom > /tmp/pv-skill/pdf-tools/references/sample.bin
(cd /tmp/pv-skill && zip -qr pdf-tools.zip pdf-tools/)
curl -s -F archive=@/tmp/pv-skill/pdf-tools.zip http://localhost:8003/api/skills/import | python3 -m json.tool
```

**Expected**: 201, `title` = `pdf-tools`, `file_count` = 3, `warnings` = `[]`. In the interface, the item appears in the list with a **Skill** badge. The detail view shows the rendered instructions with `${CLAUDE_SKILL_DIR}` left as literal text (no placeholder form), a tree containing `references/` and `scripts/` folders then `SKILL.md`, readable text for `fill.py`, and size plus download for `sample.bin`.

## Scenario 2 — Lenient import with warnings (Story 1, scenario 4)

Zip a `SKILL.md` that has no frontmatter, placed at the archive root.

**Expected**: 201, title = archive file name, and `warnings` contains `frontmatter_missing` and `no_wrapping_folder`. The interface shows a non-blocking notice listing both.

## Scenario 3 — Round trip and validator (Story 3, SC-002, SC-008)

```bash
curl -s -o /tmp/pv-skill/out.zip http://localhost:8003/api/skills/<id>/download
unzip -l /tmp/pv-skill/out.zip           # every entry starts with pdf-tools/
mkdir -p /tmp/pv-skill/out && unzip -qo /tmp/pv-skill/out.zip -d /tmp/pv-skill/out
diff -r /tmp/pv-skill/pdf-tools /tmp/pv-skill/out/pdf-tools && echo IDENTICAL
skills-ref validate /tmp/pv-skill/out/pdf-tools
```

**Expected**: `IDENTICAL`, then `Valid skill`. Rename the skill's title in the interface and download again: the folder and zip are still named `pdf-tools`.

## Scenario 4 — Malicious archives are rejected (SC-003, FR-007–FR-011)

The fixture builder creates archives with path traversal (`../evil`), an absolute path, a symbolic link, a 1 GB zip bomb, 501 files, depth 11, a case-only duplicate, a corrupt file, and an encrypted entry.

**Expected**: each one returns the error code from the contract. The `prompts`, `skill_packages` and `skill_files` row counts do not change, and `data/logs/audit.log` has one `skill.import.rejected` event per archive, with `reason_code` and no file contents. Automated in `test_skill_archive_reader.py` (parametrised), `test_skills_api.py` and, for the upload-size cases, `test_skills_upload_limits.py`.

## Scenario 5 — Replace, search, bulk-import safety (Story 4, FR-022, FR-024, FR-024a)

1. Rename the title to "My PDF helper", add a tag, then `PUT /api/skills/<id>/archive` with a zip whose `name` is `pdf-tools-v2`. **Expected**: the title is still "My PDF helper", the tag is kept, `skill_identifier` = `pdf-tools-v2`, and the description and files are new.
2. Upload a corrupt replacement. **Expected**: 400, and the skill is byte-identical to its state before the attempt.
3. Search for a word that appears only in the `SKILL.md` body. **Expected**: the skill is a hit. Search for a word that appears only in `scripts/fill.py`. **Expected**: no hit.
4. Filter the list by type Skill, then by Prompt. **Expected**: only matching items.
5. Run a bulk prompt import in **Replace** mode. **Expected**: prompts are replaced and the skill is still there. The bulk export screen shows the "skills are exported one at a time" notice, and the exported file contains no skills.

## Scenario 6 — Prompt-only actions are blocked on skills (FR-003)

Call `PUT /api/prompts/<skill id>`, the versions endpoint and the sharing endpoint on a skill. **Expected**: 409 `ITEM_IS_SKILL` each time, no new `prompt_versions` rows, and the interface does not offer these actions on skills.

## Scenario 7 — Backup and restore (Story 5, SC-006, FR-027)

1. Create a backup from the backup management page with two skills present.
2. Restore it into an empty dev instance, after setting `PROMPTVAULT_DATA_DIR` to a scratch folder (see the backup data-dir isolation note).
3. Download both skills and compare them with the originals using `diff -r`. **Expected**: identical.
4. Restore a backup taken **before** this migration, then run `alembic upgrade head`. **Expected**: the restore succeeds and every item lists as a prompt.

## Scenario 8 — Existing behaviour unchanged (SC-005)

Run the existing prompt suites (`tests/` minus the new `*skill*` files). **Expected**: all pass with no changes to those tests.

## Scenario 9 — Performance (SC-007)

`tests/benchmarks/test_skill_detail_perf.py` imports a 500-file skill and checks that `GET /api/skills/{id}` responds in under 2 s on the SQLite leg.
