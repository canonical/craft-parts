const { echo } = require("another-dep");
module.exports = { hello: () => `hello from ${echo("1.1.0")}` };
