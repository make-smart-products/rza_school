package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
	"unicode/utf8"
)

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run() error {
	if err := loadEnv(".env"); err != nil {
		return err
	}
	file := flag.String("file", "posts/001-welcome.txt", "Файл публикации UTF-8")
	send := flag.Bool("send", false, "Опубликовать в Telegram")
	reserve := flag.Bool("reserve", false, "Зарезервировать следующий пост очереди")
	deliver := flag.Bool("deliver", false, "Отправить зарезервированный пост")
	queue := flag.String("queue", "posts/lessons", "Каталог очереди")
	state := flag.String("state", ".publisher-state.json", "Файл состояния очереди")
	flag.Parse()
	if *reserve && *deliver {
		return errors.New("выберите только один режим: -reserve или -deliver")
	}
	if *reserve {
		return reserveNext(*queue, *state)
	}
	if *deliver {
		return deliverNext(*queue, *state)
	}
	data, err := os.ReadFile(*file)
	if err != nil {
		return fmt.Errorf("не удалось прочитать пост: %w", err)
	}
	body := strings.TrimSpace(strings.TrimPrefix(string(data), "\uFEFF"))
	if !utf8.ValidString(body) || body == "" || utf8.RuneCountInString(body) > 4096 {
		return errors.New("нужен текст UTF-8 длиной от 1 до 4096 символов")
	}
	channel := strings.TrimSpace(os.Getenv("TELEGRAM_CHANNEL"))
	if channel == "" {
		channel = "@rza_school"
	}
	if !*send {
		fmt.Printf("Предпросмотр для %s:\n\n%s\n\nДля публикации добавьте -send.\n", channel, body)
		return nil
	}
	token := strings.TrimSpace(os.Getenv("TELEGRAM_BOT_TOKEN"))
	if token == "" {
		return errors.New("задайте TELEGRAM_BOT_TOKEN локально или запустите publish.ps1")
	}
	client := &http.Client{Timeout: 30 * time.Second, CheckRedirect: func(req *http.Request, via []*http.Request) error { return http.ErrUseLastResponse }}
	id, err := sendMessage(client, "https://api.telegram.org", token, channel, body)
	if err != nil {
		return err
	}
	fmt.Printf("Опубликовано в %s. ID сообщения: %d\n", channel, id)
	return nil
}

func sendMessage(client *http.Client, baseURL, token, channel, body string) (int64, error) {
	payload, err := json.Marshal(map[string]string{"chat_id": channel, "text": body})
	if err != nil {
		return 0, err
	}
	resp, err := client.Post(baseURL+"/bot"+token+"/sendMessage", "application/json", bytes.NewReader(payload))
	if err != nil {
		// HTTP errors contain the request URL, which includes the bot token.
		return 0, errors.New("не удалось получить ответ Telegram; проверьте канал перед повторной отправкой, чтобы избежать дубля")
	}
	defer resp.Body.Close()
	var result struct {
		OK        bool `json:"ok"`
		ErrorCode int  `json:"error_code"`
		Result    struct {
			MessageID int64 `json:"message_id"`
		} `json:"result"`
	}
	if err := json.NewDecoder(io.LimitReader(resp.Body, 1<<20)).Decode(&result); err != nil {
		return 0, errors.New("не удалось прочитать ответ Telegram; проверьте канал перед повторной отправкой")
	}
	if resp.StatusCode != http.StatusOK || !result.OK || result.Result.MessageID == 0 {
		return 0, fmt.Errorf("Telegram отклонил публикацию (HTTP %d, код %d); проверьте токен, адрес канала и право публикации", resp.StatusCode, result.ErrorCode)
	}
	return result.Result.MessageID, nil
}
