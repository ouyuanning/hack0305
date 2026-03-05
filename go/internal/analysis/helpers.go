package analysis

import (
	"math"
	"strings"

	"github.com/matrixorigin/issue-manager/internal/issue"
)

func round(val float64, digits int) float64 {
	pow := math.Pow(10, float64(digits))
	return math.Round(val*pow) / pow
}

func countState(issues []issue.Snapshot, state string) int {
	cnt := 0
	for _, it := range issues {
		if it.State == state {
			cnt++
		}
	}
	return cnt
}

func countBlocked(issues []issue.Snapshot) int {
	cnt := 0
	for _, it := range issues {
		if it.IsBlocked {
			cnt++
		}
	}
	return cnt
}

func hasLabel(labels []string, target string) bool {
	for _, l := range labels {
		if l == target {
			return true
		}
	}
	return false
}

func parseLabels(labels []string) []string {
	return labels
}

func containsAny(text string, kws []string) bool {
	for _, k := range kws {
		if strings.Contains(text, k) {
			return true
		}
	}
	return false
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
