package main

import (
	_ "embed"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"unicode/utf16"
)

//go:embed content/advanced.json
var editorialJSON []byte

type editorialLesson struct {
	ID      string   `json:"id"`
	File    string   `json:"file"`
	Title   string   `json:"title"`
	Body    string   `json:"body"`
	Nodes   []string `json:"nodes"`
	Note    string   `json:"note"`
	Sources []string `json:"source_ids"`
}

func loadEditorial() ([]editorialLesson, error) {
	var lessons []editorialLesson
	if err := json.Unmarshal(editorialJSON, &lessons); err != nil {
		return nil, err
	}
	seenID, seenFile, seenTitle, seenBody := map[string]bool{}, map[string]bool{}, map[string]bool{}, map[string]bool{}
	for _, p := range lessons {
		if p.ID == "" || filepath.Base(p.File) != p.File || !strings.HasSuffix(p.File, "-advanced.txt") || p.Title == "" || len(p.Nodes) != 3 || p.Note == "" || len(p.Sources) == 0 || strings.TrimSpace(p.Body) == "" {
			return nil, errors.New("неполный редакционный материал")
		}
		if seenID[p.ID] || seenFile[p.File] || seenTitle[p.Title] || seenBody[p.Body] {
			return nil, errors.New("повтор редакционного материала")
		}
		seenID[p.ID], seenFile[p.File], seenTitle[p.Title], seenBody[p.Body] = true, true, true, true
		if len(utf16.Encode([]rune(p.Body))) > 900 {
			return nil, fmt.Errorf("слишком длинный материал %s", p.ID)
		}
	}
	if len(lessons) == 0 {
		return nil, errors.New("пустая редакционная серия")
	}
	return lessons, nil
}

// This finite syllabus replaces the numeric task cycle. Published sources are immutable.
// When the reviewed material ends, preparation stays empty instead of recycling topics.
func prepareEditorialQueue(dir, statePath string, buffer int) error {
	if buffer < 1 || buffer > 1000 {
		return errors.New("запас очереди должен быть от 1 до 1000 постов")
	}
	lessons, err := loadEditorial()
	if err != nil {
		return err
	}
	state, err := readState(statePath)
	if err != nil {
		return err
	}
	known := map[string]publication{}
	for _, p := range state {
		if p.Status != "sent" {
			return errors.New("есть незавершённая отправка; редакционная замена остановлена")
		}
		_, hash, err := queueText(dir, p.File)
		if err != nil {
			return err
		}
		if hash != p.SHA256 {
			return fmt.Errorf("изменён опубликованный исходник %s", p.File)
		}
		known[p.File] = p
	}
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}
	// Remove only unpublished legacy numeric variants; their history stays in git.
	files, err := filepath.Glob(filepath.Join(dir, "*-auto.txt"))
	if err != nil {
		return err
	}
	for _, file := range files {
		if _, sent := known[filepath.Base(file)]; !sent {
			if err := os.Remove(file); err != nil {
				return err
			}
		}
	}
	ready := 0
	for _, p := range lessons {
		if _, sent := known[p.File]; sent {
			continue
		}
		path := filepath.Join(dir, p.File)
		wanted := p.Body + "\n"
		data, err := os.ReadFile(path)
		if err != nil && !os.IsNotExist(err) {
			return err
		}
		if string(data) != wanted {
			if err := os.WriteFile(path, []byte(wanted), 0644); err != nil {
				return err
			}
		}
		ready++
	}
	fmt.Printf("Редакционная серия: %d новых разборов. Повторные задачи не генерируются.\n", ready)
	return nil
}
