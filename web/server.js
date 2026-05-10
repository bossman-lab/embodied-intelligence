"use strict";

const path = require("path");
const express = require("express");
const {
  repoRoot,
  fullPathFromRel,
  normalizeRelPath,
  collectCatalog,
  buildDocPayload,
  fetchGithubRepo,
} = require("./lib/content");

const publicRoot = path.join(__dirname, "public");
const port = Number(process.env.PORT || 5178);

let githubRepoCache = {
  value: null,
  expiresAt: 0,
};

const app = express();

app.get("/favicon.png", (_request, response, next) => {
  try {
    response.sendFile(fullPathFromRel("assets/线稿.png"));
  } catch (error) {
    next(error);
  }
});

app.get("/data/catalog.json", async (_request, response, next) => {
  try {
    response.json(await collectCatalog());
  } catch (error) {
    next(error);
  }
});

app.get("/data/github.json", async (_request, response, next) => {
  try {
    const now = Date.now();
    if (githubRepoCache.value && githubRepoCache.expiresAt > now) {
      response.json(githubRepoCache.value);
      return;
    }

    githubRepoCache = {
      value: await fetchGithubRepo(),
      expiresAt: now + 5 * 60 * 1000,
    };
    response.json(githubRepoCache.value);
  } catch (error) {
    next(error);
  }
});

app.get("/data/docs/:id.json", async (request, response, next) => {
  try {
    const catalog = await collectCatalog();
    const relPath = catalog.docs.find((item) => item.id === request.params.id)?.relPath;
    if (!relPath) {
      response.status(404).json({ error: "Document not found in Chinese catalog" });
      return;
    }

    response.json(await buildDocPayload(relPath, catalog));
  } catch (error) {
    next(error);
  }
});

app.get("/files/*", (request, response, next) => {
  try {
    const relPath = normalizeRelPath(decodeURIComponent(request.params[0]));
    response.sendFile(fullPathFromRel(relPath));
  } catch (error) {
    next(error);
  }
});

app.use("/vendor/katex", express.static(path.join(repoRoot, "node_modules", "katex", "dist")));
app.use(express.static(publicRoot));

app.get("*", (_request, response) => {
  response.sendFile(path.join(publicRoot, "index.html"));
});

app.use((error, _request, response, _next) => {
  console.error(error);
  response.status(500).json({ error: error.message || "Server error" });
});

app.listen(port, () => {
  console.log(`Every-Embodied reader is running at http://localhost:${port}`);
});
