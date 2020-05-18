package main

/*
Because GCP doesn't seem to have a serverless option in the free tier that
supports web sockets, we use this relay to get progress information to the
browser. This simple app has two endpoints, one for storing a string under a
given key (if the correct access token is provided) and one for retrieving the
latest data stored under a given key. A background goroutine periodically sweeps
old entries while this instance is alive.
*/

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"time"
	"sync"
)

var dataStore sync.Map
var timestamps sync.Map
func main() {
	http.HandleFunc("/get", getHandler)
	http.HandleFunc("/store", storeHandler)
	//http.HandleFunc("/sweep", sweepHandler)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
		log.Printf("Defaulting to port %s", port)
	}

	go sleepAndSweep()

	log.Printf("Listening on port %s", port)
	if err := http.ListenAndServe(":"+port, nil); err != nil {
		log.Fatal(err)
	}
}

func storeHandler(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/store" {
		http.NotFound(w, r)
		return
	}

	if err := r.ParseForm(); err != nil {
		fmt.Fprint(w, "invalid form data\n")
		return
	}

	providedAccessToken := r.FormValue("token")
	if providedAccessToken == "" {
		fmt.Fprint(w, "no token provided")
		return
	} else if providedAccessToken != accessToken {
		fmt.Fprint(w, "invalid token")
		return
	}

	key := r.FormValue("key")
	if key == "" {
		fmt.Fprint(w, "no key\n")
		return
	}

	if len(key) > 100 {
		fmt.Fprint(w, "key is too long")
		return
	}

	value := r.FormValue("value")
	if value == "" {
		fmt.Fprint(w, "no value\n")
		return
	}

	if len(value) > 1000 {
		fmt.Fprint(w, "data is too long")
		return
	}

	dataStore.Store(key, value)
	timestamps.Store(key, int64(time.Now().Unix()))
}

func getHandler(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/get" {
		http.NotFound(w, r)
		return
	}

	if err := r.ParseForm(); err != nil {
		fmt.Fprint(w, "invalid form data\n")
		return
	}

	key := r.FormValue("key")
	if key == "" {
		fmt.Fprint(w, "no key\n")
		return
	}

	if len(key) > 100 {
		fmt.Fprint(w, "key is too long")
		return
	}

	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Cache-Control", "no-cache")

	value, ok := dataStore.Load(key)
	if !ok {
		fmt.Fprint(w, "{\"error\": \"invalid key\"}")
		return
	}

	fmt.Fprint(w, value.(string))
}


func sweepHandler(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/sweep" {
		http.NotFound(w, r)
		return
	}
	if r.Header.Get("X-Appengine-Cron") != "true" {
		log.Printf("Invalid cron request")
		return
	}

	sweep()
}

func sleepAndSweep() {
	time.Sleep(sweepInterval)
	sweep()
	go sleepAndSweep()
}

func sweep() {
	i := 0
	var now int64 = int64(time.Now().Unix())
	timestamps.Range(func(k interface{}, v interface{}) bool {
		if now - v.(int64) > 60 {
			dataStore.Delete(k)
			timestamps.Delete(k)
			i += 1
		}
		return true
	})
	log.Printf("Swept %d entries", i)
}
