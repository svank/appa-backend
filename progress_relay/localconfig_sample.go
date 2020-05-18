package main

import "time"

// A valid token is required for storing data in the relay
const accessToken string = "token_here"

// Time between background sweeps of the data store
const sweepInterval time.Duration = 10 * time.Minute
