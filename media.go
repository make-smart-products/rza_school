package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"net/textproto"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"unicode/utf16"
)

type mediaDraft struct {
	Path          string `json:"path"`
	Kind          string `json:"kind"`
	Caption       string `json:"caption"`
	CaptionHTML   string `json:"caption_html"`
	CaptionSHA256 string `json:"caption_sha256"`
	SourceSHA256  string `json:"source_sha256"`
	RenderSHA256  string `json:"render_sha256"`
	Version       int    `json:"version"`
}

type mediaReceipt struct {
	MessageID int64
	FileID    string
}

func preparePostMedia(file, sourceHash string) (mediaDraft, error) {
	python := "python3"
	if runtime.GOOS == "windows" {
		python = "python"
	}
	cmd := exec.Command(python, "media/render.py", "--file", file, "--output-dir", "media/generated")
	data, err := cmd.Output()
	if err != nil {
		return mediaDraft{}, errors.New("не удалось подготовить учебное медиа; проверьте Python, Pillow и шрифт с кириллицей")
	}
	var draft mediaDraft
	if err := json.Unmarshal(data, &draft); err != nil {
		return draft, errors.New("не удалось прочитать описание медиа")
	}
	if draft.SourceSHA256 != sourceHash {
		return draft, errors.New("исходный текст изменился при подготовке медиа")
	}
	if len(utf16.Encode([]rune(draft.Caption))) > 1024 {
		return draft, errors.New("подпись медиа превышает лимит Telegram")
	}
	return draft, nil
}

func sendMedia(client *http.Client, baseURL, token, channel string, draft mediaDraft) (mediaReceipt, error) {
	var receipt mediaReceipt
	if draft.Kind != "photo" && draft.Kind != "animation" {
		return receipt, errors.New("неподдерживаемый тип медиа")
	}
	if len(utf16.Encode([]rune(draft.Caption))) > 1024 || strings.TrimSpace(draft.CaptionHTML) == "" {
		return receipt, errors.New("некорректная подпись медиа")
	}
	asset, err := os.ReadFile(draft.Path)
	if err != nil {
		return receipt, errors.New("не удалось открыть медиафайл")
	}
	if len(asset) == 0 || len(asset) > 10<<20 {
		return receipt, errors.New("медиафайл пуст или превышает 10 МБ")
	}
	hash := sha256.Sum256(asset)
	if hex.EncodeToString(hash[:]) != draft.RenderSHA256 {
		return receipt, errors.New("медиафайл изменился после подготовки")
	}
	var body bytes.Buffer
	writer := multipart.NewWriter(&body)
	for _, field := range [][2]string{{"chat_id", channel}, {"caption", draft.CaptionHTML}, {"parse_mode", "HTML"}} {
		if err := writer.WriteField(field[0], field[1]); err != nil {
			return receipt, err
		}
	}
	header := make(textproto.MIMEHeader)
	header.Set("Content-Disposition", fmt.Sprintf(`form-data; name="%s"; filename="%s"`, draft.Kind, filepath.Base(draft.Path)))
	contentType, method := "image/png", "sendPhoto"
	if draft.Kind == "animation" {
		contentType, method = "image/gif", "sendAnimation"
	}
	header.Set("Content-Type", contentType)
	part, err := writer.CreatePart(header)
	if err != nil {
		return receipt, err
	}
	if _, err := part.Write(asset); err != nil {
		return receipt, err
	}
	if err := writer.Close(); err != nil {
		return receipt, err
	}
	response, err := client.Post(baseURL+"/bot"+token+"/"+method, writer.FormDataContentType(), &body)
	if err != nil {
		return receipt, errors.New("не удалось получить ответ Telegram; проверьте канал перед повторной отправкой медиа")
	}
	defer response.Body.Close()
	var result struct {
		OK        bool `json:"ok"`
		ErrorCode int  `json:"error_code"`
		Result    struct {
			MessageID int64 `json:"message_id"`
			Photo     []struct {
				FileID string `json:"file_id"`
			} `json:"photo"`
			Animation struct {
				FileID string `json:"file_id"`
			} `json:"animation"`
		} `json:"result"`
	}
	if err := json.NewDecoder(io.LimitReader(response.Body, 1<<20)).Decode(&result); err != nil {
		return receipt, errors.New("не удалось прочитать ответ Telegram; проверьте канал перед повторной отправкой медиа")
	}
	if response.StatusCode != http.StatusOK || !result.OK || result.Result.MessageID == 0 {
		return receipt, fmt.Errorf("Telegram отклонил медиа (HTTP %d, код %d)", response.StatusCode, result.ErrorCode)
	}
	receipt.MessageID = result.Result.MessageID
	if draft.Kind == "animation" {
		receipt.FileID = result.Result.Animation.FileID
	} else if len(result.Result.Photo) > 0 {
		receipt.FileID = result.Result.Photo[len(result.Result.Photo)-1].FileID
	}
	if receipt.FileID == "" {
		return receipt, fmt.Errorf("сообщение %d отправлено, но Telegram не подтвердил медиа; проверьте канал", receipt.MessageID)
	}
	return receipt, nil
}
