# gijsovergoor-site

A static site generator for the site owner's academic website. Public
content is sourced from a private Vault via a sanitized, owner-approved
snapshot: nothing in the private Vault is read by the build or deploy
path, only the committed, reviewed `data/public/snapshot.yaml` is.

## Install

```bash
python -m pip install --editable ".[dev]"
```

## Update cycle

Routine content updates follow this cycle:

1. Update Vault records.
2. `python -m site_builder.update`
3. Review `review/public-content-inventory.md` and the logged snapshot
   diff.
4. `python -m site_builder.approve`
5. `python -m site_builder.update` (now passes)
6. Commit `data/public/snapshot.yaml` and `data/public/APPROVED.sha256`.
7. Push (GitHub Pages deploys).

Step 2 fails on the first run of a new content cycle because the snapshot
has changed since the last approval — that is the review gate working as
intended. Step 3 is the only step that requires human judgment; every other
step is mechanical.

`python -m site_builder.links` is an optional release-time check that the
external links in the approved snapshot still resolve. It is not part of
the routine cycle above.

Routine content changes that add or remove a public project also require
updating the expected inventory in `tests/test_content_contract.py`.
