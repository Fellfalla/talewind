# AGENTS.md — Rules for AI Agents

Guidelines for working on this project. For architecture, state, APIs, and implementation details see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Philosophy

This is a small, fun project — an AI-narrated RPG you open in a browser and play with friends. No build step, no bundler, no backend. One HTML file, instant deploy. Keep it that way.

Iterate fast. Ship small changes. Don't over-engineer.

---

## Development Workflow

**Every change goes through a worktree.** Never commit directly to `main`.

```
1. Create worktree    →  git worktree add ../talewind-<branch> -b <branch>
2. Implement          →  All changes happen in the worktree
3. Self-review        →  Verify quality gates below
4. Human review       →  Owner reviews the diff
5. Merge & squash     →  Only after approval, then delete worktree
```

If using Claude Code's `isolation: "worktree"` agent mode, let it handle worktree creation automatically.

### Branch Naming

```
feat/<short-description>     — new features or content
fix/<short-description>      — bug fixes
refactor/<short-description> — structural improvements
chore/<short-description>    — maintenance, docs, config
```

### Merge Protocol

1. Offer to merge only after self-review passes and owner approves
2. Squash-merge into `main` with a clean commit message
3. Delete the branch and worktree
4. Bump `CACHE_NAME` in `sw.js` if `index.html` changed

Do NOT merge without explicit owner approval. Do NOT leave orphaned worktrees.

### Allowed Git Commands

**`git push` is forbidden.** The owner handles all pushes and merges manually. Agents may only use the git commands whitelisted in `.claude/settings.local.json`:

```
git checkout, git worktree, git add, git commit, git log, git branch
```

That's it. No `push`, no `merge`, no `rebase`, no `reset`. If you need something outside this list, ask the owner.

---

## Self-Review Quality Gates

Before presenting changes for review, verify ALL of the following.

### Correctness
- [ ] Does exactly what was requested — nothing more, nothing less
- [ ] Edge cases handled (empty states, boundary values, error paths)
- [ ] No regressions — existing functionality still works
- [ ] State mutations correct and complete

### Code Quality
- [ ] Functions small, single-purpose, clearly named
- [ ] No dead code, commented-out code, or TODO placeholders
- [ ] No duplication — extract if same logic appears twice
- [ ] Consistent with existing codebase patterns
- [ ] `useCallback` on all functions in effects or passed as props

### Security & Robustness
- [ ] No XSS vectors or injection risks
- [ ] API keys never logged, exposed, or committed
- [ ] All async operations in try/catch with user-facing errors
- [ ] AbortControllers for cancellable network requests

### Performance
- [ ] No unnecessary re-renders (stable refs, correct deps)
- [ ] No memory leaks (timers cleared, listeners removed)

### Project-Specific
- [ ] Single-file architecture preserved
- [ ] Inline styles via `st` object
- [ ] All 5 data maps in sync if content touched
- [ ] Narrator tags updated in all 3 places if new tags added
- [ ] `CACHE_NAME` bumped if `index.html` changed
- [ ] Mobile layout checked (700px and 480px breakpoints)

---

## Rules

Hard-won rules from the project's evolution. Follow them.

### Architecture

1. **Single-file architecture is intentional.** No splitting, no bundler, no build step. The zero-toolchain design is a feature.
2. **One React component** (`RPGGameMaster`). Don't extract sub-components unless >3000 lines.
3. **Inline styles via the `st` object.** No CSS files, no Tailwind. Colors in the `C` object. The only `<style>` block is for base resets and responsive media queries.
4. **`useCallback` on all functions** referenced in effects or passed as props.

### Narrator & Content

5. **Narrator personalities must be restrained.** Nuanced and concise. No purple prose, no text affectations. Voice personality comes from ElevenLabs, not text manipulation. Include restraint guidance like "don't overdo it."
6. **AI responses: 1-2 paragraphs.** Trust players' imagination. End turns with a light, open-ended prompt — not a list of options.
7. **Tag-based narrator communication.** Tags: `[ROLL:]`, `[INVENTORY:]`, `[HP:]`, `[SFX:]`, `[TURN:]`. Always route through `processNarratorResponse()` — never parse inline.
8. **New narrator tags** require updates in three places: (a) system prompt in `narratorPrompt()`, (b) parsing in `processNarratorResponse()`, (c) tag stripping in `speakNarration()`.
9. **All 5 data maps must stay in sync.** SCENARIOS, CLASSES, RACES, STARTER_ITEMS, SKILL_TREES. Exactly 6 classes/races, 3 items/skills per class.

### Voice & Audio

10. **AbortController for all ElevenLabs TTS.** No fire-and-forget.
11. **Strip ALL control tags before TTS.**
12. **SFX scheduled, not immediate.** Use `scheduleSfx()` for proportional timing.
13. **Voice recognition continuous** with auto-restart. Clear ref before `.stop()`.

### Mobile & PWA

14. **Must work on phones.** Side panel restructures at 700px, adjusts at 480px.
15. **Safe area insets mandatory** on game container, input bar, modals.
16. **`body` must NOT have `overflow: hidden`** — only the playing-phase game container. This was a real bug.
17. **Bump `CACHE_NAME`** in `sw.js` on every deploy.
18. **Use `dvh` units** (not `vh`) for game container height.

### Multiplayer

19. **Turn advancement is narrator-driven** via `[TURN:]` tags. Round-robin is fallback only.
20. **Dead characters (hp === 0) skipped** in turn rotation.
21. **Active turn visually obvious** — tab highlighting, placeholder, turn badge.

### Error Handling

22. **All async operations** in try/catch with user-facing error toasts via `saveMsg`.
23. **Anthropic 400 errors** usually mean insufficient credits. Parse and display the full error.
24. **Character name regex** — names with special characters or substring matches may break tag parsing.

### Task Tracking

25. **Check `TODOs.md` before starting work.** It tracks known bugs and planned improvements. If your change completes a listed item, tick it off (`- [x]`) as part of the same commit.
