cfg_if::cfg_if! {
    if #[cfg(unix)] {
        fn foo() { println!("hello registry!"); /* unix specific functionality */ }
    } else if #[cfg(target_pointer_width = "32")] {
        fn foo() { println!("hello registry!"); /* non-unix, 32-bit functionality */ }
    } else {
        fn foo() { println!("hello registry!"); /* fallback implementation */ }
    }
}

fn main() {
    foo();
}
