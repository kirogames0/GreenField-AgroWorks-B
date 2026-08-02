Title: Field hands and applicators have no way to check REI/PHI/buffer-zone rules before acting on a compliance report or scheduling field work

## Problem

`Chemicals.is_restricted` tells us WHETHER a chemical is restricted-use,
and `generate_compliance_report` tells us WHEN an application happened
and WHO requested it. Neither tells anyone what to actually DO with that
information:

- A field hand scheduling irrigation or harvest prep has no way to check
  whether a field is still inside its Re-Entry Interval (REI) -- that
  number lives only in a physical binder in the equipment shed and in a
  few senior workers' memory.
- A compliance report prepared for a buyer audit lists application
  events, but auditors expect REI/PHI adherence to be documented
  alongside them -- right now that cross-referencing is done by hand,
  after the report is generated, by whoever happens to remember the
  relevant chemical's PHI.
- `request_pesticide_application` correctly rejects non-certified
  workers at the schema/role level, but nothing in the system explains
  *why* that's a hard requirement (it's a state regulatory rule, not an
  internal policy), which matters if a worker disputes the rejection.

This is exactly the kind of unstructured, procedural knowledge that
doesn't belong as new columns on Fields/Chemicals/Chemical_Applications
-- it's prose written by the Agronomy & Compliance team, and it'll keep
growing as new chemicals and regulations get added. We don't want to
stuff the whole handbook into every prompt that touches a field or a
chemical; we want the model to pull just the relevant section.

## What this adds

A new `search_knowledge_base(query, top_k)` tool doing keyword (BM25)
retrieval over `chemical_safety_handbook.md`, chunked by section. Same
JSON-schema-with-`additionalProperties: false` style as every other tool
in `tools_reads.py`, and it slots into `handle_tools_call()` the same way
`get_inventory` does -- no new dispatch pattern introduced.

This is read-only and available to both `field_hand` and
`certified_applicator` roles (same tier as `check_field_status`); it
doesn't touch `Chemical_Applications` or any write path.

## What's in this folder

- `keyword_search.py` -- BM25-backed store (`upsert`/`query`), no
  embeddings or external service required.
- `knowledge_base.py` -- loads `data/chemical_safety_handbook.md`, chunks
  by `##` section, indexes each chunk.
- `tool.py` -- `SEARCH_KNOWLEDGE_BASE_SCHEMA` + `search_knowledge_base`
  handler, same `(args, cursor)` shape as `check_field_status` /
  `get_inventory`.
- `demo.py` -- runnable demo: two on-topic queries, one control.
- `server_integration.py` -- the exact diff for wiring this into
  `server.py` / `tools_reads.py`.

## Demo

See `demo.py`. Querying `"how long before workers can re-enter after
spraying"` correctly returns the REI section (score 6.19) ranked above
PHI (score 2.36) -- the 24-hour/48-hour distinction and the "REI
overrides normal field-work scheduling" rule are things no query against
`Fields` or `Chemical_Applications` could produce, since they only exist
as prose in the handbook, not as a column anywhere.
