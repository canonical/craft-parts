package metric

import (
	"example.com/test"
	"example.com/test/core"
)

func RecordMetric() string {
	return "metric-" + test.RootVersion + "-" + core.GetVersion()
}
