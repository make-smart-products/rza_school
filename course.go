package main

import (
	"path/filepath"
	"sort"
	"strconv"
)

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
