package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestEditorialReplacementPreservesPublishedHistory(t *testing.T) {
	dir := t.TempDir()
	statePath := filepath.Join(dir, "state.json")
	for name, body := range map[string]string{"119-auto.txt": "Published source", "120-auto.txt": "Repeated old task", "121-auto.txt": "Repeated old task 2"} {
		if err := os.WriteFile(filepath.Join(dir, name), []byte(body), 0644); err != nil {
			t.Fatal(err)
		}
	}
	_, hash, _ := queueText(dir, "119-auto.txt")
	original := publication{File: "119-auto.txt", SHA256: hash, Status: "sent", MessageID: 122, Channel: "@rza_school"}
	if err := saveState(statePath, []publication{original}); err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 2; i++ {
		if err := prepareEditorialQueue(dir, statePath, 1000); err != nil {
			t.Fatal(err)
		}
	}
	if _, err := os.Stat(filepath.Join(dir, "120-auto.txt")); !os.IsNotExist(err) {
		t.Fatal("unpublished repeat retained")
	}
	state, _ := readState(statePath)
	if len(state) != 1 || state[0] != original {
		t.Fatal("published history changed")
	}
	files, _ := filepath.Glob(filepath.Join(dir, "*.txt"))
	lessons, _ := loadEditorial()
	if len(files) != 1+len(lessons) {
		t.Fatalf("want history + %d unique lessons, got %d files", len(lessons), len(files))
	}
	for _, p := range lessons {
		_, h, err := queueText(dir, p.File)
		if err != nil {
			t.Fatal(err)
		}
		state = append(state, publication{File: p.File, SHA256: h, Status: "sent"})
	}
	if err := saveState(statePath, state); err != nil {
		t.Fatal(err)
	}
	if err := prepareEditorialQueue(dir, statePath, 1000); err != nil {
		t.Fatal(err)
	}
	files, _ = filepath.Glob(filepath.Join(dir, "*.txt"))
	if len(files) != 1+len(lessons) {
		t.Fatal("exhausted syllabus was recycled")
	}
}

func TestEditorialBlocksUnresolvedOrChangedHistory(t *testing.T) {
	for _, status := range []string{"pending", "attempted", "sent"} {
		dir := t.TempDir()
		path := filepath.Join(dir, "state.json")
		os.WriteFile(filepath.Join(dir, "119-auto.txt"), []byte("source"), 0644)
		os.WriteFile(filepath.Join(dir, "120-auto.txt"), []byte("repeat"), 0644)
		saveState(path, []publication{{File: "119-auto.txt", SHA256: "wrong", Status: status}})
		if err := prepareEditorialQueue(dir, path, 1000); err == nil {
			t.Fatal("must block unresolved or changed source")
		}
		if _, err := os.Stat(filepath.Join(dir, "120-auto.txt")); err != nil {
			t.Fatal("mutated queue before checking history")
		}
	}
}

func TestEditorialCatalogRejectsDuplicateTitles(t *testing.T) {
	original := editorialJSON
	defer func() { editorialJSON = original }()
	editorialJSON = []byte(`[{"id":"x","file":"120-advanced.txt","title":"same","body":"a","nodes":["a","b","c"],"note":"n","source_ids":["N1"]},{"id":"y","file":"121-advanced.txt","title":"same","body":"b","nodes":["a","b","c"],"note":"n","source_ids":["N1"]}]`)
	if _, err := loadEditorial(); err == nil {
		t.Fatal("duplicate subject accepted")
	}
}

func TestNaturalOrderAcrossOneThousandLessons(t *testing.T) {
	files := []string{"1000-auto.txt", "999-auto.txt", "120-advanced.txt", "006-original.txt"}
	sortLessonFiles(files)
	if strings.Join(files, ",") != "006-original.txt,120-advanced.txt,999-auto.txt,1000-auto.txt" {
		t.Fatal(files)
	}
}
