# CtxGov v0.6.13 - Auto-Publish Research

CtxGov v0.6.13 publishes the minimal owner-approved auto-publish research
surface: public repo patch, release tag, GitHub release, and Pages
verification.

## Shipped

- Publication intent token for the approved v0.6.13 public write scope.
- Local verifier for the publication intent boundary.
- Release-tag-aware live-link verifier for the v0.6.13 release page.
- README and project-page updates that keep the claim boundary explicit.

## Boundary

No public benchmark claim. No security guarantee. No provider/model call. No
adoption claim. No package publication. No hosted runtime or live adapter. No
CLI beta. No stable public spec claim.

Excluded from this release: agent-context-evals writes, org profile updates,
GitHub issue/comment writes, and LinkedIn/X posting.

## Verification

Offline verification:

```bash
python3 scripts/check_publication_intent.py
python3 scripts/check_public_surface_hardening.py
python3 -m unittest tests.test_publication_intent tests.test_public_live_links -v
```

Optional live verification after publication:

```bash
python3 scripts/check_public_live_links.py --release-tag v0.6.13-auto-publish-research
```
