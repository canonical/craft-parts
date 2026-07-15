# Build-slices: comparison of implementation approaches

This document summarizes three candidate approaches for making Chisel
`build-slices` available at build time, with the pros and cons of each. It is a
decision aid; the currently favored approach is captured in
[`build-slices.md`](build-slices.md).

For all three, the shared first step is the same: run `chisel cut
--root=<slices_dir> <slices...>` to materialize the requested slices into a
separate directory. The approaches differ in _how that directory is exposed to
the build step_.

---

## Shared scenario

To compare the approaches concretely, assume a part that needs to build against
OpenSSL provided as slices (`build-slices: [openssl_libs, openssl_dev]`). Three
directories are involved.

**1. The build environment root (`/`)** — the normal system, abbreviated:

```
/                                   (build environment root)
├── bin/ -> usr/bin
├── etc/
├── lib/ -> usr/lib
└── usr/
    ├── bin/
    │   └── gcc
    ├── include/
    │   └── stdio.h
    └── lib/
        └── x86_64-linux-gnu/
            └── libc.so.6
```

**2. The build-slices directory** — the result of
`chisel cut --root=<slices_dir> openssl_libs openssl_dev`:

```
<slices_dir>/                       (run-scoped, e.g. .../parts/build-slices)
└── usr/
    ├── include/
    │   └── openssl/
    │       ├── ssl.h
    │       └── crypto.h
    └── lib/
        └── x86_64-linux-gnu/
            ├── libssl.so.3
            ├── libssl.so -> /usr/lib/x86_64-linux-gnu/libssl.so.3   (absolute!)
            ├── libcrypto.so.3
            └── libcrypto.so -> /usr/lib/x86_64-linux-gnu/libcrypto.so.3
```

**3. `CRAFT_PART_INSTALL`** — where the part installs its build output:

```
$CRAFT_PART_INSTALL/                (e.g. .../parts/mypart/install)
└── (empty at build start; the part populates it, e.g. usr/bin/myapp)
```

The question each approach answers: _when the build runs, how do these three
directories appear to the compiler and linker?_

---

## Approach 1 — Separate directory prepended to environment variables

Cut slices into a directory, then prepend it to the build environment's search
paths: `PATH`, `LD_LIBRARY_PATH`, `PKG_CONFIG_PATH`, `CPATH`,
`LIBRARY_PATH`, etc.

### What the build sees

The three directories stay physically separate; the compiler/linker are steered
via environment variables:

```
CPATH=<slices_dir>/usr/include:...
LIBRARY_PATH=<slices_dir>/usr/lib/x86_64-linux-gnu:...
LD_LIBRARY_PATH=<slices_dir>/usr/lib/x86_64-linux-gnu:...

/                                   (real root — unchanged)
<slices_dir>/usr/lib/.../libssl.so -> /usr/lib/x86_64-linux-gnu/libssl.so.3
                                        │
                                        └─ resolves against the REAL root,
                                           where libssl.so.3 does NOT exist  ✗
```

### Pros

- **Simplest to implement.** No mounts, no chroot, no elevated filesystem
  operations beyond writing files.
- **Fully non-destructive.** The system tree is never touched; the slices dir is
  trivially inspectable and removable.
- **No special privileges or kernel features.** Works without root, without
  overlayfs, and inside nested containers (LXD/CI) where mounts are restricted.
- **Cross-platform friendly.** Not tied to Linux-only overlayfs/chroot.
- **Easy caching/cleanup.** The directory is a plain artifact.

### Cons

- **Build systems frequently ignore these variables.** CMake, Meson, autotools,
  Go, Rust, and others often hardcode `/usr` or use their own sysroot logic, so
  the slices are not reliably found.
- **Absolute symlinks break.** Slices commonly contain absolute symlinks (e.g.
  `/usr/lib/... -> /lib/...`). Resolved against the real root, these point at the
  host system, not the slices dir — silently wrong or missing targets.
- **Path precedence hazards.** Prepending can shadow host tools/libraries in ways
  that are hard to predict and debug.
- **Incomplete coverage.** Only paths represented by known variables are covered;
  anything discovered by absolute path is missed.
- **Leaky abstraction.** Diverges from the `build-packages` mental model (where
  contents simply appear at their normal locations).

---

## Approach 2 — Existing overlay machinery, slices as the base layer

Reuse craft-parts' OVERLAY subsystem. The result of `chisel cut` becomes (part
of) the overlay's lower/base layer, so slice contents appear at their normal
locations within the overlaid root, and the build runs inside the existing
overlay chroot.

### What the build sees

Inside the overlay chroot, the slices layer and the system root are merged and
appear at `/`. `CRAFT_PART_INSTALL` is bind-mounted in at its usual path:

```
/                                   (overlay-merged root, inside chroot)
└── usr/
    ├── bin/
    │   └── gcc                     (base)
    ├── include/
    │   ├── stdio.h                 (base)
    │   └── openssl/ssl.h           (slices, via overlay lower layer)
    └── lib/
        └── x86_64-linux-gnu/
            ├── libc.so.6           (base)
            ├── libssl.so.3         (slices)
            └── libssl.so -> /usr/lib/x86_64-linux-gnu/libssl.so.3   ✓ resolves
                                        (absolute symlink now points at the
                                         merged root, where the target exists)

$CRAFT_PART_INSTALL                 (bind-mounted into the chroot, writable)
```

The overlay's writable upper layer also captures the slice files, so they are
part of the same stack used by the OVERLAY step and overlay-hash invalidation.

### Pros

- **Least new code.** Overlay mount + chroot + bind-mount plumbing already
  exists and is battle-tested (`overlay_fs.py`, `chroot.py`,
  `overlay_manager.py`, `_conditional_layer_mount`).
- **Correct filesystem semantics.** Absolute symlinks resolve correctly and
  contents sit on default toolchain paths — the two problems that sink
  Approach 1 disappear.
- **Non-destructive.** Writes land in the overlay upper layer; the real system
  stays clean.
- **Consistent execution model** with parts that already use overlay visibility.

### Cons

- **Couples build-slices to the OVERLAY feature.** Inherits its feature flag,
  constraints, and lifecycle — build-slices can't evolve independently.
- **Semantic entanglement.** The overlay layer has meaning for the OVERLAY step,
  `overlay-packages`, and overlay-hash-based invalidation. Injecting build-only
  slices into that stack risks confusing "what the overlay represents" and could
  leak build-time slices into overlay/stage/prime semantics.
- **Ordering/composition complexity.** A part that uses _both_ overlay-packages
  and build-slices needs a well-defined layer order; getting this wrong causes
  subtle shadowing bugs.
- **Feature scope creep.** Overlay is already one of the more complex,
  experimental subsystems; overloading it increases its surface and blast radius.
- **Same privilege/kernel constraints** as Approach 3 (root, overlayfs, nesting),
  but now inseparable from the broader overlay feature.

---

## Approach 3 — Dedicated `unionfs-fuse` merge, separate from the overlay machinery

Cut slices into a directory, then present a **union** of that directory and the
system root as a merged root using a dedicated mechanism built on
**`unionfs-fuse`** (userspace FUSE) plus the low-level `chroot` primitive, and
chroot into it to run the build. Independent of the OVERLAY step.

### What the build sees

Identical merged view to Approach 2 — but the union is a standalone,
build-slices-only stack (`unionfs-fuse` branches `[<slices_dir>, /]`) with its
own throwaway copy-on-write branch, unrelated to the OVERLAY step:

```
/                                   (build-slices merged root, inside chroot)
└── usr/
    ├── bin/gcc                     (base)
    ├── include/
    │   ├── stdio.h                 (base)
    │   └── openssl/ssl.h           (slices)
    └── lib/x86_64-linux-gnu/
        ├── libc.so.6               (base)
        ├── libssl.so.3             (slices)
        └── libssl.so -> /usr/lib/x86_64-linux-gnu/libssl.so.3         ✓ resolves

$CRAFT_PART_INSTALL                 (bind-mounted into the chroot, writable)

# unionfs-fuse branches = [<slices_dir> (cow), / (RO)]  ← dedicated, not OVERLAY's
# copy-on-write branch  = throwaway, discarded after the build
```

### Pros

- **Correct filesystem semantics.** Like Approach 2, absolute symlinks resolve
  and contents appear on default paths — Approach 1's failures are avoided.
- **Non-destructive.** The copy-on-write branch is discarded after the build; the
  system tree is untouched.
- **Composes when nested.** Being userspace FUSE, `unionfs-fuse` works even when
  the build instance is itself a kernel overlay — it sidesteps the fragile
  overlay-on-overlay case that afflicts Approach 2.
- **No kernel overlayfs dependency.** Only needs FUSE (`/dev/fuse`,
  `fusermount`) and the `unionfs-fuse` package.
- **Decoupled and purpose-built.** Owns its own semantics, feature flag, and
  lifecycle; no entanglement with OVERLAY-step meaning or invalidation.
- **Clear mental model.** "build-slices are merged over the system root just for
  the build," directly analogous to `build-packages` appearing in the build
  environment.
- **Reuses the proven `chroot` primitive** without inheriting the full overlay
  subsystem.

### Cons

- **More code than Approach 2.** A dedicated manager (cut, mount, bind, chroot,
  cleanup) must be written and tested, duplicating some plumbing conceptually.
- **Requires FUSE + `unionfs-fuse`.** Needs `/dev/fuse`, `fusermount`, and the
  `unionfs-fuse` package available in the build environment.
- **Performance.** FUSE adds userspace overhead versus kernel overlayfs; the
  merged root is slower to traverse for I/O-heavy builds.
- **Execution-model shift.** Non-overlay builds currently run in place; wrapping
  the build in a chroot changes how the build step executes and requires careful
  bind-mounting of the part's working dirs.
- **Linux-only.** FUSE/chroot are not portable to other platforms.
- **Two merge stacks to reconcile.** If a part _also_ uses the OVERLAY step, the
  design must define how the independent build-slices merge composes with the
  existing overlay chroot for the same build step.

---

## At-a-glance comparison

| Criterion                     | 1. Env vars | 2. Overlay base layer | 3. Dedicated unionfs-fuse |
| ----------------------------- | ----------- | --------------------- | ------------------------- |
| Implementation effort         | Lowest      | Low                   | Medium                    |
| Correct symlink/path handling | No          | Yes                   | Yes                       |
| Non-destructive               | Yes         | Yes                   | Yes                       |
| Privileges/kernel needs       | None        | root + overlayfs      | FUSE + unionfs-fuse       |
| Works in nested containers    | Yes         | Fragile               | Yes                       |
| Cross-platform                | Yes         | No (Linux)            | No (Linux)                |
| Runtime overhead              | None        | Low (kernel)          | Medium (FUSE)             |
| Coupling to OVERLAY feature   | None        | High                  | Low                       |
| Independent evolution         | Yes         | No                    | Yes                       |
| Build-system compatibility    | Poor        | High                  | High                      |

## Notes

- Approaches 2 and 3 share the same correctness benefits (absolute symlinks
  resolve, contents on default paths) and both chroot the build on Linux, but
  differ in **merge technology** and **coupling**: 2 leans on the kernel-overlay
  OVERLAY subsystem, while 3 stands alone on userspace `unionfs-fuse`. The FUSE
  choice lets Approach 3 compose inside nested/overlay build instances where
  Approach 2's kernel overlay-on-overlay is fragile, at the cost of FUSE runtime
  overhead and a `unionfs-fuse` dependency.
- Approach 1 is the only one that avoids privileged filesystem operations, at the
  cost of correctness and build-system compatibility.
