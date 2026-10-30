const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});
    const options = b.addOptions();
    options.addOption([]const u8, "message", b.option([]const u8, "message", "Greeting") orelse "Hello from Zig!");

    const executable = b.addExecutable(.{
        .name = "hello",
        .root_module = b.createModule(.{
            .root_source_file = b.path("main.zig"),
            .target = target,
            .optimize = optimize,
        }),
    });
    executable.root_module.addOptions("options", options);
    b.installArtifact(executable);

    const library = b.addLibrary(.{
        .name = "answer",
        .linkage = .static,
        .root_module = b.createModule(.{
            .root_source_file = b.path("answer.zig"),
            .target = target,
            .optimize = optimize,
        }),
    });
    b.installArtifact(library);
    b.installFile("answer.h", "include/answer.h");
    b.installFile("message.txt", "share/hello/message.txt");
}
