package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"testing"
)

type transportFunc func(*http.Request) (*http.Response, error)

func (f transportFunc) RoundTrip(r *http.Request) (*http.Response, error) { return f(r) }

func TestSendMessage(t *testing.T) {
	client := &http.Client{Transport: transportFunc(func(r *http.Request) (*http.Response, error) {
		if r.Method != "POST" || r.URL.Path != "/botsecret/sendMessage" {
			t.Errorf("unexpected request: %s %s", r.Method, r.URL.Path)
		}
		var payload map[string]string
		if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
			t.Fatal(err)
		}
		if payload["chat_id"] != "@rza_school" || payload["text"] != "Привет" {
			t.Errorf("unexpected payload: %v", payload)
		}
		return &http.Response{StatusCode: 200, Body: io.NopCloser(strings.NewReader(`{"ok":true,"result":{"message_id":42}}`))}, nil
	})}
	id, err := sendMessage(client, "https://api.telegram.org", "secret", "@rza_school", "Привет")
	if err != nil || id != 42 {
		t.Fatalf("id=%d err=%v", id, err)
	}
}

func TestTelegramFailureDoesNotExposeToken(t *testing.T) {
	client := &http.Client{Transport: transportFunc(func(r *http.Request) (*http.Response, error) {
		return &http.Response{StatusCode: 403, Body: io.NopCloser(strings.NewReader(`{"ok":false,"error_code":403,"description":"secret"}`))}, nil
	})}
	_, err := sendMessage(client, "https://api.telegram.org", "secret", "@rza_school", "Привет")
	if err == nil || strings.Contains(err.Error(), "secret") {
		t.Fatalf("unsafe error: %v", err)
	}
	client.Transport = transportFunc(func(r *http.Request) (*http.Response, error) { return nil, fmt.Errorf("network error: %s", r.URL) })
	_, err = sendMessage(client, "https://api.telegram.org", "secret", "@rza_school", "Привет")
	if err == nil || strings.Contains(err.Error(), "secret") {
		t.Fatalf("unsafe network error: %v", err)
	}
}
