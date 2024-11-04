package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"os/exec"
)

type URLRequest struct {
	URL string `json:"url"`
}

type JSONResponse map[string]interface{}

func main() {
	http.HandleFunc("/process", processHandler)
	http.Handle("/", http.FileServer(http.Dir("./static")))
	fmt.Println("Server started at localhost:8080")
	http.ListenAndServe(":8080", nil)
}

func processHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Invalid request method", http.StatusMethodNotAllowed)
		return
	}

	var req URLRequest
	err := json.NewDecoder(r.Body).Decode(&req)
	if err != nil {
		http.Error(w, "Error parsing JSON", http.StatusBadRequest)
		return
	}

	// Step 1: Write URL to a text file
	err = ioutil.WriteFile("valid_urls.txt", []byte(req.URL), 0644)
	if err != nil {
		http.Error(w, "Error writing URL to file", http.StatusInternalServerError)
		return
	}

	// Step 2: Run Go processor to create JSON output
	cmd := exec.Command("./processor") // Assumes "processor" is your compiled Go processor
	err = cmd.Run()
	if err != nil {
		http.Error(w, "Error running Go processor", http.StatusInternalServerError)
		return
	}

	// Step 3: Call Python script to further process JSON output
	cmd = exec.Command("python3", "ner.py")
	output, err := cmd.Output()
	if err != nil {
		http.Error(w, "Error running Python script", http.StatusInternalServerError)
		return
	}

	// Step 4: Send text response back to frontend
	w.Header().Set("Content-Type", "text/plain")
	w.Write(output)
}
