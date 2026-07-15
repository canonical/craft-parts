# Design: `build-slices` for craft-parts

## Summary

Add a new part property, `build-slices`, that makes Chisel-provided software
artifacts available in the build environment. It is the Chisel analogue of
`build-packages`: where `build-packages` installs Debian packages into the build
environment via apt, `build-slices` cuts Chisel slices and exposes them to the
build step.

## Motivation

Chisel produces fine-grained slices of Debian packages. Today craft-parts can
consume slices only as `stage-packages` (cut into an isolated staging area via
`chisel cut --root=<install_path>`). There is no way to make slices available
_at build time_, which is required when a part must compile or link against
slice-provided headers, libraries, or tools that are not (or should not be)
installed as full Debian packages.

## Goals

- Provide slices to the build step of a part, analogous to `build-packages`.
- Keep the host/build-environment system tree clean (non-destructive).
- Correctly handle slice contents that use absolute symlinks and expect to live
  on default toolchain paths (`/usr/lib`, `/usr/include`, `PATH`, etc.).

## Non-goals

- Replacing `build-packages` or `stage-packages`.
- Mixing packages and slices in a single field.
- Changing the existing OVERLAY step or `overlay-packages` behavior.

## Background: how the analogues work today

- **`build-packages`** (`PartSpec.build_packages`, `parts.py`): aggregated across
  _all_ parts in `Executor.prologue()` -> `_install_build_packages()`, installed
  system-wide (`/`) via `apt-get install`, recorded in build state
  (`part_handler.py`, `assets["build-packages"]`) so edits trigger a rebuild.
- **`build-snaps`**: same prologue pattern.
- **Chisel / `stage-packages`**: `_is_list_of_slices()` detects slice syntax
  (`<pkg>_<slice>`); `_unpack_stage_slices()` runs
  `chisel cut --root=<install_path> <slices>` into an isolated staging area.
  The `chisel` binary is currently obtained via `build-snaps: [chisel]`.
- **Overlay/chroot machinery** (reused as primitives):
    - `overlays/overlay_fs.py` `OverlayFS` -- wraps Linux `overlayfs`
      (`lowerdir`/`upperdir`/`workdir`).
    - `overlays/chroot.py` `chroot()` -- runs a callable inside a chroot with the
      required bind mounts (`/dev`, `/proc`, `/sys`, resolv.conf, apt sources).
    - `_run_build()` already wraps the build in `_conditional_layer_mount(...)`,
      which mounts an overlay and chroots when a part needs overlay visibility.
      This is the exact integration shape build-slices will follow.

## Rejected alternatives

1. **Cut slices into `/`.** True `build-packages` analogue, but Chisel is
   designed to populate an _empty_ rootfs; cutting into a live system clobbers
   base-system files, leaves no dpkg record, and trashes unmanaged hosts.
2. **Cut into a prefix + inject `PATH`/`LD_LIBRARY_PATH`/`PKG_CONFIG_PATH`.**
   Keeps the system clean, but many build systems ignore these variables, and
   slice **absolute symlinks** resolve against the wrong root. Fragile.
3. **Reuse the existing OVERLAY subsystem directly.** Fastest to build, but
   couples build-slices to the overlay feature flag and its semantics. Rejected
   in favor of a dedicated, decoupled mechanism.

## Chosen design: dedicated merged-root + chroot

Cut slices into a **separate directory**, then present a **union** of that
directory and the system root as a merged root, and **chroot** into it to run
the build step. Chrooting makes absolute symlinks resolve correctly and puts
slice contents on the default toolchain paths, solving the two problems that
sink the prefix approach — while keeping the real system tree untouched.

The mechanism is **dedicated to build-slices** (its own manager/flow). It uses
**`unionfs-fuse`** (userspace FUSE) for the union mount and reuses the low-level
`chroot` primitive. `unionfs-fuse` is chosen over kernel `overlayfs` because it
runs in userspace: it composes cleanly when the build instance is itself an
overlay (avoiding the fragile overlay-on-overlay case) and does not depend on
kernel overlayfs support.

### Lifecycle (hybrid: cut once, mount per build step)

1. **Cut once (global), in `Executor.prologue()`**
    - Aggregate `build-slices` across all parts (plus any plugin/source-provided
      slices, if we choose to support that source later), like `build-packages`.
    - `chisel cut --root=<slices_dir> <slices...>` into a run-scoped directory
      (e.g. under the craft-parts work/cache dir).
    - Skip entirely when no part declares `build-slices` (zero overhead/default
      behavior preserved).

2. **Mount + chroot (per build step)**, wrapping `_run_build()`'s
   `_run_step(...)` call:
    - `unionfs-fuse` union the branches `<slices_dir>` and `<system_root>`
      (slices take priority so they augment/shadow the base) at a merged
      mountpoint, using copy-on-write so writes land in a part-scoped throwaway
      branch and never touch the real system tree.
    - Bind-mount the part's working dirs (`part_build_dir`, install dirs, etc.)
      and the standard chroot mounts into the merged root.
    - `chroot()` into the merged root and execute the build.
    - On exit: unmount (`fusermount -u`) and discard the copy-on-write branch,
      leaving the system clean. The shared `<slices_dir>` persists for the run and
      is reused by every part's build step.

### What the build sees

Given a part with `build-slices: [openssl_libs, openssl_dev]`, the three
directories involved and the resulting merged root inside the build chroot:

```
/                                   (build environment root, before merge)
└── usr/
    ├── bin/gcc
    ├── include/stdio.h
    └── lib/x86_64-linux-gnu/libc.so.6

<slices_dir>/                       (chisel cut --root=<slices_dir> ...)
└── usr/
    ├── include/openssl/ssl.h
    └── lib/x86_64-linux-gnu/
        ├── libssl.so.3
        └── libssl.so -> /usr/lib/x86_64-linux-gnu/libssl.so.3   (absolute)

/                                   (merged root, inside the build chroot)
└── usr/
    ├── bin/gcc                     (base)
    ├── include/
    │   ├── stdio.h                 (base)
    │   └── openssl/ssl.h           (slices)
    └── lib/x86_64-linux-gnu/
        ├── libc.so.6               (base)
        ├── libssl.so.3             (slices)
        └── libssl.so -> /usr/lib/x86_64-linux-gnu/libssl.so.3   ✓ resolves

$CRAFT_PART_INSTALL                 (bind-mounted into the chroot, writable)

# unionfs-fuse branches = [<slices_dir> (RW/cow), / (RO)]   ·   cow branch = throwaway
```

The chroot makes the slice's absolute symlink resolve against the merged root
(where the target exists) instead of the real system root.

### State / rebuild invalidation

Record the resolved `build-slices` in the build state `assets` dict alongside
`build-packages`/`build-snaps` (`part_handler.py`), so changing the slice list
marks the build step dirty and forces a rebuild.

## Phase 0 findings (validated by spike)

Spiked on Ubuntu 24.04 amd64. Core mechanic confirmed end-to-end with **real
`chisel cut` output**; see the notes below.

- **Union mechanic works and is non-destructive.** `unionfs -o cow
"<cow>=RW:<slices>=RO:/=RO" <mountpoint>` correctly merges the slice tree over
  the system root (slice files and base files both visible), and copy-on-write
  writes land in the throwaway `<cow>` branch — the real `/` is never modified.
- **FUSE mount needs no root.** The union mounts via the setuid `fusermount`, so
  the mount itself works unprivileged. This is a real advantage over kernel
  overlayfs. (The `chroot` step still needs `CAP_SYS_CHROOT`/root, as the
  existing overlay code already assumes.)
- **No overlay-on-overlay problem.** Because the union is userspace FUSE, it
  composes on top of a build instance that is itself a kernel overlay.
- **Symlink resolution confirmed.** With the real slice output, symlinks resolve
  correctly relative to the merged root (== chroot behavior), e.g.
  `usr/lib64/ld-linux-x86-64.so.2 -> ../lib/x86_64-linux-gnu/...`,
  `lib -> usr/lib`.
- **`chisel cut` release selection works.** `chisel cut --release ubuntu-24.04
--root <dir> <slices>` fetched from the archive and produced a valid tree.

Practical notes for later phases:

- **Package/binary names.** The `unionfs-fuse` package provides the binary
  `/usr/bin/unionfs` (plus `unionfsctl`) and depends on **`libfuse2`**
  (`libfuse.so.2`). Unmount with `fusermount -u <mountpoint>`.
- **Chisel emits relative symlinks** (at least for glibc/openssl libs), so the
  primary justification for the chroot is putting slice contents on **default
  absolute toolchain/linker paths** (`/usr/lib`, `/usr/include`, ld.so,
  pkg-config), with absolute-symlink correctness as a secondary benefit.
- **`allow_other`/`user_allow_other`.** If the chrooted build process runs as a
  different uid than the one that created the FUSE mount, the mount needs
  `-o allow_other`, which requires `user_allow_other` in `/etc/fuse.conf`. To
  verify in Phase 3.
- **Chisel snap confinement gotcha.** The strictly-confined `chisel` **snap**
  cannot write to arbitrary paths (private `/tmp`, restricted filesystem). The
  `slices_dir` must live where the chisel snap can access it, or chisel should be
  sourced as a deb. Feeds the "chisel bootstrap" decision.

## Open questions / decisions to finalize

1. **Feature gating.** Introduce a `Features` flag (e.g. `build_slices_enabled`)?
   Likely yes, given the mount/chroot requirements.
2. **Privilege / FUSE / nesting.** _Resolved by spike:_ the FUSE union mount
   works unprivileged and composes over a nested overlay; only the `chroot` step
   needs root (already assumed by the overlay code). Requirements: `/dev/fuse`,
   `fusermount`, the `unionfs-fuse` package (binary `unionfs`), and `libfuse2`.
   Still need a support statement + clear error when these are unavailable.
3. **Chisel `--release` selection.** _Confirmed workable:_ `chisel cut
--release ubuntu-24.04 ...` succeeds; derive `<release>` from
   `ProjectInfo.base`/arch.
4. **Chisel binary bootstrap.** Require `build-snaps: [chisel]` (status quo), or
   have craft-parts ensure the `chisel` tool automatically before cutting? Note
   the snap-confinement gotcha above may favor a deb-sourced chisel.
5. **`unionfs-fuse` bootstrap.** Ensure `unionfs-fuse` (+ `libfuse2`) is present
   in the build environment (document requirement vs. auto-install as a build
   dependency).
6. **Interaction with the OVERLAY step.** If a project also uses
   `overlay`/`overlay-packages`, define whether the build-slices merged root
   composes with the overlay layer or is independent (current lean: independent,
   but both cannot naively chroot the same build step -- must reconcile).
7. **Slice sources.** Only part-declared `build-slices`, or also plugin/source
   contributions (as `build-packages` supports)? Start with part-declared only.
8. **Manifest/reporting.** Whether cut slices appear in the build manifest.
9. **Non-Linux platforms.** `unionfs-fuse`/chroot are Linux-only; define behavior
   elsewhere (error/unsupported).

## Rough implementation surface (for the eventual plan)

- `parts.py`: add `build_slices` field to `PartSpec` (+ docs/examples).
- `features.py`: optional feature flag.
- New module, e.g. `executor/build_slices.py` or `overlays`-adjacent: the
  dedicated merged-root manager (cut, `unionfs-fuse` mount, chroot, cleanup)
  reusing the `chroot` primitive.
- `executor/executor.py`: cut slices in `prologue()` (new `_cut_build_slices()`).
- `executor/part_handler.py`: aggregate slices (`_get_build_slices()`), wrap the
  build step in the merged-root chroot, add `build-slices` to build-state assets.
- `packages/` (Chisel helpers): `--release`/arch selection, error handling
  (reuse/extend `ChiselError`).
- Tests: unit (schema, aggregation, state invalidation) + integration
  (mirroring `tests/integration/.../test_chisel_lifecycle.py`).
- Docs: reference entry for the `build-slices` key + explanation.
