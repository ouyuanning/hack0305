package api

import (
	"testing"
)

func TestReportTypeFromFilename(t *testing.T) {
	tests := []struct {
		filename string
		want     string
	}{
		{"daily_report_matrixorigin_matrixone_20260225.json", "daily"},
		{"progress_report_matrixorigin_matrixone_20260225.json", "progress"},
		{"comprehensive_report_20260223.json", "comprehensive"},
		{"extensible_analysis_20260225.json", "extensible"},
		{"shared_features_20260223.json", "shared"},
		{"risk_analysis_20260223.json", "risk"},
		{"customer_acme_report_20260223.json", "customer"},
		{"random_file.json", "unknown"},
		{"daily_report_matrixorigin_matrixflow_20260224.json", "daily"},
	}

	for _, tt := range tests {
		t.Run(tt.filename, func(t *testing.T) {
			got := reportTypeFromFilename(tt.filename)
			if got != tt.want {
				t.Errorf("reportTypeFromFilename(%q) = %q, want %q", tt.filename, got, tt.want)
			}
		})
	}
}

func TestGeneratedAtFromJSON(t *testing.T) {
	tests := []struct {
		name string
		data string
		want string
	}{
		{
			name: "valid generated_at",
			data: `{"generated_at": "2026-02-25T14:49:52.641823", "repo": "matrixorigin/matrixone"}`,
			want: "2026-02-25T14:49:52.641823",
		},
		{
			name: "missing generated_at",
			data: `{"repo": "matrixorigin/matrixone"}`,
			want: "",
		},
		{
			name: "invalid json",
			data: `not json`,
			want: "",
		},
		{
			name: "empty generated_at",
			data: `{"generated_at": ""}`,
			want: "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := generatedAtFromJSON([]byte(tt.data))
			if got != tt.want {
				t.Errorf("generatedAtFromJSON() = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestRepoFromReportJSON(t *testing.T) {
	tests := []struct {
		name  string
		data  string
		owner string
		repo  string
		want  string
	}{
		{
			name:  "repo field present",
			data:  `{"repo": "matrixorigin/matrixone", "generated_at": "2026-02-25"}`,
			owner: "matrixorigin",
			repo:  "matrixone",
			want:  "matrixorigin/matrixone",
		},
		{
			name:  "repo field missing",
			data:  `{"generated_at": "2026-02-25"}`,
			owner: "matrixorigin",
			repo:  "matrixflow",
			want:  "matrixorigin/matrixflow",
		},
		{
			name:  "invalid json falls back",
			data:  `not json`,
			owner: "org",
			repo:  "repo",
			want:  "org/repo",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := repoFromReportJSON([]byte(tt.data), tt.owner, tt.repo)
			if got != tt.want {
				t.Errorf("repoFromReportJSON() = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestReportMetaSortOrder(t *testing.T) {
	// Verify that the sort logic produces descending order by generated_at
	items := []ReportMeta{
		{ID: "a", GeneratedAt: "2026-02-20T10:00:00"},
		{ID: "b", GeneratedAt: "2026-02-25T10:00:00"},
		{ID: "c", GeneratedAt: "2026-02-22T10:00:00"},
	}

	// Replicate the sort from handleListReports
	sortReportsByGeneratedAt(items)

	expected := []string{"b", "c", "a"}
	for i, id := range expected {
		if items[i].ID != id {
			t.Errorf("index %d: got ID %q, want %q", i, items[i].ID, id)
		}
	}
}
