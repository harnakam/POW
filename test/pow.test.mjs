import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const testDirectory = path.dirname(fileURLToPath(import.meta.url));
const scriptUrl = pathToFileURL(
  path.resolve(testDirectory, "../scripts/pow.mjs"),
).href;

async function loadPow() {
  return import(`${scriptUrl}?test=${Date.now()}-${Math.random()}`);
}

async function makeFixture(t) {
  const root = await mkdtemp(path.join(os.tmpdir(), "pow-test-"));
  const repoRoot = path.join(root, "repo");
  const codexHome = path.join(root, "codex-home");
  await mkdir(path.join(repoRoot, "commands"), { recursive: true });
  await mkdir(codexHome, { recursive: true });
  t.after(() => rm(root, { recursive: true, force: true }));
  return { repoRoot, codexHome };
}

async function writeCommand(repoRoot, name, body = "Follow the requested workflow.\n") {
  const commandRoot = path.join(repoRoot, "commands", name);
  await mkdir(commandRoot, { recursive: true });
  await writeFile(
    path.join(commandRoot, "SKILL.md"),
    [
      "---",
      `name: ${name}`,
      `description: Use when the user asks to run the ${name} workflow.`,
      "---",
      "",
      body,
    ].join("\n"),
  );
  return commandRoot;
}

function captureIo() {
  const stdout = [];
  const stderr = [];
  return {
    stdout,
    stderr,
    io: {
      stdout: (message) => stdout.push(message),
      stderr: (message) => stderr.push(message),
    },
  };
}

async function invoke(args, fixture) {
  const { run } = await loadPow();
  const captured = captureIo();
  const exitCode = await run(args, { ...fixture, ...captured.io });
  return { exitCode, ...captured };
}

test("validate accepts a well-formed command", async (t) => {
  const fixture = await makeFixture(t);
  await writeCommand(fixture.repoRoot, "hello-world");

  const result = await invoke(["validate"], fixture);

  assert.equal(result.exitCode, 0);
  assert.match(result.stdout.join("\n"), /Validated 1 command/);
});

test("validate rejects invalid names, broken frontmatter, and unfinished placeholders", async (t) => {
  const cases = [
    {
      name: "Bad_Name",
      content: "---\nname: Bad_Name\ndescription: Invalid name.\n---\n\nBody.\n",
      expected: /kebab-case/,
    },
    {
      name: "broken",
      content: "# Missing frontmatter\n",
      expected: /frontmatter/,
    },
    {
      name: "unfinished",
      content: "---\nname: unfinished\ndescription: Still TODO.\n---\n\nBody.\n",
      expected: /unfinished placeholder/,
    },
  ];

  for (const fixtureCase of cases) {
    await t.test(fixtureCase.name, async (subtest) => {
      const fixture = await makeFixture(subtest);
      const commandRoot = path.join(fixture.repoRoot, "commands", fixtureCase.name);
      await mkdir(commandRoot, { recursive: true });
      await writeFile(path.join(commandRoot, "SKILL.md"), fixtureCase.content);

      const result = await invoke(["validate"], fixture);

      assert.equal(result.exitCode, 1);
      assert.match(result.stderr.join("\n"), fixtureCase.expected);
    });
  }
});

test("install copies commands and records file hashes", async (t) => {
  const fixture = await makeFixture(t);
  await writeCommand(fixture.repoRoot, "hello-world", "Say hello.\n");

  const result = await invoke(["install"], fixture);

  assert.equal(result.exitCode, 0);
  assert.match(result.stdout.join("\n"), /Installed hello-world/);
  assert.match(
    await readFile(path.join(fixture.codexHome, "skills", "hello-world", "SKILL.md"), "utf8"),
    /Say hello\./,
  );
  const manifest = JSON.parse(
    await readFile(path.join(fixture.codexHome, ".pow", "manifest.json"), "utf8"),
  );
  assert.equal(manifest.schemaVersion, 1);
  assert.match(manifest.commands["hello-world"].files["SKILL.md"], /^[a-f0-9]{64}$/);
});

test("install refuses an unowned same-name skill", async (t) => {
  const fixture = await makeFixture(t);
  await writeCommand(fixture.repoRoot, "hello-world", "POW content.\n");
  const foreignRoot = path.join(fixture.codexHome, "skills", "hello-world");
  await mkdir(foreignRoot, { recursive: true });
  await writeFile(path.join(foreignRoot, "SKILL.md"), "foreign content\n");

  const result = await invoke(["update", "--force"], fixture);

  assert.equal(result.exitCode, 1);
  assert.match(result.stderr.join("\n"), /not owned by POW/);
  assert.equal(
    await readFile(path.join(foreignRoot, "SKILL.md"), "utf8"),
    "foreign content\n",
  );
});

test("force update never adopts an unowned prototype-named skill", async (t) => {
  const fixture = await makeFixture(t);
  await writeCommand(fixture.repoRoot, "constructor", "POW content.\n");
  const foreignRoot = path.join(fixture.codexHome, "skills", "constructor");
  await mkdir(foreignRoot, { recursive: true });
  await writeFile(path.join(foreignRoot, "SKILL.md"), "foreign content\n");

  const result = await invoke(["update", "--force"], fixture);

  assert.equal(result.exitCode, 1);
  assert.match(result.stderr.join("\n"), /not owned by POW/);
  assert.equal(
    await readFile(path.join(foreignRoot, "SKILL.md"), "utf8"),
    "foreign content\n",
  );
});

test("update preserves modified owned files unless force is used", async (t) => {
  const fixture = await makeFixture(t);
  await writeCommand(fixture.repoRoot, "hello-world", "Version one.\n");
  assert.equal((await invoke(["install"], fixture)).exitCode, 0);
  const installedSkill = path.join(fixture.codexHome, "skills", "hello-world", "SKILL.md");
  await writeFile(installedSkill, "local customization\n");
  await writeCommand(fixture.repoRoot, "hello-world", "Version two.\n");

  const safeResult = await invoke(["update"], fixture);

  assert.equal(safeResult.exitCode, 1);
  assert.match(safeResult.stderr.join("\n"), /locally modified/);
  assert.equal(await readFile(installedSkill, "utf8"), "local customization\n");

  const forcedResult = await invoke(["update", "--force"], fixture);

  assert.equal(forcedResult.exitCode, 0);
  assert.match(await readFile(installedSkill, "utf8"), /Version two\./);
});

test("uninstall removes unchanged files and preserves modified files", async (t) => {
  const cleanFixture = await makeFixture(t);
  await writeCommand(cleanFixture.repoRoot, "clean-command");
  assert.equal((await invoke(["install"], cleanFixture)).exitCode, 0);

  const cleanResult = await invoke(["uninstall"], cleanFixture);

  assert.equal(cleanResult.exitCode, 0);
  await assert.rejects(
    readFile(path.join(cleanFixture.codexHome, "skills", "clean-command", "SKILL.md")),
    { code: "ENOENT" },
  );

  const modifiedFixture = await makeFixture(t);
  await writeCommand(modifiedFixture.repoRoot, "modified-command");
  assert.equal((await invoke(["install"], modifiedFixture)).exitCode, 0);
  const modifiedSkill = path.join(
    modifiedFixture.codexHome,
    "skills",
    "modified-command",
    "SKILL.md",
  );
  await writeFile(modifiedSkill, "keep me\n");

  const modifiedResult = await invoke(["uninstall"], modifiedFixture);

  assert.equal(modifiedResult.exitCode, 1);
  assert.match(modifiedResult.stderr.join("\n"), /locally modified/);
  assert.equal(await readFile(modifiedSkill, "utf8"), "keep me\n");
});

test("list reports installed and locally modified commands", async (t) => {
  const fixture = await makeFixture(t);
  await writeCommand(fixture.repoRoot, "hello-world");
  assert.equal((await invoke(["install"], fixture)).exitCode, 0);

  const installedResult = await invoke(["list"], fixture);

  assert.equal(installedResult.exitCode, 0);
  assert.match(installedResult.stdout.join("\n"), /hello-world\s+installed/);

  await writeFile(
    path.join(fixture.codexHome, "skills", "hello-world", "SKILL.md"),
    "changed\n",
  );
  const modifiedResult = await invoke(["list"], fixture);

  assert.equal(modifiedResult.exitCode, 0);
  assert.match(modifiedResult.stdout.join("\n"), /hello-world\s+modified/);
});

test("commands fail safely when the ownership manifest is invalid", async (t) => {
  const fixture = await makeFixture(t);
  await mkdir(path.join(fixture.codexHome, ".pow"), { recursive: true });
  await writeFile(path.join(fixture.codexHome, ".pow", "manifest.json"), "not json\n");

  const result = await invoke(["list"], fixture);

  assert.equal(result.exitCode, 1);
  assert.match(result.stderr.join("\n"), /Invalid POW manifest/);
});

test("manifest validation rejects file paths outside an owned command", async (t) => {
  const fixture = await makeFixture(t);
  await mkdir(path.join(fixture.codexHome, ".pow"), { recursive: true });
  await writeFile(
    path.join(fixture.codexHome, ".pow", "manifest.json"),
    `${JSON.stringify({
      schemaVersion: 1,
      source: "POW",
      commands: {
        unsafe: {
          files: {
            "../outside": "0".repeat(64),
          },
        },
      },
    })}\n`,
  );

  const result = await invoke(["list"], fixture);

  assert.equal(result.exitCode, 1);
  assert.match(result.stderr.join("\n"), /unsafe file record/);
});
