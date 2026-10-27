package trace

import (
	"example.com/test"
	"example.com/test/core"
)

func StartSpan() string {
	return "trace-" + test.RootVersion + "-" + core.GetVersion()
}
