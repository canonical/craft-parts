package core

import "example.com/test"

func GetVersion() string {
	return "core-" + test.RootVersion
}
