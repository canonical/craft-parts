//! Build script to stage the craft_parts_docs package (docs/common) into
//! OUT_DIR for wheel builds.

use std::path::Path;
use std::{env, fs};

fn main() {
    // Files to watch mtime of and trigger a rerun of this script
    // if they have changed.
    const RERUN_FILES: &[&str] = &["src", "craft_parts", "docs/common"];
    for file in RERUN_FILES {
        println!("cargo:rerun-if-changed={file}");
    }

    stage_craft_parts_docs();
}

/// Copy docs/common into OUT_DIR so maturin can graft it into the wheel as
/// the craft_parts_docs package (see the `include` entry in pyproject.toml).
fn stage_craft_parts_docs() {
    let source = Path::new("docs/common");
    if !source.is_dir() {
        // Not present, e.g. when building from a source checkout without docs.
        return;
    }
    let out_dir = env::var_os("OUT_DIR").expect("OUT_DIR is always set for build scripts");
    copy_dir_all(source, Path::new(&out_dir)).expect("failed to stage craft_parts_docs");
}

fn copy_dir_all(source: &Path, target: &Path) -> std::io::Result<()> {
    fs::create_dir_all(target)?;
    for entry in fs::read_dir(source)? {
        let entry = entry?;
        let path = entry.path();
        let target = target.join(entry.file_name());
        if path.is_dir() {
            copy_dir_all(&path, &target)?;
        } else {
            fs::copy(&path, &target)?;
        }
    }
    Ok(())
}
