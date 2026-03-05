package github

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"
	"time"
)

type Client struct {
	baseURL string
	token   string
	http    *http.Client
}

func New(baseURL, token string) *Client {
	return &Client{
		baseURL: baseURL,
		token:   token,
		http:    &http.Client{Timeout: 60 * time.Second},
	}
}

type Issue struct {
	ID          int64      `json:"id"`
	Number      int        `json:"number"`
	Title       string     `json:"title"`
	Body        string     `json:"body"`
	State       string     `json:"state"`
	Labels      []Label    `json:"labels"`
	Assignee    *User      `json:"assignee"`
	Milestone   *Milestone `json:"milestone"`
	CreatedAt   string     `json:"created_at"`
	UpdatedAt   string     `json:"updated_at"`
	ClosedAt    *string    `json:"closed_at"`
	PullRequest any        `json:"pull_request"`
}

type Label struct {
	Name string `json:"name"`
}

type User struct {
	Login string `json:"login"`
}

type Milestone struct {
	Title string `json:"title"`
}

type Comment struct {
	ID        int64  `json:"id"`
	User      User   `json:"user"`
	Body      string `json:"body"`
	CreatedAt string `json:"created_at"`
	UpdatedAt string `json:"updated_at"`
}

func (c *Client) FetchIssues(ctx context.Context, owner, repo, state string, since *time.Time, page, perPage int) ([]Issue, int, error) {
	url := fmt.Sprintf("%s/repos/%s/%s/issues?state=%s&page=%d&per_page=%d", c.baseURL, owner, repo, state, page, perPage)
	if since != nil {
		url += "&since=" + since.UTC().Format(time.RFC3339)
	}
	var issues []Issue
	rawCount, err := c.do(ctx, url, &issues)
	if err != nil {
		return nil, 0, err
	}
	filtered := make([]Issue, 0, len(issues))
	for _, it := range issues {
		if it.PullRequest != nil {
			continue
		}
		filtered = append(filtered, it)
	}
	return filtered, rawCount, nil
}

func (c *Client) FetchComments(ctx context.Context, owner, repo string, number int) ([]Comment, error) {
	url := fmt.Sprintf("%s/repos/%s/%s/issues/%d/comments", c.baseURL, owner, repo, number)
	var comments []Comment
	_, err := c.do(ctx, url, &comments)
	return comments, err
}

func (c *Client) FetchTimeline(ctx context.Context, owner, repo string, number int) ([]map[string]any, error) {
	url := fmt.Sprintf("%s/repos/%s/%s/issues/%d/timeline", c.baseURL, owner, repo, number)
	var events []map[string]any
	_, err := c.do(ctx, url, &events)
	return events, err
}

func (c *Client) CreateIssue(ctx context.Context, owner, repo, title, body string, labels, assignees []string) (map[string]any, error) {
	url := fmt.Sprintf("%s/repos/%s/%s/issues", c.baseURL, owner, repo)
	payload := map[string]any{
		"title":     title,
		"body":      body,
		"labels":    labels,
		"assignees": assignees,
	}
	data, _ := json.Marshal(payload)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, io.NopCloser(strings.NewReader(string(data))))
	if err != nil {
		return nil, err
	}
	c.applyHeaders(req)
	resp, err := c.http.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("github create issue failed: %s", string(bodyBytes))
	}
	var out map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return nil, err
	}
	return out, nil
}

func (c *Client) do(ctx context.Context, url string, out any) (int, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return 0, err
	}
	c.applyHeaders(req)
	resp, err := c.http.Do(req)
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()

	if resp.StatusCode == 403 || resp.StatusCode == 429 {
		if reset := resp.Header.Get("X-RateLimit-Reset"); reset != "" {
			if ts, err := strconv.ParseInt(reset, 10, 64); err == nil {
				sleep := time.Until(time.Unix(ts, 0)) + 2*time.Second
				if sleep > 0 && sleep < 10*time.Minute {
					time.Sleep(sleep)
					return c.do(ctx, url, out)
				}
			}
		}
	}

	if resp.StatusCode >= 300 {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return 0, fmt.Errorf("github api error: %s", string(bodyBytes))
	}

	remaining := 0
	if v := resp.Header.Get("X-RateLimit-Remaining"); v != "" {
		remaining, _ = strconv.Atoi(v)
		if remaining < 10 {
			if reset := resp.Header.Get("X-RateLimit-Reset"); reset != "" {
				if ts, err := strconv.ParseInt(reset, 10, 64); err == nil {
					sleep := time.Until(time.Unix(ts, 0)) + 2*time.Second
					if sleep > 0 && sleep < 10*time.Minute {
						time.Sleep(sleep)
					}
				}
			}
		}
	}

	if err := json.NewDecoder(resp.Body).Decode(out); err != nil {
		return 0, err
	}
	return remaining, nil
}

func (c *Client) applyHeaders(req *http.Request) {
	req.Header.Set("Authorization", "token "+c.token)
	req.Header.Set("Accept", "application/vnd.github.v3+json")
	req.Header.Set("User-Agent", "Issue-Manager")
}
