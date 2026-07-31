# GitHub Issues — Person B (Server Core & Real-time Behavior)

Paste each section below as a separate GitHub Issue. Assign each to
yourself. Reference the issue number in your PR title/description
("Closes #N") when you merge the work that resolves it.

---

## Issue 1: No client-side guarantee that risky tools are actually supported before use

**Problem**
The agent currently has no way to know, before it tries to call
`request_pesticide_application`, whether the server it's connected to
actually supports the safety mechanisms that tool depends on
(specifically `elicitation`). If a client assumes every server
supports elicitation and one doesn't, a controlled-substance
application could complete with no human sign-off at all — the exact
failure mode this project is supposed to prevent.

**Constraint**
Capability support cannot be assumed in either direction. The MCP
`initialize` handshake exists specifically so the server can declare
what it actually supports and the client can check that declaration
before relying on it, instead of silently assuming compatibility.

**Acceptance criteria**
- [ ] Server's `initialize` response declares `elicitation`,
      `resources`, `prompts`, and `tools.listChanged` capabilities
      accurately (i.e., matching what's actually implemented, not
      aspirational).
- [ ] Server does not accept `tools/list` or `tools/call` requests
      before receiving the client's `initialized` notification.
- [ ] Agent explicitly reads `capabilities.elicitation` from the
      initialize response and does NOT expose/offer
      `request_pesticide_application` if it's false — falls back to
      read-only tools only.
- [ ] A test run exists showing this fallback actually happening (not
      just described) — e.g. a modified client that omits elicitation
      support and confirms it never sees the pesticide tool as
      callable.

---

## Issue 2: Tool availability doesn't reflect who's actually authenticated on the session

**Problem**
Right now, any connected session could in principle call
`request_pesticide_application`, regardless of whether the person
behind that session is a certified pesticide applicator. A field hand
should never even see that tool as an option — not "see it but get
denied," but genuinely not have it in their tool list — because a
front-desk or field-hand session has no business initiating a
controlled-substance application. Static tool lists can't express
this; the tool set has to actually change when a session's role
changes mid-connection.

**Constraint**
The tool set must change without requiring the client to reconnect or
poll on a timer. MCP's `notifications/tools/list_changed` exists
specifically for this: a server-initiated push telling the client
"go re-fetch tools/list, something changed."

**Acceptance criteria**
- [ ] Sessions start as `field_hand` by default (least privilege) with
      only read-only tools visible via `tools/list`.
- [ ] An `authenticate` action exists that, given a worker ID, upgrades
      the session's role if that worker is a certified applicator in
      the `workers` table.
- [ ] The notification fires **only** on a genuine role transition —
      re-authenticating as the same role must not re-fire it (avoids a
      "notification spam" anti-pattern that would just train the
      client to ignore these).
- [ ] Agent reacts to the notification by re-calling `tools/list` and
      updating what it presents as callable — demoed end-to-end: call
      pesticide tool as field_hand (unavailable) → authenticate as
      applicator → notification fires → tool now callable.

---

## Issue 3: Compliance report generation blocks the client with no feedback for its full duration

**Problem**
`generate_compliance_report` scans every chemical-application record
for a buyer across a date range, field by field. For a buyer with
applications across many fields and a wide date range, this is a
genuinely slow operation. Leaving the client blocked with zero
feedback until the entire report finishes is a bad experience and
gives no way to detect a hang vs. a genuinely long-running job.

**Constraint**
The tool must report real intermediate progress tied to actual work
completed (fields processed so far), not a fake progress bar
disconnected from the real computation. Progress must correlate to
the original request via the `progressToken` the client provides, per
the MCP progress spec — not by guessing which tool call is "the slow
one" client-side.

**Acceptance criteria**
- [ ] Client passes a `progressToken` in the `tools/call` request for
      `generate_compliance_report`.
- [ ] Server sends `notifications/progress` after each field's records
      are processed, with `progress` (fields done) and `total` (fields
      to process) matching real state, not placeholders.
- [ ] Test case uses at least 3 distinct fields for one buyer so at
      least 3 progress updates are observable in the demo transcript,
      not just a single jump from 0 to 100%.
- [ ] Final tool result still returns the complete report content —
      progress notifications supplement the response, they don't
      replace it.

---

## Issue 4 (supporting, shared with Person C): Tool input schemas need real constraints, not bare types

**Problem**
The read-only tools I own (`check_field_status`, `get_inventory`,
`generate_compliance_report`) need typed, constrained JSON Schemas —
required fields and `additionalProperties: false` — so a malformed or
extra-field call fails validation before it ever reaches handler code,
rather than the handler having to guess what a stray field means.

**Constraint**
Rubric requires schema-level constraints beyond bare types on every
tool, not just the risky write tool.

**Acceptance criteria**
- [ ] All three read-only tool schemas defined with `required` and
      `additionalProperties: false`.
- [ ] `field_id` and `chemical_id` use regex `pattern` constraints
      matching actual ID formats in the seed data, not free-text
      strings.
- [ ] Real, non-placeholder `description` fields on every tool and
      parameter (graders can tell a copy-pasted stub from an actual
      description).
