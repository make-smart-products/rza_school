package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestQueueReservationAndRecovery(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "state.json")
	t.Setenv("TELEGRAM_CHANNEL", "@rza_school")
	for _, name := range []string{"002.txt", "001.txt"} {
		if err := os.WriteFile(filepath.Join(dir, name), []byte("Учебный пост"), 0600); err != nil {
			t.Fatal(err)
		}
	}
	if err := reserveNext(dir, path); err != nil {
		t.Fatal(err)
	}
	state, err := readState(path)
	if err != nil || len(state) != 1 || state[0].File != "001.txt" || state[0].Status != "pending" {
		t.Fatalf("state=%v err=%v", state, err)
	}
	if err := reserveNext(dir, path); err == nil {
		t.Fatal("must block while previous delivery is unresolved")
	}
	state[0].Status = "sent"
	state[0].MessageID = 42
	if err := saveState(path, state); err != nil {
		t.Fatal(err)
	}
	if err := reserveNext(dir, path); err != nil {
		t.Fatal(err)
	}
	state, err = readState(path)
	if err != nil || len(state) != 2 || state[1].File != "002.txt" {
		t.Fatalf("state=%v err=%v", state, err)
	}
}

func TestQueueBlocksChangedContentAndRepeatedAttempt(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "state.json")
	t.Setenv("TELEGRAM_CHANNEL", "@rza_school")
	t.Setenv("TELEGRAM_BOT_TOKEN", "test-token")
	post := filepath.Join(dir, "001.txt")
	if err := os.WriteFile(post, []byte("Первый текст"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := reserveNext(dir, path); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(post, []byte("Изменённый текст"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := deliverNext(dir, path); err == nil {
		t.Fatal("must reject changed content before network call")
	}
	state, err := readState(path)
	if err != nil {
		t.Fatal(err)
	}
	state[0].Status = "attempted"
	if err := saveState(path, state); err != nil {
		t.Fatal(err)
	}
	if err := deliverNext(dir, path); err == nil {
		t.Fatal("must reject a repeated attempt")
	}
}

func TestQueueRejectsCorruptStateAndPathTraversal(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "state.json")
	if err := os.WriteFile(path, []byte("invalid JSON"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := reserveNext(dir, path); err == nil {
		t.Fatal("must not reset corrupt state")
	}
	if _, _, err := queueText(dir, "../other.txt"); err == nil {
		t.Fatal("must reject path traversal")
	}
}
