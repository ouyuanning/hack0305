package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/matrixorigin/issue-manager/internal/analysis"
	"github.com/matrixorigin/issue-manager/internal/config"
	"github.com/matrixorigin/issue-manager/internal/github"
	"github.com/matrixorigin/issue-manager/internal/llm"
	"github.com/matrixorigin/issue-manager/internal/storage"
	"github.com/matrixorigin/issue-manager/internal/workflow"

	moi "github.com/matrixflow/moi-core/go-sdk"
)

func main() {
	cfgPath := flag.String("config", "config.yaml", "config file")
	flag.Parse()

	if len(flag.Args()) == 0 {
		fmt.Println("usage: issuectl <command> [args]")
		os.Exit(1)
	}

	cfg, err := config.Load(*cfgPath)
	if err != nil {
		fmt.Println("config error:", err)
		os.Exit(1)
	}

	client, err := moi.New(cfg.MOI.BaseURL, cfg.MOI.APIKey)
	if err != nil {
		fmt.Println("moi client error:", err)
		os.Exit(1)
	}
	defer client.Close()

	store := storage.NewVolumeStore(client, cfg.MOI.WorkspaceID, cfg.MOI.DatabaseID, cfg.MOI.VolumeName, cfg.Storage.BasePath, cfg.MOI.BaseURL, cfg.MOI.APIKey)
	analyzer := analysis.New(store)
	_ = github.New(cfg.GitHub.BaseURL, cfg.GitHub.Token)
	_ = llm.New(client, cfg.MOI.WorkspaceID, cfg.LLM.Model)

	cmd := flag.Args()[0]
	switch cmd {
	case "workflow":
		if len(flag.Args()) < 2 {
			die("workflow subcommand required")
		}
		sub := flag.Args()[1]
		if sub == "install" {
			inst := workflow.NewInstaller(client, cfg.MOI.WorkspaceID)
			if err := inst.InstallAll(context.Background()); err != nil {
				die(err.Error())
			}
			fmt.Println("workflows installed")
		}
	case "run":
		if len(flag.Args()) < 2 {
			die("run requires wf id")
		}
		wf := flag.Args()[1]
		owner, repo := parseRepo(flag.Args())
		data := map[string]any{"repo_owner": owner, "repo_name": repo}
		if hasFlag(flag.Args(), "--full") {
			data["full_sync"] = true
		}
		if since := getFlagValue(flag.Args(), "--since"); since != "" {
			data["since"] = since
		}
		if userInput := getFlagValue(flag.Args(), "--user-input"); userInput != "" {
			data["user_input"] = userInput
		}
		if images := getFlagValue(flag.Args(), "--images"); images != "" {
			data["images"] = strings.Split(images, ",")
		}
		if url := getFlagValue(flag.Args(), "--browser-issue-url"); url != "" {
			data["browser_issue_url"] = url
		}
		payload, _ := json.Marshal(data)
		def, err := client.Workflows(cfg.MOI.WorkspaceID).GetByName(context.Background(), wf)
		if err != nil {
			die(err.Error())
		}
		versions, err := client.WorkflowVersions(cfg.MOI.WorkspaceID).List(context.Background(), def.GetId())
		if err != nil {
			die(err.Error())
		}
		if len(versions) == 0 {
			die("no workflow versions")
		}
		latest := versions[0]
		for _, v := range versions {
			if v.GetVersion() > latest.GetVersion() {
				latest = v
			}
		}
		task, err := client.Tasks(cfg.MOI.WorkspaceID).Create(context.Background(), "issuectl",
			moi.WithTaskWorkflowVersionID(latest.GetId()),
			moi.WithTaskData(string(payload)),
		)
		if err != nil {
			die(err.Error())
		}
		fmt.Println("task created:", task.GetId())
	case "report":
		owner, repo := parseRepo(flag.Args())
		daily, err := analyzer.DailyReport(context.Background(), owner, repo, time.Now())
		if err != nil {
			die(err.Error())
		}
		progress, err := analyzer.ProgressReport(context.Background(), owner, repo)
		if err != nil {
			die(err.Error())
		}
		fmt.Printf("daily: %+v\nprogress: %+v\n", daily, progress)
	default:
		die("unknown command")
	}
}

func parseRepo(args []string) (string, string) {
	for i, a := range args {
		if a == "--repo" && i+1 < len(args) {
			parts := splitRepo(args[i+1])
			return parts[0], parts[1]
		}
	}
	return "", ""
}

func splitRepo(v string) [2]string {
	var out [2]string
	for i, p := range splitOnce(v, "/") {
		out[i] = p
	}
	return out
}

func splitOnce(s, sep string) []string {
	idx := -1
	if i := len(s); i > 0 {
		idx = indexOf(s, sep)
	}
	if idx < 0 {
		return []string{s, ""}
	}
	return []string{s[:idx], s[idx+1:]}
}

func indexOf(s, sep string) int {
	for i := 0; i+len(sep) <= len(s); i++ {
		if s[i:i+len(sep)] == sep {
			return i
		}
	}
	return -1
}

func hasFlag(args []string, flag string) bool {
	for _, a := range args {
		if a == flag {
			return true
		}
	}
	return false
}

func getFlagValue(args []string, flag string) string {
	for i, a := range args {
		if a == flag && i+1 < len(args) {
			return args[i+1]
		}
	}
	return ""
}

func die(msg string) {
	fmt.Println(msg)
	os.Exit(1)
}
