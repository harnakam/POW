#!/usr/bin/env node

import { createHash } from "node:crypto";
import {
  chmod,
  copyFile,
  mkdir,
  readFile,
  readdir,
  rename,
  rm,
  stat,
  writeFile,
} from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const MANIFEST_VERSION = 1;
const COMMAND_NAME = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const HASH = /^[a-f0-9]{64}$/;
const SCRIPT_PATH = fileURLToPath(import.meta.url);
const DEFAULT_REPO_ROOT = path.resolve(path.dirname(SCRIPT_PATH), "..");

class PowError extends Error {}

function defaultIo() {
  return {
    stdout: (message) => console.log(message),
    stderr: (message) => console.error(message),
  };
}

function emptyManifest() {
  return {
    schemaVersion: MANIFEST_VERSION,
    source: "POW",
    commands: {},
  };
}

function assertCommandName(name) {
  if (!COMMAND_NAME.test(name) || name.length > 63) {
    throw new PowError(`Command name "${name}" must be kebab-case and at most 63 characters.`);
  }
}

function parseFrontmatter(content, commandName) {
  const normalized = content.replaceAll("\r\n", "\n");
  if (!normalized.startsWith("---\n")) {
    throw new PowError(`${commandName}/SKILL.md must start with YAML frontmatter.`);
  }

  const end = normalized.indexOf("\n---\n", 4);
  if (end === -1) {
    throw new PowError(`${commandName}/SKILL.md has invalid YAML frontmatter.`);
  }

  const metadata = {};
  for (const line of normalized.slice(4, end).split("\n")) {
    const match = /^([a-z][a-z0-9_-]*):\s*(.*?)\s*$/.exec(line);
    if (!match) {
      throw new PowError(`${commandName}/SKILL.md has invalid YAML frontmatter.`);
    }
    metadata[match[1]] = match[2].replace(/^(["'])(.*)\1$/, "$2");
  }

  if (!metadata.name || !metadata.description) {
    throw new PowError(`${commandName}/SKILL.md frontmatter requires name and description.`);
  }
  if (metadata.name !== commandName) {
    throw new PowError(
      `${commandName}/SKILL.md name must match its directory (found "${metadata.name}").`,
    );
  }
  assertCommandName(metadata.name);

  const body = normalized.slice(end + 5).trim();
  if (!body) {
    throw new PowError(`${commandName}/SKILL.md must include instructions.`);
  }
  if (/\b(?:TODO|TBD)\b/i.test(normalized)) {
    throw new PowError(`${commandName}/SKILL.md contains an unfinished placeholder.`);
  }
}

async function hashFile(filePath) {
  const content = await readFile(filePath);
  return createHash("sha256").update(content).digest("hex");
}

async function collectFileHashes(root, relative = "") {
  const current = path.join(root, relative);
  const entries = await readdir(current, { withFileTypes: true });
  const files = {};

  for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
    const childRelative = relative ? path.join(relative, entry.name) : entry.name;
    if (entry.isSymbolicLink()) {
      throw new PowError(`Symbolic links are not allowed in commands: ${childRelative}`);
    }
    if (entry.isDirectory()) {
      Object.assign(files, await collectFileHashes(root, childRelative));
      continue;
    }
    if (!entry.isFile()) {
      throw new PowError(`Unsupported file type in command: ${childRelative}`);
    }
    files[childRelative.split(path.sep).join("/")] = await hashFile(path.join(root, childRelative));
  }

  return files;
}

async function validateCommands(repoRoot) {
  const commandsRoot = path.join(repoRoot, "commands");
  let entries;
  try {
    entries = await readdir(commandsRoot, { withFileTypes: true });
  } catch (error) {
    if (error.code === "ENOENT") {
      throw new PowError(`Commands directory not found: ${commandsRoot}`);
    }
    throw error;
  }

  const commands = [];
  for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
    if (entry.isSymbolicLink()) {
      throw new PowError(`Symbolic links are not allowed in commands: ${entry.name}`);
    }
    if (!entry.isDirectory()) {
      throw new PowError(`commands/ may contain only command directories: ${entry.name}`);
    }

    assertCommandName(entry.name);
    const commandRoot = path.join(commandsRoot, entry.name);
    let skill;
    try {
      skill = await readFile(path.join(commandRoot, "SKILL.md"), "utf8");
    } catch (error) {
      if (error.code === "ENOENT") {
        throw new PowError(`${entry.name}/SKILL.md is required.`);
      }
      throw error;
    }
    parseFrontmatter(skill, entry.name);
    const files = await collectFileHashes(commandRoot);
    commands.push({ name: entry.name, root: commandRoot, files });
  }

  if (commands.length === 0) {
    throw new PowError("No commands found in commands/.");
  }
  return commands;
}

function validateManifest(manifest) {
  if (
    !manifest ||
    manifest.schemaVersion !== MANIFEST_VERSION ||
    manifest.source !== "POW" ||
    !manifest.commands ||
    Array.isArray(manifest.commands) ||
    typeof manifest.commands !== "object"
  ) {
    throw new PowError("Invalid POW manifest: unsupported or malformed schema.");
  }

  for (const [name, command] of Object.entries(manifest.commands)) {
    try {
      assertCommandName(name);
    } catch {
      throw new PowError("Invalid POW manifest: malformed command name.");
    }
    if (!command || !command.files || typeof command.files !== "object") {
      throw new PowError("Invalid POW manifest: malformed command record.");
    }
    for (const [relative, hash] of Object.entries(command.files)) {
      const normalized = path.posix.normalize(relative);
      if (
        path.posix.isAbsolute(relative) ||
        normalized === ".." ||
        normalized.startsWith("../") ||
        normalized !== relative ||
        !HASH.test(hash)
      ) {
        throw new PowError("Invalid POW manifest: unsafe file record.");
      }
    }
  }
  return manifest;
}

async function loadManifest(manifestPath) {
  let content;
  try {
    content = await readFile(manifestPath, "utf8");
  } catch (error) {
    if (error.code === "ENOENT") return null;
    throw error;
  }

  try {
    return validateManifest(JSON.parse(content));
  } catch (error) {
    if (error instanceof PowError) throw error;
    throw new PowError(`Invalid POW manifest: ${error.message}`);
  }
}

async function pathExists(target) {
  try {
    await stat(target);
    return true;
  } catch (error) {
    if (error.code === "ENOENT") return false;
    throw error;
  }
}

function sameFileMap(left, right) {
  const leftEntries = Object.entries(left).sort();
  const rightEntries = Object.entries(right).sort();
  return (
    leftEntries.length === rightEntries.length &&
    leftEntries.every(([file, hash], index) => {
      const [otherFile, otherHash] = rightEntries[index];
      return file === otherFile && hash === otherHash;
    })
  );
}

async function installedState(destination, record) {
  if (!(await pathExists(destination))) return "missing";
  try {
    const files = await collectFileHashes(destination);
    return sameFileMap(files, record.files) ? "installed" : "modified";
  } catch {
    return "modified";
  }
}

async function copyCommand(source, destination) {
  await mkdir(destination, { recursive: true });
  for (const relative of Object.keys(source.files)) {
    const platformRelative = relative.split("/").join(path.sep);
    const sourceFile = path.join(source.root, platformRelative);
    const destinationFile = path.join(destination, platformRelative);
    await mkdir(path.dirname(destinationFile), { recursive: true });
    await copyFile(sourceFile, destinationFile);
    const sourceStat = await stat(sourceFile);
    await chmod(destinationFile, sourceStat.mode);
  }
}

async function writeManifest(manifestPath, manifest) {
  await mkdir(path.dirname(manifestPath), { recursive: true });
  const temporary = `${manifestPath}.${process.pid}.tmp`;
  await writeFile(temporary, `${JSON.stringify(manifest, null, 2)}\n`, { mode: 0o600 });
  await rename(temporary, manifestPath);
}

async function synchronize(mode, context, force) {
  const commands = await validateCommands(context.repoRoot);
  const manifest = (await loadManifest(context.manifestPath)) ?? emptyManifest();
  const actions = [];

  for (const command of commands) {
    const destination = path.join(context.skillsRoot, command.name);
    const record = Object.hasOwn(manifest.commands, command.name)
      ? manifest.commands[command.name]
      : undefined;
    const exists = await pathExists(destination);

    if (!record && exists) {
      throw new PowError(`${command.name} already exists and is not owned by POW.`);
    }
    if (!record) {
      actions.push({ type: "install", command, destination });
      continue;
    }

    const state = await installedState(destination, record);
    if (state === "modified" && !force) {
      throw new PowError(`${command.name} is locally modified; rerun update with --force to replace it.`);
    }
    if (state === "missing") {
      actions.push({ type: "install", command, destination });
    } else if (mode === "update") {
      actions.push({ type: "update", command, destination });
    } else {
      actions.push({ type: "skip", command, destination });
    }
  }

  for (const action of actions) {
    if (action.type === "skip") {
      context.io.stdout(`Already installed ${action.command.name}`);
      continue;
    }
    if (action.type === "update") {
      await rm(action.destination, { recursive: true, force: true });
    }
    await copyCommand(action.command, action.destination);
    manifest.commands[action.command.name] = {
      files: action.command.files,
      installedAt: new Date().toISOString(),
    };
    context.io.stdout(
      `${action.type === "update" ? "Updated" : "Installed"} ${action.command.name}`,
    );
  }

  await writeManifest(context.manifestPath, manifest);
  return 0;
}

async function uninstall(context) {
  const manifest = await loadManifest(context.manifestPath);
  if (!manifest) {
    context.io.stdout("No POW commands installed.");
    return 0;
  }

  let preserved = false;
  for (const [name, record] of Object.entries(manifest.commands)) {
    const destination = path.join(context.skillsRoot, name);
    const state = await installedState(destination, record);
    if (state === "modified") {
      context.io.stderr(`${name} is locally modified and was preserved.`);
      preserved = true;
      continue;
    }
    if (state === "installed") {
      await rm(destination, { recursive: true, force: true });
    }
    delete manifest.commands[name];
    context.io.stdout(`Removed ${name}`);
  }

  if (Object.keys(manifest.commands).length === 0) {
    await rm(context.manifestPath, { force: true });
    await rm(path.dirname(context.manifestPath), { recursive: true, force: true });
  } else {
    await writeManifest(context.manifestPath, manifest);
  }
  return preserved ? 1 : 0;
}

async function listInstalled(context) {
  const manifest = await loadManifest(context.manifestPath);
  if (!manifest || Object.keys(manifest.commands).length === 0) {
    context.io.stdout("No POW commands installed.");
    return 0;
  }

  for (const [name, record] of Object.entries(manifest.commands).sort()) {
    const state = await installedState(path.join(context.skillsRoot, name), record);
    context.io.stdout(`${name}\t${state}`);
  }
  return 0;
}

function usage() {
  return [
    "Usage: node scripts/pow.mjs <command> [--force]",
    "",
    "Commands:",
    "  install     Install missing POW commands",
    "  update      Update POW-owned commands",
    "  uninstall   Remove unchanged POW-owned commands",
    "  list        Show installed command status",
    "  validate    Validate repository commands",
  ].join("\n");
}

export async function run(args, options = {}) {
  const defaults = defaultIo();
  const io = {
    stdout: options.stdout ?? defaults.stdout,
    stderr: options.stderr ?? defaults.stderr,
  };
  const repoRoot = path.resolve(options.repoRoot ?? DEFAULT_REPO_ROOT);
  const codexHome = path.resolve(
    options.codexHome ?? process.env.CODEX_HOME ?? path.join(os.homedir(), ".codex"),
  );
  const context = {
    io,
    repoRoot,
    codexHome,
    skillsRoot: path.join(codexHome, "skills"),
    manifestPath: path.join(codexHome, ".pow", "manifest.json"),
  };
  const force = args.includes("--force");
  const positional = args.filter((argument) => argument !== "--force");
  const command = positional[0];

  try {
    if (positional.length !== 1 || !command || command === "help" || command === "--help") {
      io.stdout(usage());
      return command === "help" || command === "--help" ? 0 : 1;
    }
    if (force && command !== "update") {
      throw new PowError("--force is supported only with update.");
    }

    if (command === "validate") {
      const commands = await validateCommands(repoRoot);
      io.stdout(`Validated ${commands.length} command${commands.length === 1 ? "" : "s"}.`);
      return 0;
    }
    if (command === "install" || command === "update") {
      return await synchronize(command, context, force);
    }
    if (command === "uninstall") return await uninstall(context);
    if (command === "list") return await listInstalled(context);

    throw new PowError(`Unknown command: ${command}\n\n${usage()}`);
  } catch (error) {
    io.stderr(error instanceof PowError ? error.message : `POW failed: ${error.message}`);
    return 1;
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === SCRIPT_PATH) {
  process.exitCode = await run(process.argv.slice(2));
}
