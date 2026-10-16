# Repository guidance

- Keep the public workflow self-contained with `assets/base-baozi.jpg` (A) plus a user's runtime photo (D). Never require private paired examples.
- A supplies bun shape and scene; D supplies identity, expression and face orientation. Preserve source tilt; center by translating the feature group, not straightening it.
- Keep only the explicitly approved image A in this repository, including all commits. Do not add photos, generated previews, screenshots, archives or embedded/base64 images elsewhere.
- Runtime images and results must stay outside this repository. Do not import private skill folders or their Git history.
- Preserve the distinction between instruction validation and actual visual testing. Do not claim pixel locking or identity fidelity from prompt wording.
- Before publishing changes, run `python3 scripts/audit_public_release.py`. If intentionally changing the public file contract, review the exact additions before adjusting the allowlist.
