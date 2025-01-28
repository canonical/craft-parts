use ascii::{AsciiString};
fn main() {
    let my_str = match AsciiString::from_ascii("Hello, world!") {
        Ok(my_str) => my_str,
        Err(_) => todo!(),
    };
    println!("{}", my_str);
}
