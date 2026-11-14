# art — painting inventory

```
art list                       # everything
art list --location agh        # any category folder (alias: --category)
art list --status sold
art list --max-size 30         # longest side ≤ 30"
art list --min-size 40 --pdf   # big works as art-catalog.pdf (or --pdf my.pdf)
art list --prices              # prices are hidden unless asked for (also works with --pdf)
art check                      # images vs. catalog.csv (exit 1 on errors)
art build                      # static site -> dist/   (--clean, --prices/--no-prices)
art deploy                     # rebuild, then publish dist/ to the gh-pages branch
```

## Setup

```
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Data

- Images go in a sub-folder of `paintings/` per category (e.g. `studio/`, `agh/`, or `prints/`, `drawings/`).
- `paintings/catalog.csv`: `file,title,medium,width_in,height_in,year,status,price`.
  `file` is the path under `paintings/` (e.g. `agh/flower.png`); its first folder is the category.
  `status` is one of `available`, `sold`, `on_hold`. Price may be blank.
  Filename case must match exactly (GitHub's servers are case-sensitive; `art check` flags this).
- `site.toml` (committed, so public): title, tagline, domain, `show_prices`, `currency`, `logo`/`logo_width`, `about`/`about_photo`,
  `category_label`, `[[categories]]` (key, label, optional `link` + `link_label`) and `[[size_buckets]]`.
  Leave `[[categories]]` out and the folders in `paintings/` are used, labelled from their names.
- `site.local.toml` (git-ignored, optional): overrides `site.toml`. Keep `contact_email` here so it never lands in the public repo.

## About page

Write your statement and bio in a Markdown file, for example `about.md`:

```markdown
## Artist statement
Text about the work...

## Bio
Text about you... [links](https://example.com) and *italics* work.
```

Then set `about = "about.md"` in `site.toml` (and optionally `about_photo = "portrait.jpg"`). The build adds
`about.html` and "Gallery / About" links in the header. To switch it off, set `about = ""`; the page and photo
are removed from `dist/` on the next build.

## Using this for another artist

The tool is the same for everyone; only the folder differs. In a new folder (its own git repo):

1. `paintings/<category>/` image folders and `paintings/catalog.csv`.
2. `site.toml` with their name, tagline, domain, categories, size buckets (prints may want smaller ones) and a `logo` file
   (or leave `logo` blank to show their name as text).
3. `art check`, then `art build` to preview `dist/index.html`.
4. Create their GitHub repo, `git remote add origin ...`, push `main`, run `art deploy`, then set Pages to `gh-pages`
   and add their domain's DNS records (see below).

Run `art` from that folder, or pass `--root /path/to/their/folder`.

## Publishing on GitHub Pages

Originals never leave your machine. `art deploy` rebuilds `dist/` and force-pushes only its contents
(resized copies + HTML) to the `gh-pages` branch of `origin`. Source code and `catalog.csv` go on `main`;
`paintings/studio|agh/*` images are git-ignored.

Update loop: edit the CSV / add an image → `art check` → `art deploy`.

One-time: repo → Settings → Pages → Source: **Deploy from a branch** → `gh-pages` / `(root)`.
Without a custom domain the site is at `https://gordbond.github.io/art_catalog/`.

### Connecting gordbondart.com (GoDaddy)

In GoDaddy → DNS for gordbondart.com, delete the default parked `A` record and the `www` CNAME, then add:

| Type  | Name | Value                |
|-------|------|----------------------|
| A     | @    | 185.199.108.153      |
| A     | @    | 185.199.109.153      |
| A     | @    | 185.199.110.153      |
| A     | @    | 185.199.111.153      |
| CNAME | www  | gordbond.github.io   |

Then in repo Settings → Pages set **Custom domain** to `gordbondart.com`, and once the certificate is issued
tick **Enforce HTTPS**. DNS can take from minutes to a few hours. (Check GitHub's current IPs in their
"Managing a custom domain" docs if anything doesn't resolve.)
