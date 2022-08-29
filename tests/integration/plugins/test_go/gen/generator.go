// generator.go: Go program called by "go generate" to create the "main.go" file
// in the parent directory.

//go:generate go run generator.go

package main

import (
	"log"
	"os"
)

func main() {
	filename := "../main.go"

	f, err := os.Create(filename)

	if err != nil {
		log.Fatal(err)
	}

	defer f.Close()

	template := `
package main;

import "fmt"

func main() {
    fmt.Println("This is a generated line")
}
`

	_, err2 := f.WriteString(template)

	if err2 != nil {
		log.Fatal(err2)
	}
}
