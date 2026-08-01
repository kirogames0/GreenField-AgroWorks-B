# Greenfield Agroworks: Chemical Safety & Compliance Handbook

Maintained by the Agronomy & Compliance team. This is reference prose, not
part of the `Chemicals` / `Chemical_Applications` tables in the database --
`is_restricted` in the Chemicals table tells you WHETHER a chemical is
restricted, but this handbook is where the actual procedural requirements
live: buffer zones, re-entry intervals, pre-harvest intervals, and what a
worker needs to do if something goes wrong.

## Restricted-Use Chemicals: Certified Applicator Requirement

Any chemical flagged `is_restricted = true` may only be applied by a
worker holding an active applicator certification (see `is_certified` on
the Workers table). This is a state regulatory requirement, not an
internal Greenfield policy, so it cannot be waived by a supervisor. If a
`request_pesticide_application` call is submitted by a worker who is not
certified, the request must be rejected outright rather than queued as
Pending -- a Pending record implies the request only needs approval, not
that the requester was even eligible to ask.

## Re-Entry Interval (REI)

The Re-Entry Interval is the minimum time that must pass after an
application before anyone (workers, visitors) may re-enter the treated
field without personal protective equipment (PPE). Standard REI for most
restricted-use insecticides at Greenfield is 24 hours; several
organophosphate products carry a 48-hour REI instead. Field hands should
never be scheduled into a field's row for irrigation, scouting, or harvest
prep during the REI window, even if the crop stage otherwise calls for
it -- REI compliance overrides normal field-work scheduling.

## Pre-Harvest Interval (PHI)

The Pre-Harvest Interval is the minimum number of days between the last
chemical application and harvest. PHI varies by chemical and crop, and
violating it is a compliance failure that can void a buyer contract, not
just a safety issue -- treated produce harvested before PHI has elapsed
cannot legally be sold under the chemical's label terms. When
`generate_compliance_report` shows an application close to a harvest
date, the PHI for that specific chemical/crop pairing should be checked
before assuming the harvest can proceed on schedule.

## Buffer Zone Requirements

Restricted-use chemicals applied by ground equipment require a minimum
25-foot buffer zone from any occupied structure, waterway, or
non-target crop edge; aerial application (where used) requires 100 feet.
Buffer zone violations are one of the most common causes of neighboring-
farm complaints and should be treated as a compliance incident requiring
documentation, not just a verbal correction to the applicator.

## Spill Response and First Aid

For any chemical spill exceeding one gallon, or any dermal/inhalation
exposure incident, the worker's first action is to move away from the
application area and rinse exposed skin with water for at least 15
minutes -- do not wait for a supervisor to arrive before starting
decontamination. The chemical's label (kept with the physical
container, not in this system) has the specific first-aid statement and
must be brought to any medical provider the worker sees afterward.
Spills must be reported the same day, regardless of how minor they seem,
since even small spills factor into the buffer-zone and REI compliance
record for that field.

## Record-Keeping for Compliance Reports

`generate_compliance_report` pulls from `Chemical_Applications`, but
auditors reviewing a buyer's report also expect REI/PHI adherence to be
documented, not just that an application happened. If a compliance
report is being prepared for an external buyer audit, the accompanying
notes should reference the REI and PHI that applied to each record, since
the raw table only stores the application event itself, not whether the
required waiting periods were subsequently honored.

## Unrelated Legacy Note (retained for corpus size / retrieval testing)

The Greenfield company softball league schedule is not part of chemical
compliance and should never surface in a search of this handbook; this
section exists only to confirm off-topic queries don't return noise.
