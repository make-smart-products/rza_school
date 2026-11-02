package main

import (
	"crypto/sha256"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"unicode/utf8"
)

func TestFreeCourseAndPracticeRemainValidAndDistinct(t *testing.T) {
	topics, err := loadCourse()
	if err != nil {
		t.Fatal(err)
	}
	seen := map[[32]byte]bool{}
	for i := 0; i < len(topics)*3+10000; i++ {
		text, err := freeLesson(i, topics)
		if err != nil || !utf8.ValidString(text) || utf8.RuneCountInString(text) > 4096 {
			t.Fatalf("lesson %d: %v", i, err)
		}
		hash := sha256.Sum256([]byte(text))
		if seen[hash] {
			t.Fatalf("duplicate lesson %d", i)
		}
		seen[hash] = true
	}
}

func TestPracticeAnswersAndUnits(t *testing.T) {
	for _, tc := range []struct {
		index    int
		expected string
	}{
		{0, "80 × 0,6 = 48 А"},
		{1, "101 + 5 + 45 = 151 мс"},
		{2, "1021 − 1000 = 21 мс"},
		{3, "|1001 − 1000| = 1 мА"},
		{4, "501 мс = 0,501 с"},
		{2499, "1000 мс = 1,000 с"},
	} {
		if text := practiceLesson(tc.index); !strings.Contains(text, tc.expected) {
			t.Fatalf("task %d: expected %q in %q", tc.index, tc.expected, text)
		}
	}
}

func TestPrepareQueueTopUpAndIdempotency(t *testing.T) {
	dir := t.TempDir()
	statePath := filepath.Join(dir, "state.json")
	t.Setenv("TELEGRAM_CHANNEL", "@rza_school")
	if err := os.WriteFile(filepath.Join(dir, "006-original.txt"), []byte("Существующий урок"), 0644); err != nil {
		t.Fatal(err)
	}
	if err := prepareQueue(dir, statePath, 3); err != nil {
		t.Fatal(err)
	}
	files, _ := filepath.Glob(filepath.Join(dir, "*.txt"))
	if len(files) != 3 {
		t.Fatalf("expected 3 lessons, got %d", len(files))
	}
	if err := prepareQueue(dir, statePath, 3); err != nil {
		t.Fatal(err)
	}
	files, _ = filepath.Glob(filepath.Join(dir, "*.txt"))
	if len(files) != 3 {
		t.Fatal("prepare must not append while the buffer is full")
	}
	if err := reserveNext(dir, statePath); err != nil {
		t.Fatal(err)
	}
	if err := prepareQueue(dir, statePath, 3); err == nil {
		t.Fatal("must block unresolved delivery")
	}
	state, err := readState(statePath)
	if err != nil {
		t.Fatal(err)
	}
	if state[0].File != "006-original.txt" {
		t.Fatal("existing lesson must be published first")
	}
	state[0].Status = "sent"
	if err := saveState(statePath, state); err != nil {
		t.Fatal(err)
	}
	if err := prepareQueue(dir, statePath, 3); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(filepath.Join(dir, "009-auto.txt")); err != nil {
		t.Fatal("new lesson was not generated")
	}
	data, _ := os.ReadFile(filepath.Join(dir, "009-auto.txt"))
	if !strings.Contains(string(data), "Полярность измерений") {
		t.Fatal("course must continue from its third topic")
	}
}

func TestNaturalOrderAcrossOneThousandLessons(t *testing.T) {
	files := []string{"1000-auto.txt", "999-auto.txt", "007-auto.txt", "006-original.txt"}
	sortLessonFiles(files)
	if strings.Join(files, ",") != "006-original.txt,007-auto.txt,999-auto.txt,1000-auto.txt" {
		t.Fatalf("wrong order: %v", files)
	}
}

func TestPrepareRejectsMissingPublishedSource(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "state.json")
	if err := saveState(path, []publication{{File: "001-auto.txt", Status: "sent"}}); err != nil {
		t.Fatal(err)
	}
	if err := prepareQueue(dir, path, 6); err == nil {
		t.Fatal("must not restart course after deleting its history")
	}
}
