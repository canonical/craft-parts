//! Build script to derive the package version from git tags.

use std::process::Command;

fn main() {
    // Files to watch mtime of and trigger a rerun of this script
    // if they have changed.
    const RERUN_FILES: &[&str] = &[
        ".git/HEAD",
        ".git/refs/tags",
        ".git/packed-refs",
        "src",
        "craft_parts",
    ];
    for file in RERUN_FILES {
        println!("cargo:rerun-if-changed={file}");
    }

    let version = git_describe().unwrap_or("0.0.0.dev0+unknown".into());

    println!("cargo:rustc-env=CRAFT_PARTS_CARGO_VERSION={version}");
}

fn git_describe() -> Option<String> {
    let output = Command::new("git")
        .args([
            "describe",
            "--dirty",
            "--long",
            "--match",
            "[0-9]*.[0-9]*.[0-9]*",
            "--exclude",
            "*[^0-9.]*",
        ])
        .output()
        .ok()?;

    if !output.status.success() {
        return None;
    }

    let raw = String::from_utf8(output.stdout).ok()?;

    Some(normalize_pep440(raw.trim()))
}

fn normalize_pep440(describe: &str) -> String {
    let (core, dirty) = match describe.strip_suffix("-dirty") {
        Some(c) => (c, true),
        None => (describe, false),
    };

    let mut parts = core.rsplitn(3, '-');
    let sha = parts.next().unwrap_or("");
    let distance = parts.next();
    let tag = parts.next();

    let mut version = match (tag, distance) {
        // Distance "0" == exactly on a tag
        (Some(tag), Some("0")) => tag.to_string(),
        // N commits past a tag: "0.1.0.devN+g<HASH>"
        (Some(tag), Some(n)) => format!("{tag}.dev{n}+{sha}"),
        // No tag at all (shallow clone?)
        _ => format!("0.0.0.dev0+{sha}"),
    };

    if dirty {
        if version.contains('+') {
            version.push_str(".dirty");
        } else {
            version.push_str("+dirty");
        }
    }

    version
}
