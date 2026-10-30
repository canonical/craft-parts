const std = @import("std");

// Declared directly, because newer Zig releases removed @cImport.
extern fn answer() c_int;

pub fn main() void {
    std.debug.print("C answer: {d}\n", .{answer()});
}
