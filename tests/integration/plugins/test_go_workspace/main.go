package main

import (
	"fmt"
	"github.com/jessevdk/go-flags"
	"os"
)

type Options struct {
	Say string `long:"say" description:"What to say" optional:"yes" default:"Hello world"`
}

var options Options

var parser = flags.NewParser(&options, flags.Default)

func main() {
	if _, err := parser.Parse(); err != nil {
		switch flagsErr := err.(type) {
		case flags.ErrorType:
			if flagsErr == flags.ErrHelp {
				os.Exit(0)
			}
			os.Exit(1)
		default:
			os.Exit(1)
		}
	}
	fmt.Printf("%s\n", options.Say)
}
