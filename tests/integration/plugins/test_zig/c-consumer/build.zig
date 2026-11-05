const std = @import("std");

pub fn build(b: *std.Build) void {
    const module = b.createModule(.{
        .root_source_file = b.path("main.zig"),
        .target = b.standardTargetOptions(.{}),
        .optimize = b.standardOptimizeOption(.{}),
        .link_libc = true,
    });
    module.linkSystemLibrary("answer", .{ .use_pkg_config = .no });
    b.installArtifact(b.addExecutable(.{
        .name = "hello",
        .root_module = module,
    }));
}
