package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"regexp"
	"slices"
	"strings"
	"time"

	"golang.org/x/net/html"
)

const (
	urlFile         = "urls.txt"
	validUrlsFile   = "valid_urls.txt"
	resultFile      = "results.json"
	validResultFile = "valid_results.json"
	attempts        = 5
	timeout         = 10 * time.Second
)

func main() {

	/*if err := createValidUrls(urlFile); err != nil {
		fmt.Println("Ошибка:", err)
		return
	}*/

	res, err := processAll(validUrlsFile, attempts, timeout)
	if err != nil {
		fmt.Println("Ошибка:", err)
		return
	}

	if err := saveResultsToFile(res, validResultFile); err != nil {
		fmt.Println("Ошибка:", err)
		return
	}

	printResults(res)

}

// Функция для создания файла с валидными URL
func createValidUrls(fileName string) error {
	results, err := loadResults(fileName)
	if err != nil {
		return err
	}

	validUrl := []string{}

	for _, r := range results {
		if r.Error != "" || len(r.Text) == 0 {
			continue
		}

		validUrl = append(validUrl, r.URL)
	}

	return saveValidUrls(validUrl, validUrlsFile)
}

// Функция для загрузки HTML страницы
func fetchHTML(url string, attempts int, timeout time.Duration) (string, error) {
	var lastError error
	for i := 0; i < attempts; i++ {
		client := http.Client{
			Timeout: timeout,
		}

		resp, err := client.Get(url)
		if err != nil {
			lastError = err
			time.Sleep(1 * time.Second) // пауза между попытками
			continue
		}
		defer resp.Body.Close()

		// Проверяем статус ответа
		if resp.StatusCode != http.StatusOK {
			// Если код 404 или другой, возвращаем ошибку
			return "", fmt.Errorf("получен статус %d: %s", resp.StatusCode, http.StatusText(resp.StatusCode))
		}

		body, err := io.ReadAll(resp.Body)
		if err != nil {
			return "", err
		}

		return string(body), nil
	}
	return "", lastError
}

// Определяем структуру Result
type Result struct {
	URL    string   `json:"URL"`    // URL страницы
	Error  string   `json:"error"`  // Ошибка при загрузке страницы
	Title  string   `json:"title"`  // содержимое тега <title>
	H1     []string `json:"h1"`     // содержимое всех тегов <h1>
	Text   []Item   `json:"text"`   // содержимое всех остальных тегов
	Images []Image  `json:"images"` // URL и альтернативный текст изображений
}

// AddOrUpdateItem Метод для добавления или обновления элемента в Result.Text
func (r *Result) AddOrUpdateItem(tag, content string) {
	// Если предыдущий элемент имеет тот же Tag, то текст добавляется к нему
	if len(r.Text) > 0 && r.Text[len(r.Text)-1].Tag == tag {
		r.Text[len(r.Text)-1].Content += " " + content
		// Убираем лишние пробелы
		r.Text[len(r.Text)-1].Content = strings.TrimSpace(r.Text[len(r.Text)-1].Content)
	} else {
		// Иначе добавляем новый элемент
		r.Text = append(
			r.Text, Item{
				Tag:     tag,
				Content: content,
			},
		)
	}
}

type Item struct {
	Tag     string `json:"tag"`     // тэг элемента
	Content string `json:"content"` // текстовое содержимое
}

type Image struct {
	Src string `json:"src"` // URL изображения
	Alt string `json:"alt"` // альтернативный текст
}

// Рекурсивная функция для обхода узлов и заполнения объекта Result
func extractObject(n *html.Node, result *Result) {
	ignoredTags := []string{
		"script",
		"style",
		"noscript",
		"link",
		"button",
		"form",
		"input",
		"label",
		"textarea",
		"s", // Элемент перечеркнутый (устарел)
	}

	// Игнорируем теги <script> и <style> и их содержимое
	if n.Type == html.ElementNode && slices.Contains(ignoredTags, n.Data) {
		return
	}

	// Обрабатываем тег <meta>
	if n.Type == html.ElementNode && n.Data == "meta" {
		var name, content string

		// Ищем атрибуты name и content
		for _, attr := range n.Attr {
			if attr.Key == "name" && strings.Contains(attr.Val, "description") {
				name = attr.Val
			}
			if attr.Key == "content" {
				content = cleanText(attr.Val)
			}
		}

		// Если найдены оба атрибута, добавляем новый Item
		if name != "" && content != "" {
			metaTag := "meta." + name
			result.AddOrUpdateItem(metaTag, content)
		}
	}

	// Обрабатываем тег <img> для добавления изображения в Result
	if n.Type == html.ElementNode && n.Data == "img" {
		var src, alt string
		for _, attr := range n.Attr {
			if attr.Key == "src" {
				if len(attr.Val) > 200 {
					src = "..."
				} else {
					src = attr.Val
				}
			}
			if attr.Key == "alt" {
				alt = attr.Val
			}
		}
		// Если атрибут src найден, добавляем изображение в список Images
		if src != "" && alt != "" {
			result.Images = append(result.Images, Image{Src: src, Alt: alt})
		}
	}

	if n.Type == html.TextNode {
		cleanedText := cleanText(n.Data)

		if cleanedText != "" && n.Parent != nil {
			// Заполняем объект Result в зависимости от тега
			switch n.Parent.Data {
			case "title":
				result.Title = cleanedText
			case "h1":
				result.H1 = append(result.H1, cleanedText)
			default:
				// Используем метод Result для добавления или обновления элемента
				result.AddOrUpdateItem(n.Parent.Data, cleanedText)
			}
		}
	}

	for c := n.FirstChild; c != nil; c = c.NextSibling {
		extractObject(c, result)
	}
}

// Функция для очистки текста: удаление лишних пробелов, переводов строк и т.д.
func cleanText(text string) string {
	// Убираем переводы строк и заменяем их на пробелы
	cleanedText := strings.ReplaceAll(text, "\n", " ")
	cleanedText = strings.ReplaceAll(cleanedText, "\r", " ")

	// Заменяем неразрывные пробелы (NBSP) на обычные пробелы
	cleanedText = strings.ReplaceAll(cleanedText, "\u00A0", " ")

	// Заменяем Unicode символ `\u0026` на символ `&`
	cleanedText = strings.ReplaceAll(cleanedText, "\u0026", "&")
	// Убираем повторяющиеся пробелы
	cleanedText = strings.Join(strings.Fields(cleanedText), " ")

	// Удаляем все слэши `\`
	cleanedText = strings.ReplaceAll(cleanedText, "\\", "")
	cleanedText = strings.ReplaceAll(cleanedText, "/", "")
	cleanedText = strings.ReplaceAll(cleanedText, "|", "")

	// Проверяем, есть ли в строке значимые символы (буквы или цифры)
	if !containsSignificantChars(cleanedText) {
		// Если строка не содержит значимых символов, очищаем её
		return ""
	}

	return strings.TrimSpace(cleanedText)
}

// Функция для проверки наличия значимых символов (буквы и цифры)
func containsSignificantChars(text string) bool {
	// Регулярное выражение для проверки наличия букв или цифр в любой локали
	re := regexp.MustCompile(`[\p{L}\p{N}]`)
	return re.MatchString(text)
}

// Функция для удаления тегов <span> и <strong> с помощью регулярных выражений
func removeTags(htmlContent string) string {
	tags := []string{
		"span",
		"strong",
		"em",
		"aside",
		"small",
		"b",
		"i",
		"mark",
		"abbr",
		"ins",
		"sub",
		"sup",
		"q",
		"a",
	}

	for _, tag := range tags {
		// Обрабатываем открывающие теги, с точным совпадением названия тега
		openTagPattern := `(?i)<` + tag + `(\s[^>]*)?>`
		reOpenTag := regexp.MustCompile(openTagPattern)
		htmlContent = reOpenTag.ReplaceAllString(htmlContent, "")

		// Обрабатываем закрывающие теги
		closeTagPattern := `(?i)</` + tag + `>`
		htmlContent = regexp.MustCompile(closeTagPattern).ReplaceAllString(htmlContent, "")
	}

	return htmlContent
}

// Функция для обработки URL
func process(url string, attempts int, timeout time.Duration) Result {
	result := Result{URL: url}

	htmlContent, err := fetchHTML(url, attempts, timeout)
	if err != nil {
		result.Error = err.Error()
		return result
	}

	// Удаляем теги <span> и <strong> из дерева DOM
	htmlContent = removeTags(htmlContent)

	doc, err := html.Parse(strings.NewReader(htmlContent))
	if err != nil {
		result.Error = err.Error()
		return result
	}

	// Извлекаем объект с содержимым
	extractObject(doc, &result)

	return result
}

// Функция для запуска горутин с обработкой URL
func fetchData(urls []string, attempts int, timeout time.Duration) []Result {
	results := make([]Result, len(urls))
	resultChannel := make(chan Result)

	// Запуск горутин для каждого URL
	for _, url := range urls {
		go func(u string) {
			resultChannel <- process(u, attempts, timeout)
		}(url)
	}

	// Сбор результатов
	for i := 0; i < len(urls); i++ {
		results[i] = <-resultChannel
	}

	return results
}

func printResults(results []Result) {
	errorsCount := 0
	emptyCount := 0
	readyCount := 0

	for _, r := range results {
		if r.Error != "" {
			errorsCount++
			continue
		}
		if len(r.Text) == 0 {
			emptyCount++

			continue
		}

		readyCount++
	}

	fmt.Printf("Всего URL: %d\n", len(results))
	fmt.Println("Готовых:", readyCount)
	fmt.Printf("Ошибок: %d\n", errorsCount)
	fmt.Printf("Без текста: %d\n", emptyCount)
}

func saveValidUrls(urls []string, fileName string) error {
	file, err := os.Create(fileName)
	if err != nil {
		return err
	}
	defer file.Close()

	writer := bufio.NewWriter(file)
	for _, url := range urls {
		_, err := writer.WriteString(url + "\n")
		if err != nil {
			return err
		}
	}

	return writer.Flush()
}

func loadResults(fileName string) ([]Result, error) {
	file, err := os.Open(fileName)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var results []Result
	if err := json.NewDecoder(file).Decode(&results); err != nil {
		return results, err
	}

	return results, nil
}

func processAll(fileName string, attempts int, timeout time.Duration) ([]Result, error) {
	urls, err := loadFile(fileName, -1)
	if err != nil {
		return nil, err
	}

	results := fetchData(urls, attempts, timeout)

	return results, nil
}

// Функция для сохранения слайса Result в JSON файл
func saveResultsToFile(results []Result, fileName string) error {
	// Открываем файл для записи (создаём новый или перезаписываем существующий)
	file, err := os.Create(fileName)
	if err != nil {
		return fmt.Errorf("не удалось создать файл: %w", err)
	}
	defer file.Close()

	// Преобразуем слайс Result в JSON
	jsonData, err := json.MarshalIndent(results, "", "  ") // Форматируем с отступами
	if err != nil {
		return fmt.Errorf("не удалось сериализовать данные в JSON: %w", err)
	}

	// Записываем JSON в файл
	_, err = file.Write(jsonData)
	if err != nil {
		return fmt.Errorf("не удалось записать данные в файл: %w", err)
	}

	return nil
}

// Функция для чтения текстового файла и получения списка URL
func loadFile(fileName string, count int) ([]string, error) {
	file, err := os.Open(fileName)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var urls []string
	scanner := bufio.NewScanner(file)

	// Читаем файл построчно и добавляем непустые строки в список URL
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text()) // Удаляем пробелы и лишние символы
		if line != "" {                           // Пропускаем пустые строки
			urls = append(urls, line)
			if len(urls) == count { // Останавливаем чтение, если достигнуто нужное количество строк
				break
			}
		}
	}

	// Проверяем наличие ошибок при чтении файла
	if err := scanner.Err(); err != nil {
		return nil, err
	}

	return urls, nil
}

func first(url string) {
	// url := "https://www.factorybuys.com.au/products/euro-top-mattress-king" // URL страницы для парсинга
	htmlContent, err := fetchHTML(url, 1, 10*time.Second) // Загружаем HTML страницу
	if err != nil {
		fmt.Println("Ошибка:", err)
		return
	}

	// Пример: извлекаем все текстовые узлы
	// text := extractText(doc)
	// fmt.Println("Текст страницы:")
	// fmt.Println(text)

	// Инициализируем map для хранения текста по тегам
	/*tagTextMap := make(map[string][]string)
	extractTextByTag(doc, tagTextMap)
	fmt.Println("Текст внутри тегов:")
	for tag, texts := range tagTextMap {
		fmt.Printf("<%s>: %v\n", tag, texts)
	}*/

	// Инициализируем объект Result для хранения текста
	result := &Result{}

	// Удаляем теги <span> и <strong> из дерева DOM
	htmlContent = removeTags(htmlContent)

	// Парсим очищенный HTML (преобразуем строку в io.Reader)
	doc, err := html.Parse(strings.NewReader(htmlContent))
	if err != nil {
		fmt.Println("Ошибка парсинга HTML:", err)
		return
	}

	// Извлекаем объект с содержимым
	extractObject(doc, result)

	// Выводим результат
	fmt.Println("Содержимое объекта Result:")
	fmt.Printf("Title: %s\n", result.Title)
	fmt.Printf("H1: %v\n", result.H1)

	for _, item := range result.Text {
		fmt.Printf("Tag: %s.\t", item.Tag)
		fmt.Printf("Content: %s\n", item.Content)
	}

	for _, im := range result.Images {
		fmt.Printf("Src: %s\n", im.Src)
		fmt.Printf("Alt: %s\n", im.Alt)
	}

	// fmt.Printf("Text: %v\n", result.Text)
	// fmt.Printf("Text: %d\n", len(result.Text))
}
