package api

import (
	"testing"
)

func TestExtractKnowledgeVersion(t *testing.T) {
	tests := []struct {
		filename    string
		wantVersion string
		wantOK      bool
	}{
		{"matrixorigin_matrixone_knowledge_20260225.md", "20260225", true},
		{"matrixorigin_matrixflow_knowledge_20260101.md", "20260101", true},
		{"matrixorigin_matrixone_knowledge_latest.md", "", false},
		{"random_file.md", "", false},
		{"knowledge_20260225.json", "", false},
		{"org_repo_knowledge_20261231.md", "20261231", true},
	}

	for _, tt := range tests {
		t.Run(tt.filename, func(t *testing.T) {
			version, ok := extractKnowledgeVersion(tt.filename)
			if ok != tt.wantOK {
				t.Errorf("extractKnowledgeVersion(%q) ok = %v, want %v", tt.filename, ok, tt.wantOK)
			}
			if version != tt.wantVersion {
				t.Errorf("extractKnowledgeVersion(%q) version = %q, want %q", tt.filename, version, tt.wantVersion)
			}
		})
	}
}

func TestGeneratedAtFromVersion(t *testing.T) {
	tests := []struct {
		version string
		want    string
	}{
		{"20260225", "2026-02-25T00:00:00Z"},
		{"20260101", "2026-01-01T00:00:00Z"},
		{"invalid", ""},
		{"", ""},
		{"2026022", ""},
	}

	for _, tt := range tests {
		t.Run(tt.version, func(t *testing.T) {
			got := generatedAtFromVersion(tt.version)
			if got != tt.want {
				t.Errorf("generatedAtFromVersion(%q) = %q, want %q", tt.version, got, tt.want)
			}
		})
	}
}
