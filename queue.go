package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
	"unicode/utf8"
)

type publication struct {
	File      string `json:"file"`
	SHA256    string `json:"sha256"`
	Status    string `json:"status"`
	MessageID int64  `json:"message_id,omitempty"`
	Channel   string `json:"channel"`
}

func readState(path string) ([]publication, error) {
	data, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return []publication{}, nil
	}
	if err != nil {
		return nil, err
	}
	var state []publication
	if err := json.Unmarshal(data, &state); err != nil {
		return nil, errors.New("повреждён файл состояния очереди; отправка остановлена")
	}
	return state, nil
}

func saveState(path string, state []publication) error {
	data, err := json.MarshalIndent(state, "", "  ")
	if err != nil {
		return err
	}
	if err := os.WriteFile(path+".tmp", append(data, '\n'), 0600); err != nil {
		return err
	}
	return os.Rename(path+".tmp", path)
}

func queueText(dir, name string) (string, string, error) {
	if filepath.Base(name) != name || !strings.HasSuffix(name, ".txt") {
		return "", "", errors.New("неверное имя файла поста")
	}
	data, err := os.ReadFile(filepath.Join(dir, name))
	if err != nil {
		return "", "", err
	}
	body := strings.TrimSpace(strings.TrimPrefix(string(data), "\uFEFF"))
	if !utf8.ValidString(body) || len(body) == 0 || utf8.RuneCountInString(body) > 4096 {
		return "", "", errors.New("некорректный текст поста")
	}
	hash := sha256.Sum256([]byte(body))
	return body, hex.EncodeToString(hash[:]), nil
}

func channelName() string {
	if value := strings.TrimSpace(os.Getenv("TELEGRAM_CHANNEL")); value != "" {
		return value
	}
	return "@rza_school"
}

func reserveNext(dir, statePath string) error {
	state, err := readState(statePath)
	if err != nil {
		return err
	}
	known := map[string]bool{}
	for _, post := range state {
		if post.Status != "sent" {
			return errors.New("есть незавершённая отправка; проверьте канал и файл состояния вручную перед продолжением")
		}
		known[post.File] = true
	}
	files, err := filepath.Glob(filepath.Join(dir, "*.txt"))
	if err != nil {
		return err
	}
	sort.Strings(files)
	for _, file := range files {
		name := filepath.Base(file)
		if known[name] {
			continue
		}
		_, hash, err := queueText(dir, name)
		if err != nil {
			return err
		}
		state = append(state, publication{File: name, SHA256: hash, Status: "pending", Channel: channelName()})
		if err := saveState(statePath, state); err != nil {
			return err
		}
		fmt.Println("Зарезервирован пост:", name)
		return nil
	}
	fmt.Println("Очередь пуста. Добавьте новые материалы в posts/lessons.")
	return nil
}

func deliverNext(dir, statePath string) error {
	state, err := readState(statePath)
	if err != nil {
		return err
	}
	token := strings.TrimSpace(os.Getenv("TELEGRAM_BOT_TOKEN"))
	if token == "" {
		return errors.New("не задан TELEGRAM_BOT_TOKEN")
	}
	for i := range state {
		post := &state[i]
		if post.Status == "sent" {
			continue
		}
		if post.Status != "pending" {
			return errors.New("отправка уже запускалась; проверьте канал вручную")
		}
		if post.Channel != channelName() {
			return errors.New("канал изменился после резервирования")
		}
		body, hash, err := queueText(dir, post.File)
		if err != nil {
			return err
		}
		if hash != post.SHA256 {
			return errors.New("пост изменился после резервирования")
		}
		// Persist an attempt before the network call. Ambiguous failures require manual review.
		post.Status = "attempted"
		if err := saveState(statePath, state); err != nil {
			return err
		}
		client := &http.Client{Timeout: 30 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}
		id, err := sendMessage(client, "https://api.telegram.org", token, post.Channel, body)
		if err != nil {
			return err
		}
		post.Status, post.MessageID = "sent", id
		if err := saveState(statePath, state); err != nil {
			return fmt.Errorf("сообщение %d отправлено, но состояние не сохранено: %w", id, err)
		}
		fmt.Printf("Опубликован %s, ID: %d\n", post.File, id)
		return nil
	}
	fmt.Println("Нет зарезервированных постов.")
	return nil
}
