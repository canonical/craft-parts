# Feature: build-slices

`build-slices` is a Part key with similar semantics to `build-packages`. Instead of
Debian packages, it lists Chisel slices which are made available during the build but
are not part of the final payload.

Since there is no way to safely "mix" slices and debs in a single filesystem, build-slices
are mutually exclusive with build-packages. During the lifecycle, the slices are cut into
a separate, clean directory at the same point in time where build-packages are handled
(the prologue). During the build step, the directory containing the cut slices becomes the
system root. The part's directories (like pull, build, install, etc), plus the other lifecycle
directories (stage, prime, etc) are temporarily made available so that parts can correctly
build its source and make use of the artifacts built by other parts.

## Design decisions

The following decisions were agreed while fleshing out the feature.

- **Feature flag.** `build-slices` is gated behind a new `Features.enable_build_slices`
  flag (default disabled), mirroring `enable_overlay`. Using `build-slices` while the
  flag is disabled raises a validation error. The feature is _not_ restricted to deb-based
  hosts.
- **Mutual exclusivity (per-part).** Within a single part, `build-slices` cannot be
  combined with `build-packages` _or_ `build-snaps`. The rule is per-part: one part may
  use debs while another uses slices, since each gets its own build root.
- **Global collection, shared directory.** Like `build-packages`, the `build-slices` of
  all parts are collected into a single list and cut once, in the prologue, into a single
  shared directory. This directory lives at `<work_dir>/build-slices/` (outside any
  part's directory).
- **Chroot scope.** Only the _build_ step runs inside the chroot rooted at the shared
  slice directory. The pull step runs on the regular build system, so source-type tooling
  (e.g. `git`) is provided by the host as usual.
- **Directories visible in the chroot.** For a given part, only that part's `pull`,
  `build` and `install` directories are bind-mounted in, plus the shared `stage` and
  `prime` directories, at their normal absolute paths. Other parts' directories are not
  made visible.
- **Reuse of chroot machinery.** The build step reuses the existing
  `craft_parts/overlays/chroot.py` machinery, extended to accept extra bind mounts.
- **Build tooling is user-provided.** The slice root is clean; all required build tooling
  (compilers, interpreters, etc.) must be provided by the user through slices in
  `build-slices`. Consequently, for slice-based parts craft-parts skips the deb
  `build-packages` injected by the source handler and the plugin.
- **State invalidation.** `build-slices` is recorded in the build step's assets (alongside
  `build-packages` and `build-snaps`), so changing the slice list invalidates the build.
- **Validation errors.** A validation error is raised when `build-slices` is mixed with
  `build-packages`/`build-snaps` in the same part, and when `build-slices` is used
  while the feature flag is disabled.

## Open questions (deferred)

- **craftctl / interpreter in the clean root.** Scriptlets normally rely on `craftctl`
  and a Python environment, which won't be present in a clean slice root. Whether
  craft-parts should bind-mount its own `craftctl`/interpreter into the root, or leave it
  to the user, is left for a future decision.
- **Interaction with overlays.** Whether `build-slices` and the `overlay` feature should
  be mutually exclusive or compose is deferred.

## Implementation notes

Proof-of-concept wiring (behind `enable_build_slices`):

- `features.py` — new `enable_build_slices` flag.
- `parts.py` — `build_slices` field; feature-flag and mutual-exclusivity validators;
  `has_build_slices` on `PartSpec`/`Part` and a `part_has_build_slices` helper.
- `dirs.py` — `build_slices_dir` at `<work_dir>/build-slices`.
- `packages/deb.py` / `packages/base.py` — reusable `cut_slices()` entry point.
- `executor/executor.py` — `_cut_build_slices()` collects and cuts slices in the prologue.
- `executor/part_handler.py` — skips injected build-packages for slice parts; runs the
  build step inside the slice-root chroot with the part + shared directories bind-mounted;
  records `build-slices` in the build state assets.
- `overlays/chroot.py` — `chroot()` extended with an `extra_bind_mounts` parameter.

## Validation status

Verified in an unprivileged environment that the prologue cutting populates
`<work_dir>/build-slices/` and that the build step reaches the chroot setup. The chroot
bind mounts themselves require root privileges (the same requirement as the `overlay`
feature), so completing a chrooted build must be validated in a privileged environment.

Environment gotchas observed while testing with the Chisel snap (external to the code):

- The Chisel snap has a private `/tmp` namespace, so the cut `--root` must not live
  under `/tmp`.
- The snap `home` interface cannot write to hidden directories (e.g. `~/.cache`); the
  `--root` must be a non-hidden path the snap can access.
