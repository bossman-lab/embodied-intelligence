"use strict";

const fs = require("fs/promises");
const fsSync = require("fs");
const path = require("path");
const MarkdownIt = require("markdown-it");
const texmath = require("markdown-it-texmath");
const katex = require("katex");
const cheerio = require("cheerio");

const repoRoot = path.resolve(__dirname, "..", "..");
const collator = new Intl.Collator("zh-Hans-CN", {
  numeric: true,
  sensitivity: "base",
});

const hiddenOrGeneratedDirs = new Set([
  ".git",
  ".github",
  ".specstory",
  "node_modules",
  "web",
  "dist",
  "__pycache__",
]);

const supportingDocDirs = new Set([
  "assets",
  "asset",
  "images",
  "resources",
  "external-libraries",
  "code",
  "代码",
]);

const projectAssetMap = {
  cover: "assets/main.png",
  hero: "assets/main.png",
  homepageHero: "assets/首页背景图.png",
  logo: "assets/头像 logo.jpg",
  favicon: "assets/线稿.png",
  map: "map.png",
};

const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  breaks: false,
});

md.use(texmath, {
  engine: katex,
  delimiters: "dollars",
  katexOptions: {
    throwOnError: false,
    strict: "ignore",
  },
});

addHeadingIds(md);
addLinkAndImageResolvers(md);

function toPosix(value) {
  return value.replace(/\\/g, "/");
}

function encodePathForUrl(relPath) {
  return normalizeRelPath(relPath)
    .split("/")
    .map((segment) => encodeURIComponent(segment))
    .join("/");
}

function normalizeRelPath(value) {
  const normalized = path.posix.normalize(toPosix(value));
  if (
    normalized === "." ||
    normalized.startsWith("../") ||
    normalized.includes("/../") ||
    path.posix.isAbsolute(normalized)
  ) {
    throw new Error("Invalid repository path");
  }
  return normalized;
}

function fullPathFromRel(relPath) {
  const safeRel = normalizeRelPath(relPath);
  const fullPath = path.resolve(repoRoot, safeRel);
  const relative = path.relative(repoRoot, fullPath);
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error("Path escapes repository root");
  }
  return fullPath;
}

function relPathExists(relPath) {
  try {
    return fsSync.existsSync(fullPathFromRel(relPath));
  } catch {
    return false;
  }
}

function idFromRel(relPath) {
  return Buffer.from(normalizeRelPath(relPath), "utf8").toString("base64url");
}

function relFromId(id) {
  const relPath = Buffer.from(id, "base64url").toString("utf8");
  return normalizeRelPath(relPath);
}

function safeDecodeUrl(value) {
  try {
    return decodeURI(value);
  } catch {
    return value;
  }
}

function isExternalUrl(value) {
  return (
    /^(https?:)?\/\//i.test(value) ||
    /^(mailto|tel|data):/i.test(value) ||
    hasEmail(value.trim())
  );
}

function isEnglishPath(relPath) {
  const lower = relPath.toLowerCase();
  const parts = lower.split("/");
  return (
    parts.includes("en") ||
    lower.endsWith(".en.md") ||
    path.posix.basename(lower) === "readme.en.md"
  );
}

function isSupportingDocPath(relPath) {
  return relPath
    .toLowerCase()
    .split("/")
    .some((part) => supportingDocDirs.has(part));
}

function hasChineseText(text) {
  const matches = text.match(/[\u3400-\u9fff]/g);
  return Boolean(matches && matches.length >= 6);
}

function shouldSkipDirectory(dirName) {
  return hiddenOrGeneratedDirs.has(dirName.toLowerCase());
}

function shouldSkipMarkdownFile(relPath) {
  const lower = relPath.toLowerCase();
  if (!lower.endsWith(".md")) return true;
  if (isEnglishPath(relPath)) return true;
  if (isSupportingDocPath(relPath)) return true;
  return false;
}

async function walkMarkdownFiles(directory = repoRoot, relativeBase = "") {
  const entries = await fs.readdir(directory, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    if (entry.isSymbolicLink()) continue;
    const relPath = relativeBase
      ? path.posix.join(relativeBase, entry.name)
      : entry.name;
    const fullPath = path.join(directory, entry.name);

    if (entry.isDirectory()) {
      if (shouldSkipDirectory(entry.name)) continue;
      files.push(...(await walkMarkdownFiles(fullPath, relPath)));
      continue;
    }

    if (entry.isFile() && !shouldSkipMarkdownFile(relPath)) {
      files.push(normalizeRelPath(relPath));
    }
  }

  return files;
}

async function walkStaticFiles(directory = repoRoot, relativeBase = "") {
  const entries = await fs.readdir(directory, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    if (entry.isSymbolicLink()) continue;
    const relPath = relativeBase
      ? path.posix.join(relativeBase, entry.name)
      : entry.name;
    const fullPath = path.join(directory, entry.name);

    if (entry.isDirectory()) {
      if (shouldSkipDirectory(entry.name)) continue;
      files.push(...(await walkStaticFiles(fullPath, relPath)));
      continue;
    }

    if (entry.isFile() && !entry.name.toLowerCase().endsWith(".md")) {
      files.push(normalizeRelPath(relPath));
    }
  }

  return files;
}

async function readUtf8(relPath) {
  return (await fs.readFile(fullPathFromRel(relPath), "utf8")).replace(/^\ufeff/, "");
}

function stripMarkdownInline(value) {
  return value
    .replace(/<[^>]+>/g, "")
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/[`*_~#>\[\]]/g, "")
    .replace(/&nbsp;/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function normalizeMetadataLine(value) {
  return stripMarkdownInline(value)
    .replace(/^[#>\s-]+/, "")
    .replace(/[【】]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function hasEmail(value) {
  return /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i.test(value);
}

function isAuthorMetadataLine(line) {
  const clean = normalizeMetadataLine(line);
  if (!clean) return false;
  if (/^作者\s*$/.test(clean)) return true;
  if (/^作者\s*[:：]/.test(clean) && /(联系方式|联系|邮箱|email|@)/i.test(clean)) {
    return true;
  }
  return /^作者\s*[:：]\s*\S/.test(clean) && clean.length <= 80 && !/[。！？?!]/.test(clean);
}

function isContactMetadataLine(line) {
  const clean = normalizeMetadataLine(line);
  if (!clean) return false;
  if (hasEmail(clean) && clean.length <= 90) return true;
  return /^(联系方式|联系邮箱|邮箱|email)\s*[:：]/i.test(clean);
}

function removeTopAuthorMetadata(markdown) {
  const lines = markdown.split(/\r?\n/);
  const output = [];
  let meaningfulLines = 0;
  let removingAuthorBlock = false;

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const trimmed = line.trim();
    const stillInHeaderArea = index < 16 && meaningfulLines < 6;

    if (stillInHeaderArea && isAuthorMetadataLine(line)) {
      removingAuthorBlock = true;
      continue;
    }

    if (stillInHeaderArea && removingAuthorBlock && (!trimmed || isContactMetadataLine(line))) {
      continue;
    }

    if (stillInHeaderArea && isContactMetadataLine(line)) {
      continue;
    }

    output.push(line);
    if (trimmed) {
      meaningfulLines += 1;
      removingAuthorBlock = false;
    }
  }

  return output.join("\n");
}

function stripEmojiNoise(value) {
  return value.replace(/[\u{1f300}-\u{1faff}\u{2600}-\u{27bf}]/gu, "").trim();
}

function formatSegmentTitle(segment) {
  return segment
    .replace(/\.md$/i, "")
    .replace(/^(\d+)[-_]/, "$1 · ")
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function formatDocTitle(segment) {
  const withoutExt = segment.replace(/\.md$/i, "");
  const withoutOrder = withoutExt
    // Drop file-order prefixes such as 01Foo, 02-Foo, 03_Foo, but keep names
    // such as "1X 世界模型挑战" where the digit is part of the project name.
    .replace(/^(\d{2,})(?:[-_\s.、]*)/, "")
    .replace(/^(\d{1,2})[-_\s.、]+/, "")
    .trim();
  return (withoutOrder || withoutExt).replace(/_/g, " ").replace(/\s+/g, " ").trim();
}

function titleFromPath(relPath) {
  const parts = relPath.split("/");
  const filename = parts[parts.length - 1];
  if (/^readme\.md$/i.test(filename)) {
    if (parts.length === 1) return "项目首页";
    return formatSegmentTitle(parts[parts.length - 2]);
  }
  return formatDocTitle(filename);
}

function extractHeadingTitle(markdown) {
  let inFence = false;
  for (const line of markdown.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (/^```/.test(trimmed) || /^~~~/.test(trimmed)) {
      inFence = !inFence;
      continue;
    }
    if (inFence) continue;

    const match = line.match(/^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$/);
    if (!match) continue;
    const title = stripEmojiNoise(stripMarkdownInline(match[2]));
    if (!title || /^(\d+[\s.、]*)?(简介|引言|概述|overview)$/i.test(title)) {
      continue;
    }
    return title;
  }
  return "";
}

function extractExcerpt(markdown) {
  let inFence = false;
  for (const line of markdown.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (/^```/.test(trimmed) || /^~~~/.test(trimmed)) {
      inFence = !inFence;
      continue;
    }
    if (
      inFence ||
      !trimmed ||
      trimmed.startsWith("#") ||
      trimmed.startsWith("|") ||
      trimmed.startsWith("<") ||
      trimmed.startsWith("!") ||
      trimmed.length < 16
    ) {
      continue;
    }
    const text = stripMarkdownInline(trimmed);
    if (hasChineseText(text)) return text.slice(0, 110);
  }
  return "";
}

function slugify(value, fallback = "section") {
  const clean = stripMarkdownInline(value)
    .normalize("NFKD")
    .toLowerCase()
    .replace(/[^\p{Letter}\p{Number}\s_-]+/gu, "")
    .trim()
    .replace(/\s+/g, "-");

  return clean || fallback;
}

function uniqueSlug(value, seen, fallback) {
  const base = slugify(value, fallback);
  const count = seen.get(base) || 0;
  seen.set(base, count + 1);
  return count === 0 ? base : `${base}-${count + 1}`;
}

function extractHeadings(markdown) {
  const headings = [];
  const seen = new Map();
  let inFence = false;

  for (const line of markdown.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (/^```/.test(trimmed) || /^~~~/.test(trimmed)) {
      inFence = !inFence;
      continue;
    }
    if (inFence) continue;

    const match = line.match(/^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$/);
    if (!match) continue;
    const text = stripMarkdownInline(match[2]);
    if (!text) continue;

    headings.push({
      id: uniqueSlug(text, seen, `section-${headings.length + 1}`),
      level: match[1].length,
      text,
    });
  }

  return headings;
}

function addHeadingIds(markdownIt) {
  markdownIt.core.ruler.push("heading_ids", (state) => {
    const seen = new Map();
    for (let index = 0; index < state.tokens.length - 1; index += 1) {
      const token = state.tokens[index];
      const inline = state.tokens[index + 1];
      if (token.type !== "heading_open" || inline.type !== "inline") continue;
      const text = stripMarkdownInline(inline.content);
      const id = uniqueSlug(text, seen, `section-${index}`);
      token.attrSet("id", id);
      token.attrJoin("class", "doc-heading");
    }
  });
}

function splitLocalHref(href) {
  const hashIndex = href.indexOf("#");
  if (hashIndex === -1) {
    return { filePart: href, anchor: "" };
  }
  return {
    filePart: href.slice(0, hashIndex),
    anchor: href.slice(hashIndex + 1),
  };
}

function tryResolveAbsoluteLocalPath(targetPath) {
  const normalized = targetPath.replace(/\\/g, "/");
  if (!/^[a-zA-Z]:\//.test(normalized) && !normalized.startsWith("/")) {
    return "";
  }

  const parts = normalized.split("/").filter(Boolean);
  for (let index = 0; index < parts.length; index += 1) {
    const candidate = parts.slice(index).join("/");
    if (relPathExists(candidate)) {
      return candidate;
    }
  }

  return "";
}

function resolveRepoRelative(currentRelPath, targetPath) {
  const decoded = safeDecodeUrl(targetPath).replace(/\\/g, "/");
  const absoluteCandidate = tryResolveAbsoluteLocalPath(decoded);
  if (absoluteCandidate) {
    return normalizeRelPath(absoluteCandidate);
  }
  const currentDir = path.posix.dirname(currentRelPath);
  return normalizeRelPath(path.posix.join(currentDir, decoded));
}

function fileHrefFromRel(relPath, options = {}) {
  const safeRel = normalizeRelPath(relPath);
  if (!relPathExists(safeRel)) {
    return "#";
  }
  const encoded = encodePathForUrl(safeRel);
  const version = options.withVersion === false ? "" : `?v=${Math.round(fsSync.statSync(fullPathFromRel(safeRel)).mtimeMs)}`;
  return `files/${encoded}${version}`;
}

function resolveHref(href, currentRelPath, options = {}) {
  if (!href) return { href };
  if (isExternalUrl(href)) return { href, external: true };

  const { filePart, anchor } = splitLocalHref(href);
  if (!filePart) {
    const currentId = idFromRel(currentRelPath);
    return {
      href: `#/doc/${currentId}${anchor ? `?anchor=${encodeURIComponent(anchor)}` : ""}`,
      internal: true,
    };
  }

  const targetRel = resolveRepoRelative(currentRelPath, filePart);
  const lower = targetRel.toLowerCase();
  if (lower.endsWith(".md")) {
    if (isEnglishPath(targetRel)) {
      return {
        href: "#",
        disabled: true,
        title: "当前阅读器只收录中文 Markdown 正文",
      };
    }
    return {
      href: `#/doc/${idFromRel(targetRel)}${anchor ? `?anchor=${encodeURIComponent(anchor)}` : ""}`,
      internal: true,
    };
  }

  return { href: fileHrefFromRel(targetRel, options), asset: true };
}

function addLinkAndImageResolvers(markdownIt) {
  const defaultLinkOpen =
    markdownIt.renderer.rules.link_open ||
    ((tokens, idx, renderOptions, env, self) => self.renderToken(tokens, idx, renderOptions));
  const defaultImage =
    markdownIt.renderer.rules.image ||
    ((tokens, idx, renderOptions, env, self) => self.renderToken(tokens, idx, renderOptions));

  markdownIt.renderer.rules.link_open = (tokens, idx, renderOptions, env, self) => {
    const token = tokens[idx];
    const href = token.attrGet("href");
    const resolved = resolveHref(href, env.relPath, env.linkOptions);
    token.attrSet("href", resolved.href);
    if (resolved.external) {
      token.attrSet("target", "_blank");
      token.attrSet("rel", "noopener noreferrer");
    }
    if (resolved.disabled) {
      token.attrJoin("class", "disabled-link");
      token.attrSet("aria-disabled", "true");
      token.attrSet("title", resolved.title);
    }
    return defaultLinkOpen(tokens, idx, renderOptions, env, self);
  };

  markdownIt.renderer.rules.image = (tokens, idx, renderOptions, env, self) => {
    const token = tokens[idx];
    const src = token.attrGet("src");
    if (src && !isExternalUrl(src)) {
      const resolved = resolveHref(src, env.relPath, env.linkOptions);
      token.attrSet("src", resolved.href);
    }
    token.attrSet("loading", "lazy");
    return defaultImage(tokens, idx, renderOptions, env, self);
  };
}

function transformRenderedHtml(html, currentRelPath, options = {}) {
  const $ = cheerio.load(html, { decodeEntities: false }, false);

  $("img, source").each((_, element) => {
    const node = $(element);
    const attrName = node.attr("src") ? "src" : "srcset";
    const value = node.attr(attrName);
    if (!value || isExternalUrl(value) || value.startsWith("files/")) return;
    const resolved = resolveHref(value, currentRelPath, options);
    node.attr(attrName, resolved.href);
    if (element.tagName === "img" && !node.attr("loading")) {
      node.attr("loading", "lazy");
    }
  });

  $("a").each((_, element) => {
    const node = $(element);
    const href = node.attr("href");
    if (!href || href.startsWith("#/doc/") || href.startsWith("files/")) return;
    const resolved = resolveHref(href, currentRelPath, options);
    node.attr("href", resolved.href);
    if (resolved.external) {
      node.attr("target", "_blank");
      node.attr("rel", "noopener noreferrer");
    }
    if (resolved.disabled) {
      node.addClass("disabled-link");
      node.attr("aria-disabled", "true");
      node.attr("title", resolved.title);
    }
  });

  $("table").each((_, element) => {
    const table = $(element);
    if (!table.parent().hasClass("table-wrap")) {
      table.wrap('<div class="table-wrap"></div>');
    }
  });

  return $.html();
}

function groupForDoc(relPath) {
  if (relPath === "README.md") {
    return {
      key: "__root__",
      title: "项目首页",
      sortTitle: "00-项目首页",
    };
  }

  const first = relPath.split("/")[0];
  return {
    key: first,
    title: formatSegmentTitle(first),
    sortTitle: first,
  };
}

function catalogSortPath(relPath) {
  return relPath === "README.md" ? "00-README.md" : relPath;
}

async function collectCatalog(options = {}) {
  const files = await walkMarkdownFiles();
  const docs = [];

  for (const relPath of files) {
    const markdown = await readUtf8(relPath);
    if (!hasChineseText(markdown)) continue;

    const group = groupForDoc(relPath);
    const isReadme = /(^|\/)readme\.md$/i.test(relPath);
    const title = isReadme
      ? extractHeadingTitle(markdown) || titleFromPath(relPath)
      : titleFromPath(relPath) || extractHeadingTitle(markdown);
    docs.push({
      id: idFromRel(relPath),
      relPath,
      title,
      groupKey: group.key,
      groupTitle: group.title,
      groupSortTitle: group.sortTitle,
      excerpt: extractExcerpt(markdown),
      depth: Math.max(0, relPath.split("/").length - 1),
      dirname: path.posix.dirname(relPath) === "." ? "" : path.posix.dirname(relPath),
    });
  }

  docs.sort((left, right) =>
    collator.compare(catalogSortPath(left.relPath), catalogSortPath(right.relPath)),
  );

  docs.forEach((doc, index) => {
    doc.order = index + 1;
    doc.previousId = docs[index - 1]?.id || "";
    doc.nextId = docs[index + 1]?.id || "";
  });

  const groupMap = new Map();
  for (const doc of docs) {
    if (!groupMap.has(doc.groupKey)) {
      groupMap.set(doc.groupKey, {
        key: doc.groupKey,
        title: doc.groupTitle,
        sortTitle: doc.groupSortTitle,
        docs: [],
      });
    }
    groupMap.get(doc.groupKey).docs.push(doc);
  }

  const groups = Array.from(groupMap.values()).sort((left, right) =>
    collator.compare(left.sortTitle, right.sortTitle),
  );

  const project = {
    title: "Every-Embodied 电子书",
    subtitle: "从 0 到 1 走进具身智能",
  };

  for (const [key, relPath] of Object.entries(projectAssetMap)) {
    if (fsSync.existsSync(fullPathFromRel(relPath))) {
      project[key] = fileHrefFromRel(relPath, options);
    } else {
      project[key] = "";
    }
  }

  return {
    generatedAt: new Date().toISOString(),
    project,
    stats: {
      docs: docs.length,
      groups: groups.length,
    },
    groups,
    docs,
  };
}

async function buildDocPayload(relPath, catalog, options = {}) {
  const safeRel = normalizeRelPath(relPath);
  const doc = catalog.docs.find((item) => item.relPath === safeRel);
  if (!doc) {
    throw new Error("Document not found in Chinese catalog");
  }

  const markdown = await readUtf8(safeRel);
  const displayMarkdown = removeTopAuthorMetadata(markdown);
  const rendered = md.render(displayMarkdown, {
    relPath: safeRel,
    linkOptions: options,
  });

  return {
    ...doc,
    html: transformRenderedHtml(rendered, safeRel, options),
    headings: extractHeadings(displayMarkdown),
  };
}

async function fetchGithubRepo() {
  const response = await fetch("https://api.github.com/repos/datawhalechina/every-embodied", {
    headers: {
      Accept: "application/vnd.github+json",
      "User-Agent": "every-embodied-reader",
    },
  });

  if (!response.ok) {
    throw new Error(`GitHub API returned ${response.status}`);
  }

  const repo = await response.json();
  return {
    stars: repo.stargazers_count,
    forks: repo.forks_count,
    updatedAt: repo.updated_at,
  };
}

module.exports = {
  repoRoot,
  projectAssetMap,
  normalizeRelPath,
  fullPathFromRel,
  idFromRel,
  relFromId,
  encodePathForUrl,
  fileHrefFromRel,
  walkStaticFiles,
  collectCatalog,
  buildDocPayload,
  fetchGithubRepo,
};
