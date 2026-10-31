const std = @import("std");

pub fn build(b: *std.Build) void {
    const module = b.createModule(.{
        .target = b.standardTargetOptions(.{}),
        .optimize = b.standardOptimizeOption(.{}),
        .link_libc = true,
    });
    module.addCSourceFile(.{ .file = b.path("answer.c") });
    const library = b.addLibrary(.{
        .name = "answer",
        .linkage = .static,
        .root_module = module,
    });
    b.installArtifact(library);
    b.installFile("answer.h", "include/answer.h");
}
