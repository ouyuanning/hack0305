package main

import (
	"context"
	"flag"
	"fmt"
	"os"

	"github.com/matrixorigin/issue-manager/internal/analysis"
	"github.com/matrixorigin/issue-manager/internal/config"
	"github.com/matrixorigin/issue-manager/internal/email"
	"github.com/matrixorigin/issue-manager/internal/github"
	"github.com/matrixorigin/issue-manager/internal/llm"
	"github.com/matrixorigin/issue-manager/internal/storage"
	"github.com/matrixorigin/issue-manager/internal/templates"
	"github.com/matrixorigin/issue-manager/internal/workflow"

	moi "github.com/matrixflow/moi-core/go-sdk"
)

func main() {
	cfgPath := flag.String("config", "config.yaml", "config file")
	workerID := flag.String("worker-id", "issue-worker", "worker id")
	flag.Parse()

	cfg, err := config.Load(*cfgPath)
	if err != nil {
		fmt.Println("config error:", err)
		os.Exit(1)
	}

	client, err := moi.New(cfg.MOI.BaseURL, cfg.MOI.APIKey, moi.WithWorkerID(*workerID))
	if err != nil {
		fmt.Println("moi client error:", err)
		os.Exit(1)
	}
	defer client.Close()

	store := storage.NewVolumeStore(client, cfg.MOI.WorkspaceID, cfg.MOI.DatabaseID, cfg.MOI.VolumeName, cfg.Storage.BasePath, cfg.MOI.BaseURL, cfg.MOI.APIKey)
	analyzer := analysis.New(store)
	gh := github.New(cfg.GitHub.BaseURL, cfg.GitHub.Token)
	llmClient := llm.New(client, cfg.MOI.WorkspaceID, cfg.LLM.Model)

	tplStore, _ := templates.Load("src/feature_issue_and_kanban/templates")

	env := &workflow.Env{GitHub: gh, LLM: llmClient, Store: store, Analyzer: analyzer, WorkspaceID: cfg.MOI.WorkspaceID, Client: client}
	env.BrowserCDP = cfg.Browser.CDPURL
	env.BrowserCDPEnabled = cfg.Browser.CDPEnabled
	env.Templates = tplStore
	env.MirrorLocal = cfg.Report.MirrorLocal
	env.MirrorPath = cfg.Report.MirrorPath
	env.SMTPConfig = email.Config{
		Host:     cfg.SMTP.Host,
		Port:     cfg.SMTP.Port,
		User:     cfg.SMTP.User,
		Password: cfg.SMTP.Password,
		From:     cfg.SMTP.From,
		FromName: cfg.SMTP.FromName,
	}
	env.EmailTo = cfg.SMTP.DefaultTo

	worker := client.Worker("")
	if err := workflow.RegisterWorkItems(worker, env); err != nil {
		fmt.Println("register workitems error:", err)
		os.Exit(1)
	}
	if err := worker.Connect(context.Background()); err != nil {
		fmt.Println("worker connect error:", err)
		os.Exit(1)
	}
	select {}
}
