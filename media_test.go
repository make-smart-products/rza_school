package main

import (
	"crypto/sha256"
	"encoding/hex"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestMediaUploadPreservesCaptionAndConfirmsFile(t *testing.T) {
	for _, kind := range []string{"photo", "animation"} {
		t.Run(kind, func(t *testing.T) {
			path := filepath.Join(t.TempDir(), "asset.png")
			asset := []byte("test media bytes")
			if err := os.WriteFile(path, asset, 0600); err != nil {
				t.Fatal(err)
			}
			hash := sha256.Sum256(asset)
			draft := mediaDraft{Path: path, Kind: kind, Caption: "Пример", CaptionHTML: "<b>Пример</b>", RenderSHA256: hex.EncodeToString(hash[:])}
			client := &http.Client{Transport: transportFunc(func(r *http.Request) (*http.Response, error) {
				expected := "/botsecret/sendPhoto"
				if kind == "animation" {
					expected = "/botsecret/sendAnimation"
				}
				if r.URL.Path != expected {
					t.Errorf("wrong method: %s", r.URL.Path)
				}
				if err := r.ParseMultipartForm(1 << 20); err != nil {
					t.Fatal(err)
				}
				if r.FormValue("chat_id") != "@rza_school" || r.FormValue("caption") != "<b>Пример</b>" || r.FormValue("parse_mode") != "HTML" {
					t.Fatal("lost channel or caption formatting")
				}
				file, _, err := r.FormFile(kind)
				if err != nil {
					t.Fatal(err)
				}
				defer file.Close()
				data, _ := io.ReadAll(file)
				if string(data) != string(asset) {
					t.Fatal("asset changed during upload")
				}
				response := `{"ok":true,"result":{"message_id":123,"photo":[{"file_id":"photo-id"}],"animation":{"file_id":"animation-id"}}}`
				return &http.Response{StatusCode: 200, Body: io.NopCloser(strings.NewReader(response))}, nil
			})}
			receipt, err := sendMedia(client, "https://api.telegram.org", "secret", "@rza_school", draft)
			if err != nil || receipt.MessageID != 123 || receipt.FileID != kind+"-id" {
				t.Fatalf("receipt=%+v err=%v", receipt, err)
			}
		})
	}
}

func TestMediaRejectsLongCaptionsBeforeNetwork(t *testing.T) {
	_, err := sendMedia(nil, "https://api.telegram.org", "secret", "@rza_school", mediaDraft{Kind: "photo", Caption: strings.Repeat("😀", 513), CaptionHTML: "long"})
	if err == nil {
		t.Fatal("must count UTF-16 characters and reject oversized captions")
	}
}
