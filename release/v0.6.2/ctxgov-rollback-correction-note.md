# CtxGov v0.6.2.post1 Rollback And Correction Note

Status: prepared rollback/correction note. Do not publish unless a package,
GitHub Release, or announcement needs correction.

## Package Correction

If the official PyPI package is published with incorrect metadata, broken
install behavior, or unsafe public copy:

- yank the affected PyPI release instead of deleting history;
- publish a corrected post release;
- update the GitHub Release with a correction note;
- keep the original receipt and add a superseding receipt;
- do not overwrite or imply that the original artifact never existed.

If only TestPyPI is affected:

- do not make official install claims from the TestPyPI artifact;
- record the failed preview state;
- rerun TestPyPI with a corrected package before PyPI publication.

## GitHub Release Correction

If a GitHub Release copy is published before the official PyPI install path is
verified:

- edit the release body to remove install claims;
- add a correction note that official PyPI verification was not complete at the
  time of publication;
- keep the tag unless the tag points to the wrong source commit;
- record the corrected release URL and before/after body hashes.

## Announcement Correction

If an announcement over-claims the release:

- publish a correction in the same channel when possible;
- remove claims about security, performance, universal compatibility, stable
  protocol status, automatic remediation, maintainer endorsement, or downstream
  OSS evaluation;
- point users to the GitHub Release and package receipt;
- do not contact downstream maintainers as part of the correction unless a
  separate maintainer-outreach lane is approved.

## Current Boundary

At preparation time:

- TestPyPI publication and clean install smoke passed.
- Official PyPI publication has not run.
- GitHub Release for `v0.6.2.post1` has not been created.
- Package-first announcement has not been published.
- Maintainer outreach remains blocked for v0.6.2.
