# Build-slices: implementation plan

Implementation plan for the `build-slices` feature. See [`build-slices.md`](build-slices.md)
for the design and [`build-slices-approaches.md`](build-slices-approaches.md) for
the approach comparison.

Chosen approach: **dedicated merged-root + chroot** (Approach 3), using
**`unionfs-fuse`** (userspace FUSE) for the union mount, with the **hybrid**
lifecycle — cut once globally in `prologue()`, mount+chroot per build step.

## Guiding constraints

- Preserve existing behavior when no part declares `build-slices` (zero overhead,
  no chroot, no mounts).
- Use `unionfs-fuse` (userspace) rather than kernel `overlayfs` so the merge
  composes inside nested/overlay build instances; reuse only the low-level
  `overlays/chroot.py` primitive.
- Follow the `build-packages` code paths as the structural template.

## Phase 0 — De-risk and finalize decisions

- **Spike** the core mechanism outside the codebase: `unionfs-fuse` union of
  `<slices_dir>` and `/` (copy-on-write), chroot, run a compile against a
  slice-provided lib. Validate especially that the FUSE union works **inside a
  managed LXD/CI build instance that is itself a kernel overlay** (the key
  advantage over overlayfs) and measure FUSE overhead on an I/O-heavy build.
- Finalize open questions from the design doc:
    - **FUSE / privilege / nesting** support statement + failure behavior when
      `/dev/fuse`, `fusermount`, or `unionfs-fuse` are unavailable.
    - **Chisel `--release`** derivation from `ProjectInfo.base` + arch.
    - **Chisel binary bootstrap**: require `build-snaps: [chisel]` vs auto-ensure.
    - **`unionfs-fuse` bootstrap**: document requirement vs auto-install as a build
      dependency.
    - **OVERLAY-step interaction**: a build step must not chroot into two roots;
      define composition (e.g. build-slices branch added under the overlay when
      both are active, single chroot).
    - Output: decisions recorded back into `build-slices.md`.

## Phase 1 — Schema, feature flag, and plumbing (no runtime behavior)

- `parts.py`: add `build_slices: list[str]` to `PartSpec` with description,
  examples, and docstring (mirror `build_packages`). Add any needed property on
  `Part`.
- `features.py`: add `enable_build_slices: bool = False` to `Features`.
- `dirs.py`: add `build_slices_dir` (e.g. `work_dir / "build-slices"`).
- `executor/part_handler.py`: add `_get_build_slices(part=...)` aggregation and
  expose `handler.build_slices`; add `"build-slices"` to the `assets` dict in
  `_run_build` for rebuild invalidation.
- Unit tests: schema parse/validate, aggregation, state assets contain slices.

## Phase 2 — Cut slices globally in prologue

- `executor/executor.py`: add `_cut_build_slices()` called from `prologue()`
  (after handlers are created). Aggregate slices across handlers + any
  `extra_*`; return early when empty.
- Chisel invocation helper (in `packages/` or a new `chisel` helper): run
  `chisel cut --root=<build_slices_dir> --release=<release> <slices...>`;
  derive `<release>` from base/arch; reuse/extend `errors.ChiselError`.
- Chisel binary bootstrap per Phase 0 decision.
- Validate slice syntax (reuse `_is_list_of_slices` logic) and reject mixed
  package/slice input.
- Unit tests with chisel mocked; optional integration behind availability check.

## Phase 3 — Merged-root manager and build-step wrap

- New module (e.g. `craft_parts/build_slices/` or `executor/build_slices.py`):
  a context manager `BuildSlicesMount` that:
    - Runs `unionfs-fuse` to union the branches `[<slices_dir>, /]` with
      copy-on-write (writes to a part-scoped throwaway branch) at a merged
      mountpoint. A thin `UnionFsFuse` helper (mount via `unionfs-fuse`, unmount
      via `fusermount -u`) mirrors the shape of `overlays/overlay_fs.py`.
    - Bind-mounts the part working dirs (`part_build_dir`, install dirs) and the
      standard chroot mounts (reuse `overlays/chroot.py` helpers).
    - `chroot()`s into the merged root to run the build, then unmounts and discards
      the copy-on-write branch.
- `executor/part_handler.py`: wrap `_run_build`'s `_run_step(...)` in a
  `_conditional_build_slices_mount(...)` analogous to `_conditional_layer_mount`,
  active only when the part has build-slices (and the feature is enabled).
- Reconcile with the existing overlay mount when both are active (Phase 0
  decision).

## Phase 4 — Robustness and edge cases

- Guaranteed cleanup (`fusermount -u`, discard cow branch) on build failure or
  exception.
- Clear errors when FUSE (`/dev/fuse`, `fusermount`) or `unionfs-fuse` are
  unavailable, or on non-Linux.
- Confirm sequencer marks build dirty when the slice list changes (via assets)
  and that clean/re-run works.

## Phase 5 — Tests and documentation

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

| Area                             | Files                                                                  |
| -------------------------------- | ---------------------------------------------------------------------- |
| Schema / model                   | `craft_parts/parts.py`                                                 |
| Feature flag                     | `craft_parts/features.py`                                              |
| Directories                      | `craft_parts/dirs.py`                                                  |
| Cut orchestration                | `craft_parts/executor/executor.py`                                     |
| Aggregation + build wrap + state | `craft_parts/executor/part_handler.py`                                 |
| Merged-root manager              | new module (new `unionfs-fuse` helper + reusing `overlays/chroot.py`)  |
| Chisel helpers / errors          | `craft_parts/packages/` (deb.py / errors.py)                           |
| Tests                            | `tests/unit/...`, `tests/integration/...`                              |
| Docs                             | `docs/reference/`, `docs/explanation/`, `docs/reference/changelog.rst` |
