# Reviewer Packet

Use this packet for lightweight external review of the public-safe Memory X-Ray
release surface.

## Scope

Review the homepage, README, release notes, evidence summary, technical note,
claim lint, leak scan, and 60-second demo script.

## Questions

1. Does the public copy clearly communicate the user problem within 30 seconds?
2. Are the evidence links sufficient to support the narrow report-shape claim?
3. Do any phrases imply benchmark performance, adoption, security guarantees,
   provider compatibility, package availability, or protocol stability?
4. Are the limits and rollback path visible enough for a cautious engineering
   audience?
5. Does the demo show a real before/after workflow without exposing private
   trace contents or fixture internals?

## Expected Output

Please provide:

- Any claim-boundary wording that should be tightened.
- Any finding type or evidence-span shape that is confusing.
- Any missing provenance or rollback detail.
- Any visual/demo edit that would improve comprehension without expanding the
  claim.

## Out Of Scope

Do not score model quality, security effectiveness, provider compatibility,
adoption, package readiness, or public benchmark performance from this pack.
