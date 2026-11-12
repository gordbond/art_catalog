## Project Overview

`art` is a personal inventory tool for managing my available paintings. It stores images and metadata for work in two locations (my studio and the Art Gallery of Hamilton), generates filtered lists and PDF sheets to send to collectors, and builds a static gallery website hosted on my own domain.

### Goals
- Single source of truth for available paintings: image + title, medium, size, year, status, price
- Quickly answer "what do you have available?" with a list or PDF, filtered by location and size
- Publish an up-to-date public gallery with minimal effort (edit CSV, add image, build, deploy)

### Data model
- Images live in `paintings/studio/` and `paintings/agh/`; the folder determines location
- Metadata lives in `paintings/catalog.csv`, keyed by image filename
- Columns: `file, title, medium, width_in, height_in, year, status, price`
- `status` is one of `available`, `sold`, `on_hold`; rows are never deleted
- Dimensions are in inches; "size" for filtering means the longest side
- `price` is optional and may be hidden from public output

### CLI commands
- `art list` — list paintings; filters: `--location {studio,agh}`, `--status`, `--min-size`, `--max-size`
- `art list ... --pdf` — export the filtered list as a PDF with thumbnails
- `art check` — report images missing from the CSV, CSV rows missing images, and invalid values
- `art build` — generate the static site into `dist/` with resized web images

### Tech stack
- Python 3, Click (CLI), Jinja2 (HTML templates), Pillow (image resizing), WeasyPrint or ReportLab (PDF)
- Static output deployed to Cloudflare Pages / Netlify / GitHub Pages

### Conventions
- Image filenames are lowercase slugs (`harbour-at-dusk.jpg`) and act as unique IDs
- Never modify or upload original full-resolution images; only write derived copies to `dist/`
- The CSV must remain editable by hand in Excel/Numbers — no extra formatting or computed columns

## IMPORTANT

- **Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.
- **Build one module at a time.** Do not start the next until the current passes all acceptance criteria and the user approves.
- **On test failure:** Root-cause the issue. Do not suppress, work around, or wrap in try/except as a fix.
- **Never hardcode secrets.** 
- **Security is important!** Keys and other sensitive information should never be stored in plain text and never be included in any repos. Audit plans for security gaps.
- **The development plan is the source of truth.**
- **Follow the runbook.** `RUNBOOK.md` contains the module-by-module execution steps, acceptance criteria, verification commands, and deployment procedures. Reference it before starting any module.

## Behavioral Guidelines

### 1. Think Before Coding
Don't assume. Don't hide confusion. Surface tradeoffs.

Before implementing:
- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First
Minimum code that solves the problem. Nothing speculative.

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes
Touch only what you must. Clean up only your own mess.

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that **your** changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution
Define success criteria. Loop until verified.

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria allow independent iteration. Weak criteria ("make it work") require constant clarification.


