# Adapters

One YAML file per host. **This directory is the fetch allowlist** — a host with
no file here (and not in `INTEL_ALLOWED_HOSTS`) is refused at add-time.

Adding a source is a data change, reviewable in a diff, with no Python release.
That is the whole answer to "every new source means new selectors".

## Fields

| Field | Meaning |
|---|---|
| `host` | Registrable host. Subdomains match automatically; omit `www.` |
| `currency` | Default when the markup does not say. `VND` if omitted |
| `tiers` | Which rungs to run, in precedence order. Omit to run all five |
| `state_paths` | Dotted paths into `__NEXT_DATA__` etc. Promotes the `state` rung from confidence 75 to 90 |
| `selectors.price` | CSS selector for the current price |
| `selectors.title` | CSS selector for the product title |
| `selectors.unavailable` | If this matches, the listing is out of stock |
| `notes` | Why this file looks the way it does. Write it down |

## Before adding one

Run the ladder against a few real product pages on the host first:

```bash
python3 back_end/scripts/spike_price_sources.py --skip-probes --urls urls.txt
```

If `jsonld` already fires at confidence 90+, **write a minimal file with no
selectors**. A selector that is never used is a selector that rots silently and
then fires wrong after a redesign.
