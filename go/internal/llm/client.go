package llm

import (
	"context"
	"fmt"
	"strings"

	moi "github.com/matrixflow/moi-core/go-sdk"
)

type Client struct {
	service *moi.LLMService
	model   string
}

func New(client *moi.Client, workspaceID, model string) *Client {
	return &Client{service: client.LLM(workspaceID), model: model}
}

func (c *Client) Ask(ctx context.Context, systemPrompt, userPrompt string) (string, error) {
	prompt := systemPrompt + "\n" + userPrompt
	ch, err := c.service.ChatCompletion(ctx, prompt, c.model)
	if err != nil {
		return "", err
	}
	var b strings.Builder
	for token := range ch {
		b.WriteString(token)
	}
	out := strings.TrimSpace(b.String())
	if out == "" {
		return "", fmt.Errorf("empty llm response")
	}
	return out, nil
}
