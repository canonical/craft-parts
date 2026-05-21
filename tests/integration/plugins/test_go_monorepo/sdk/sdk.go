package sdk

import (
	"example.com/test"
	"example.com/test/core"
	"example.com/test/metric"
	"example.com/test/trace"
)

func Initialize() string {
	return test.RootVersion + ":" + core.GetVersion() + ":" + trace.StartSpan() + ":" + metric.RecordMetric()
}
