# notes

My engineering knowledge base — TIL, cheatsheets, and guides. Built with
[MkDocs Material](https://squidfunk.github.io/mkdocs-material/) and deployed to
GitHub Pages at <https://notes.zufardhiyaulhaq.com>.

## Structure

```
docs/
  index.md            landing
  til/                Today I Learned  (dated, tagged blog posts)
    posts/            one file per entry: YYYY-MM-DD-slug.md
  cheatsheets/        commands grouped by tool
  guides/             full how-tos and runbooks
  tags.md             tag index
  stylesheets/        theme override to match zufardhiyaulhaq.com
mkdocs.yml
```

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
mkdocs serve        # http://127.0.0.1:8000
```

## Adding content

- **TIL:** add `docs/til/posts/YYYY-MM-DD-slug.md` with front matter
  (`date`, `authors`, `categories`, `tags`). Put a `<!-- more -->` after the
  first paragraph to set the excerpt. This is also the target for the daily
  TIL agent.
- **Cheatsheet:** add or edit a page under `docs/cheatsheets/`, then list it in
  `nav:` in `mkdocs.yml`.
- **Guide:** add a page under `docs/guides/`, then list it in `nav:`.

## Deploy (one-time setup)

1. In the repo: **Settings → Pages → Source → GitHub Actions**.
2. DNS: add a `CNAME` record `notes` → `zufardhiyaulhaq.github.io`.
3. Push to `master`. The [deploy workflow](.github/workflows/deploy.yml) builds
   the site and publishes it. The `docs/CNAME` file keeps the custom domain.
