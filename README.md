# art — painting inventory

```
art list                       # everything
art list --location agh        # studio | agh
art list --status sold
art list --max-size 30         # longest side ≤ 30"
art list --min-size 40 --pdf   # big works as art-catalog.pdf (or --pdf my.pdf)
art list --prices              # prices are hidden unless asked for (also works with --pdf)
art check                      # images vs. catalog.csv (exit 1 on errors)
art build                      # static site -> dist/   (--clean, --prices/--no-prices)
```

## Setup

```
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Data

- Images go in `paintings/studio/` or `paintings/agh/`.
- `paintings/catalog.csv`: `file,title,medium,width_in,height_in,year,status,price`.
  `file` is the path under `paintings/` (e.g. `agh/flower.png`) and its first folder *is* the location.
  Price may be blank. Filename case must match exactly (GitHub's servers are case-sensitive; `art check` flags this).
- `site.toml`: site title, tagline, domain, `show_prices`, optional `contact_email`.

## Publishing on GitHub Pages

1. Push to `https://github.com/gordbond/art_catalog.git` on branch `main`.
2. Repo → Settings → Pages → Source: **GitHub Actions**. The workflow in `.github/workflows/pages.yml`
   runs `art check` + `art build` on every push and deploys `dist/`.
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
