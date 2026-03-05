package browser

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"os"
	"os/exec"
	"regexp"
	"runtime"
	"strings"
	"time"
)

var issueURLRe = regexp.MustCompile(`https?://github\.com/[^/]+/[^/]+/issues/\d+`)

func DetectIssueURL(ctx context.Context) (string, string) {
	if url := detectCDP(ctx, ""); url != "" {
		return url, "cdp"
	}
	if url := detectWindow(ctx); url != "" {
		return url, "window"
	}
	if url := detectClipboard(ctx); url != "" {
		return url, "clipboard"
	}
	return "", "manual"
}

func DetectIssueURLWithCDP(ctx context.Context, cdpURL string, enabled bool) (string, string) {
	if !enabled {
		return "", "manual"
	}
	if url := detectCDP(ctx, cdpURL); url != "" {
		return url, "cdp"
	}
	if url := detectWindow(ctx); url != "" {
		return url, "window"
	}
	if url := detectClipboard(ctx); url != "" {
		return url, "clipboard"
	}
	return "", "manual"
}

// detectCDP queries a Chrome DevTools endpoint for active tabs.
// It reads CDP endpoint from arg or CDP_URL env (default http://127.0.0.1:9222).
func detectCDP(ctx context.Context, cdpURL string) string {
	endpoint := strings.TrimSpace(cdpURL)
	if endpoint == "" {
		endpoint = os.Getenv("CDP_URL")
	}
	if endpoint == "" {
		endpoint = "http://127.0.0.1:9222"
	}
	client := &http.Client{Timeout: 2 * time.Second}

	// Try /json to list pages
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint+"/json", nil)
	if err != nil {
		return ""
	}
	resp, err := client.Do(req)
	if err != nil {
		return ""
	}
	defer resp.Body.Close()

	var pages []struct {
		Type  string `json:"type"`
		URL   string `json:"url"`
		Title string `json:"title"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&pages); err != nil {
		return ""
	}
	for _, p := range pages {
		if p.Type != "page" {
			continue
		}
		if url := extractURL(p.URL); url != "" {
			return url
		}
		if url := extractURL(p.Title); url != "" {
			return url
		}
	}
	return ""
}

func detectWindow(ctx context.Context) string {
	if runtime.GOOS != "darwin" {
		return detectWindowOther(ctx)
	}
	cmd := exec.CommandContext(ctx, "osascript", "-e", `tell application \"System Events\" to tell (first application process whose frontmost is true) to get name of front window`)
	out, err := cmd.Output()
	if err != nil {
		return ""
	}
	return extractURL(string(out))
}

func detectClipboard(ctx context.Context) string {
	if runtime.GOOS == "darwin" {
		cmd := exec.CommandContext(ctx, "pbpaste")
		out, err := cmd.Output()
		if err == nil {
			return extractURL(string(out))
		}
	}
	return ""
}

func detectWindowOther(ctx context.Context) string {
	switch runtime.GOOS {
	case "windows":
		if cmdPath, _ := exec.LookPath("powershell"); cmdPath != "" {
			script := `$hwnd = (Add-Type -Name Win32 -Namespace User32 -PassThru -MemberDefinition @'
[DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
[DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);
'@)::GetForegroundWindow();
$sb = New-Object System.Text.StringBuilder 1024;
[void][User32.Win32]::GetWindowText($hwnd, $sb, $sb.Capacity);
$sb.ToString()`
			out, err := exec.CommandContext(ctx, "powershell", "-NoProfile", "-Command", script).Output()
			if err == nil {
				return extractURL(string(out))
			}
		}
	case "linux":
		if cmdPath, _ := exec.LookPath("xdotool"); cmdPath != "" {
			out, err := exec.CommandContext(ctx, "xdotool", "getactivewindow", "getwindowname").Output()
			if err == nil {
				return extractURL(string(out))
			}
		}
		if cmdPath, _ := exec.LookPath("xprop"); cmdPath != "" {
			script := `xprop -root _NET_ACTIVE_WINDOW | awk '{print $5}'`
			out, err := exec.CommandContext(ctx, "bash", "-lc", script).Output()
			if err == nil {
				winID := strings.TrimSpace(string(out))
				if winID != "" {
					out2, err := exec.CommandContext(ctx, "xprop", "-id", winID, "_NET_WM_NAME").Output()
					if err == nil {
						return extractURL(string(out2))
					}
				}
			}
		}
	}
	return ""
}

func extractURL(text string) string {
	m := issueURLRe.FindString(text)
	return m
}

func WaitManual(ctx context.Context, input string) (string, error) {
	select {
	case <-ctx.Done():
		return "", ctx.Err()
	case <-time.After(10 * time.Millisecond):
		if strings.TrimSpace(input) == "" {
			return "", errors.New("manual input required")
		}
		return input, nil
	}
}
