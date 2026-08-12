# Build-slices: implementation plan

Implementation plan for the `build-slices` feature. See [`build-slices.md`](build-slices.md)
for the design and [`build-slices-approaches.md`](build-slices-approaches.md) for
the approach comparison.

Chosen approach: **dedicated merged-root + chroot** (Approach 3), using
**`unionfs-fuse`** (userspace FUSE) for the union mount, with the **hybrid**
lifecycle — cut once globally in `prologue()`, mount+chroot per build step.

## Status

| Phase | Description                             | Status         |
| ----- | --------------------------------------- | -------------- |
| 0     | De-risk and finalize decisions          | ✅ Done        |
| 1     | Schema, feature flag, and plumbing      | ✅ Done        |
| 2     | Cut slices globally in prologue         | ✅ Done        |
| 3     | Merged-root manager and build-step wrap | ✅ Done        |
| 4     | Robustness and edge cases               | ⬜ Not started |
| 5     | Tests and documentation                 | ⬜ Not started |

Phases 0–3 are implemented on the `work/CRAFT-5254-build-slices-proto` branch and
validated end-to-end against a real application (bincraft), including executing a
slice-provided `ruby` interpreter inside the merged-root chroot. Per an explicit
request, **no automated tests were written for Phases 1–3** — all testing is
deferred to Phase 5.

## Guiding constraints

- Preserve existing behavior when no part declares `build-slices` (zero overhead,
  no chroot, no mounts).
- Use `unionfs-fuse` (userspace) rather than kernel `overlayfs` so the merge
  composes inside nested/overlay build instances; reuse only the low-level
  `overlays/chroot.py` primitive.
- Follow the `build-packages` code paths as the structural template.

## Phase 0 — De-risk and finalize decisions ✅ Done

- **Spike** the core mechanism outside the codebase: `unionfs-fuse` union of
  `<slices_dir>` and `/` (copy-on-write), chroot, run a compile against a
  slice-provided lib. Validate especially that the FUSE union works **inside a
  managed LXD/CI build instance that is itself a kernel overlay** (the key
  advantage over overlayfs) and measure FUSE overhead on an I/O-heavy build.
- Finalize open questions from the design doc. Outcomes (recorded in
  `build-slices.md`):
    - **FUSE / privilege / nesting**: union mounts unprivileged via setuid
      `fusermount`; composes over a nested kernel overlay; only `chroot` needs
      root. ✅ Resolved.
    - **Chisel `--release`**: **decided against** deriving `--release` from
      `ProjectInfo.base` + arch. Chisel auto-detects the release from the build
      environment (mirrors the existing `stage-packages` slice path in `deb.py`),
      avoiding a brittle base→release mapping. ✅ Resolved (deviation from the
      original plan).
    - **Chisel binary bootstrap**: **decided** to assume the `chisel` binary is
      available on `PATH`; craft-parts does not install or bootstrap it. ✅
      Resolved.
    - **`unionfs-fuse` bootstrap**: documented as an environment requirement
      (the consuming application must provide `unionfs`/`fusermount`); not
      auto-installed by craft-parts. ✅ Resolved.
    - **OVERLAY-step interaction**: a build step must not chroot into two roots;
      define composition (e.g. build-slices branch added under the overlay when
      both are active, single chroot). ⬜ **Still open — deferred to Phase 4.**

## Phase 1 — Schema, feature flag, and plumbing (no runtime behavior) ✅ Done

- `parts.py`: add `build_slices: list[str]` to `PartSpec` with description,
  examples, and docstring (mirror `build_packages`). Add any needed property on
  `Part`.
- `features.py`: add `enable_build_slices: bool = False` to `Features`.
- `dirs.py`: add `build_slices_dir` (e.g. `work_dir / "build-slices"`).
- `executor/part_handler.py`: add `_get_build_slices(part=...)` aggregation and
  expose `handler.build_slices`; add `"build-slices"` to the `assets` dict in
  `_run_build` for rebuild invalidation.
- `state_manager/build_state.py`: add `"build-slices"` to
  `properties_of_interest` (the actual driver of build-step dirty detection).
- Unit tests: schema parse/validate, aggregation, state assets contain slices.
  ⬜ **Deferred to Phase 5.**

## Phase 2 — Cut slices globally in prologue ✅ Done

- `executor/executor.py`: add `_cut_build_slices()` called from `prologue()`
  (after handlers are created, gated on `Features().enable_build_slices`).
  Aggregate slices across handlers; return early when empty.
- Chisel invocation helper: **new module `packages/chisel.py`** with
  `is_slice()`, `validate_slices()`, and `cut_slices(slices, *, root)`. Runs
  `chisel cut --root=<build_slices_dir> <slices...>` — **no `--release`/`--arch`**
  (chisel auto-detects; see Phase 0). Output is kept verbatim (no `normalize()`,
  unlike the stage-slices path — the chroot handles symlink resolution).
- Errors: new `InvalidBuildSlices` in `packages/errors.py`; reuse
  `errors.ChiselError` for cut failures.
- Validate slice syntax and reject non-slice input via `validate_slices()`.
- Chisel binary assumed available (Phase 0 decision — no bootstrap).
- Unit tests with chisel mocked; optional integration behind availability check.
  ⬜ **Deferred to Phase 5.**

## Phase 3 — Merged-root manager and build-step wrap ✅ Done

- **New module `executor/build_slices.py`**: a context manager
  `BuildSlicesMount` that:
    - Runs `unionfs-fuse` to union the branches `[<cow>, <slices_dir>, /]` with
      copy-on-write (writes to a throwaway cow branch) at a merged mountpoint. A
      thin `UnionFsFuse` helper (mount via `unionfs`, unmount via `fusermount -u`)
      mirrors the shape of `overlays/overlay_fs.py`.
    - Bind-mounts the part working dirs (`src`, `build`, install dirs, `stage`,
      `backstage`) and the standard chroot mounts (reuse `overlays/chroot.py`
      helpers) into the merged root. (See `build-slices.md` for why the bind
      mounts are required given the read-only base branch.)
    - `chroot()`s into the merged root to run the build, then unmounts and
      discards the copy-on-write branch.
- `dirs.py`: add `build_slices_mount_dir` and `build_slices_cow_dir`.
- `utils/os_utils.py`: add `mount_unionfs()` and `umount_fuse()` helpers.
- `executor/errors.py`: add `BuildSlicesMountError` and `BuildSlicesUnmountError`.
- `executor/part_handler.py`: wrap `_run_build`'s `_run_step(...)` in a
  `_conditional_build_slices_mount(...)` analogous to `_conditional_layer_mount`,
  active only when the part has build-slices (and the feature is enabled); add
  `_needs_build_slices()`.
- Reconcile with the existing overlay mount when both are active. ⬜ **Still open
  — deferred to Phase 4.**

## Phase 4 — Robustness and edge cases ⬜ Not started

- Guaranteed cleanup (`fusermount -u`, discard cow branch) on build failure or
  exception.
- Clear errors when FUSE (`/dev/fuse`, `fusermount`) or `unionfs-fuse` are
  unavailable, or on non-Linux.
- Confirm sequencer marks build dirty when the slice list changes (via assets)
  and that clean/re-run works.

## Phase 5 — Tests and documentation ⬜ Not started

- **Backfill the deferred unit tests for Phases 1–3**: schema parse/validate,
  slice aggregation, state assets contain slices, `chisel.py` cut/validate, and
  the merged-root manager. Fix the known `test_run_build` failure caused by the
  new `"build-slices"` assets key.
- Integration test mirroring `tests/integration/.../test_chisel_lifecycle.py`
  for the build-time path (real chisel where available; skip/guard otherwise).
- Unit tests for the merged-root manager (mounts, bind mounts, cleanup, error
  paths) using existing overlay test patterns as a template.
- Docs: `reference` entry for the `build-slices` key; `explanation` page for how
  build-slices work; changelog entry.

## Rollout

- Ship behind the `enable_build_slices` feature flag, off by default.
- Applications opt in once the managed-environment requirements are documented.

## File-touch summary

| Area                     | Files                                                                                           |
| ------------------------ | ----------------------------------------------------------------------------------------------- |
| Schema / model           | `craft_parts/parts.py`                                                                          |
| Feature flag             | `craft_parts/features.py`                                                                       |
| Directories              | `craft_parts/dirs.py` (`build_slices_dir`, `build_slices_mount_dir`, `build_slices_cow_dir`)    |
| Cut orchestration        | `craft_parts/executor/executor.py`                                                              |
| Aggregation + build wrap | `craft_parts/executor/part_handler.py`                                                          |
| State / dirty detection  | `craft_parts/state_manager/build_state.py` (`properties_of_interest`)                           |
| Merged-root manager      | `craft_parts/executor/build_slices.py` (new; reuses `overlays/chroot.py`)                       |
| FUSE mount helpers       | `craft_parts/utils/os_utils.py` (`mount_unionfs`, `umount_fuse`)                                |
| Merged-root errors       | `craft_parts/executor/errors.py` (`BuildSlicesMountError`, `BuildSlicesUnmountError`)           |
| Chisel helpers / errors  | `craft_parts/packages/chisel.py` (new), `craft_parts/packages/errors.py` (`InvalidBuildSlices`) |
| Tests                    | `tests/unit/...`, `tests/integration/...`                                                       |
| Docs                     | `docs/reference/`, `docs/explanation/`, `docs/reference/changelog.rst`                          |
