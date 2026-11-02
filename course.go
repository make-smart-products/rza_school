package main

import (
	_ "embed"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"unicode/utf8"
)

//go:embed content/course.json
var courseJSON []byte

type courseTopic struct {
	Title       string `json:"title"`
	Explanation string `json:"explanation"`
	Question    string `json:"question"`
	Answer      string `json:"answer"`
	Case        string `json:"case"`
	Resolution  string `json:"resolution"`
}

func lessonNumber(path string) int {
	name := filepath.Base(path)
	end := 0
	for end < len(name) && name[end] >= '0' && name[end] <= '9' {
		end++
	}
	if end == 0 {
		return 0
	}
	n, _ := strconv.Atoi(name[:end])
	return n
}

func sortLessonFiles(files []string) {
	sort.Slice(files, func(i, j int) bool {
		a, b := lessonNumber(files[i]), lessonNumber(files[j])
		if a != b {
			return a < b
		}
		return files[i] < files[j]
	})
}

func loadCourse() ([]courseTopic, error) {
	var topics []courseTopic
	if err := json.Unmarshal(courseJSON, &topics); err != nil {
		return nil, err
	}
	if len(topics) == 0 {
		return nil, errors.New("пустой учебный курс")
	}
	for _, topic := range topics {
		if topic.Title == "" || topic.Explanation == "" || topic.Question == "" || topic.Answer == "" || topic.Case == "" || topic.Resolution == "" {
			return nil, errors.New("неполная тема учебного курса")
		}
	}
	return topics, nil
}

func freeLesson(index int, topics []courseTopic) (string, error) {
	if index < 0 || len(topics) == 0 {
		return "", errors.New("неверный номер урока")
	}
	var text string
	if index < len(topics)*3 {
		topic := topics[index%len(topics)]
		switch index / len(topics) {
		case 0:
			text = topic.Title + "\n\n" + topic.Explanation + "\n\nПроверьте себя: " + topic.Question + "\n\nОтвет: " + topic.Answer
		case 1:
			text = "Разбор ситуации: " + topic.Title + "\n\n" + topic.Case + "\n\nРазбор: " + topic.Resolution
		case 2:
			text = "Самопроверка: " + topic.Title + "\n\n" + topic.Question + "\n\nСначала сформулируйте ответ своими словами.\n\nОтвет и пояснение: " + topic.Answer + "\n\nСвязь с практикой: " + topic.Resolution
		}
	} else {
		text = practiceLesson(index - len(topics)*3)
	}
	text += "\n\nУчебный материал; расчётные примеры не являются уставками для действующего оборудования.\n\n#РЗА #ШколаРЗА"
	if !utf8.ValidString(text) || utf8.RuneCountInString(text) > 4096 {
		return "", errors.New("сформированный урок превышает размер Telegram")
	}
	return text, nil
}

// Each task uses a monotonically increasing parameter, so old tasks are not recycled.
// Fixed-point integer arithmetic keeps the answer independent of floating-point rounding.
func practiceLesson(index int) string {
	n := int64(index/5 + 1)
	switch index % 5 {
	case 0:
		k, secondaryTenths := int64(80), n+5
		return fmt.Sprintf("Учебная задача: первичный и вторичный ток\n\nВ идеализированной модели трансформатора тока коэффициент K = I₁/I₂ = %d. Вторичный ток I₂ = %d,%d А. Найдите первичный ток. Погрешность и насыщение исключены из модели.\n\nРешение: I₁ = K × I₂ = %d × %d,%d = %d А.\n\nКоэффициент здесь задан условием задачи и не выбирается для реальной установки.", k, secondaryTenths/10, secondaryTenths%10, k, secondaryTenths/10, secondaryTenths%10, k*secondaryTenths/10)
	case 1:
		delay, breaker, circuit := 100+n, int64(45), int64(5)
		return fmt.Sprintf("Учебная задача: полное время отключения\n\nВ условной последовательной модели время действия защиты — %d мс, время передачи команды — %d мс, время отключения выключателя — %d мс. Найдите суммарное время. Перекрытия процессов в этой модели нет.\n\nРешение: %d + %d + %d = %d мс.\n\nЭтот пример показывает отличие времени защиты от полного времени отключения; значения не являются рекомендацией по выбору выдержек.", delay, circuit, breaker, delay, circuit, breaker, delay+circuit+breaker)
	case 2:
		start, gap := int64(1000), 20+n
		return fmt.Sprintf("Учебная задача: интервал между событиями\n\nВ одном журнале, на одной шкале времени, пуск зарегистрирован в момент %d мс, а команда отключения — в момент %d мс. Каков интервал между отметками?\n\nРешение: Δt = %d − %d = %d мс.\n\nПо двум отметкам можно вычислить интервал, но нельзя установить причину задержки. Для сравнения разных устройств нужно учитывать синхронизацию и точность регистрации.", start, start+gap, start+gap, start, gap)
	case 3:
		in, out := int64(1000)+n, int64(1000)
		return fmt.Sprintf("Учебная задача: баланс токов\n\nВ условной модели два тока уже приведены к одной стороне и одной базе. Они синфазны, направления учтены так, что в нормальном режиме значения вычитаются. Iвх = %d мА, Iвых = %d мА. Найдите модуль разности.\n\nРешение: |Iвх − Iвых| = |%d − %d| = %d мА.\n\nЭто арифметическая модель баланса. Реальный алгоритм дифференциальной защиты дополнительно учитывает фазовые соотношения, торможение и особенности измерений.", in, out, in, out, n)
	default:
		milliseconds := int64(500) + n
		return fmt.Sprintf("Учебная задача: единицы времени\n\nВ журнале указан интервал %d мс. Представьте его в секундах.\n\nРешение: 1 с = 1000 мс. Поэтому %d мс = %d,%03d с.\n\nПри сравнении записей и расчётов сначала приведите значения к одинаковым единицам. Ошибка между секундами и миллисекундами меняет численное значение в 1000 раз.", milliseconds, milliseconds, milliseconds/1000, milliseconds%1000)
	}
}

func prepareQueue(dir, statePath string, buffer int) error {
	if buffer < 1 || buffer > 24 {
		return errors.New("запас очереди должен быть от 1 до 24 постов")
	}
	state, err := readState(statePath)
	if err != nil {
		return err
	}
	known := map[string]bool{}
	maxNumber, generated := 0, 0
	for _, post := range state {
		if post.Status != "sent" {
			return errors.New("есть незавершённая отправка; пополнение остановлено до проверки канала")
		}
		known[post.File] = true
		if n := lessonNumber(post.File); n > maxNumber {
			maxNumber = n
		}
	}
	files, err := filepath.Glob(filepath.Join(dir, "*.txt"))
	if err != nil {
		return err
	}
	remaining := 0
	for _, path := range files {
		name := filepath.Base(path)
		if _, _, err := queueText(dir, name); err != nil {
			return err
		}
		if n := lessonNumber(name); n > maxNumber {
			maxNumber = n
		}
		if strings.HasSuffix(name, "-auto.txt") {
			generated++
		}
		if !known[name] {
			remaining++
		}
	}
	// Missing archived source files can otherwise reset the course and repeat lessons.
	for name := range known {
		if _, err := os.Stat(filepath.Join(dir, name)); err != nil {
			return fmt.Errorf("не найден исходный опубликованный пост %s; восстановите файл", name)
		}
	}
	topics, err := loadCourse()
	if err != nil {
		return err
	}
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}
	for remaining < buffer {
		body, err := freeLesson(generated, topics)
		if err != nil {
			return err
		}
		maxNumber++
		name := fmt.Sprintf("%03d-auto.txt", maxNumber)
		f, err := os.OpenFile(filepath.Join(dir, name), os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0644)
		if err != nil {
			return err
		}
		_, writeErr := f.WriteString(body + "\n")
		closeErr := f.Close()
		if writeErr != nil {
			return writeErr
		}
		if closeErr != nil {
			return closeErr
		}
		fmt.Println("Подготовлен урок:", name)
		remaining++
		generated++
	}
	fmt.Printf("Готово к публикации: %d постов. Платные API не используются.\n", remaining)
	return nil
}
