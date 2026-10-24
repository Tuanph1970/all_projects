# Vendored wheels — `vnstock` and `vnai`

**These are here because the packages were withdrawn from public PyPI.**
Without them this repo cannot build `stock-data-service` from scratch.

Verified 2026-10-24:

```
$ docker run --rm python:3.11-slim pip download --no-deps vnstock==4.0.7
ERROR: No matching distribution found for vnstock==4.0.7
```

`vnstock` **and its dependency `vnai`** both return HTTP 404 on PyPI. The
vendor moved to generation 5 (released 2026-10-15), which is distributed
through a **registered, keyed channel** — `vnstock register` then
`vnstock install`, with a stated 365-day limit per version — not public PyPI.
See Backlog `#96`.

## Why builds appeared to keep working

Docker layer caching. `requirements.txt` had not changed, so the
`pip install -r requirements.txt` layer was reused on every rebuild and the
withdrawn package was never fetched again. The break only surfaces when that
layer is invalidated — **any** change to `requirements.txt`, a
`docker builder prune`, or a build on a different machine.

## Where these came from

Repacked from the already-installed distributions inside the running
`stock_data_service` image, using their surviving `.dist-info/RECORD` to
decide which top-level paths each distribution owns. They are genuine wheels,
not an archive: verified by installing into a clean `python:3.11-slim`
alongside the public index and exercising the API (`Quote.history` returned 25
rows; `Finance(source="KBS").ratio` returned its 58x6 frame).

The pip HTTP cache inside the image was checked first and does **not** contain
the originals, so repacking was the only route.

## How the build uses them

`--find-links` with the public index still enabled, so the withdrawn packages
resolve locally while every other dependency resolves normally. Do not add
`--no-index`: it would also block `requests`, `pandas` and the rest.

## Do not treat this as a fix

It restores **buildability**, not supportability. The vendor is on gen 5 and
these artifacts are frozen at 4.0.7, which is also the version whose `ratio()`
is corrupted (Backlog `#97`). The real decision — register for gen 5, or move
off vnstock — is `#96`.
