package templates

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

type Store struct {
	Items map[string]string
}

func Load(dir string) (*Store, error) {
	items := map[string]string{}
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, err
	}
	for _, e := range entries {
		if e.IsDir() { continue }
		if !strings.HasSuffix(e.Name(), ".md") { continue }
		path := filepath.Join(dir, e.Name())
		data, err := os.ReadFile(path)
		if err != nil { return nil, err }
		items[e.Name()] = string(data)
	}
	return &Store{Items: items}, nil
}

func (s *Store) Pick(issueType string) string {
	if s == nil || len(s.Items) == 0 { return "" }
	issueType = strings.ToLower(issueType)
	for name, content := range s.Items {
		lname := strings.ToLower(name)
		if strings.Contains(lname, issueType) {
			return fmt.Sprintf("Template: %s\n%s", name, content)
		}
	}
	// fallback first
	for name, content := range s.Items {
		return fmt.Sprintf("Template: %s\n%s", name, content)
	}
	return ""
}
