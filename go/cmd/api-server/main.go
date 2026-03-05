package main

import (
	"flag"
	"fmt"
	"log"
	"os"

	"github.com/gin-gonic/gin"
	moi "github.com/matrixflow/moi-core/go-sdk"

	"github.com/matrixorigin/issue-manager/internal/analysis"
	"github.com/matrixorigin/issue-manager/internal/api"
	"github.com/matrixorigin/issue-manager/internal/config"
	"github.com/matrixorigin/issue-manager/internal/github"
	"github.com/matrixorigin/issue-manager/internal/llm"
	"github.com/matrixorigin/issue-manager/internal/storage"
)

func main() {
	cfgPath := flag.String("config", "config.yaml", "path to config file")
	addr := flag.String("addr", ":8080", "HTTP listen address")
	flag.Parse()

	cfg, err := config.Load(*cfgPath)
	if err != nil {
		log.Fatalf("config error: %v", err)
	}

	client, err := moi.New(cfg.MOI.BaseURL, cfg.MOI.APIKey)
	if err != nil {
		log.Fatalf("moi client error: %v", err)
	}
	defer client.Close()

	store := storage.NewVolumeStore(
		client,
		cfg.MOI.WorkspaceID,
		cfg.MOI.DatabaseID,
		cfg.MOI.VolumeName,
		cfg.Storage.BasePath,
	)
	analyzer := analysis.New(store)
	gh := github.New(cfg.GitHub.BaseURL, cfg.GitHub.Token)
	llmClient := llm.New(client, cfg.MOI.WorkspaceID, cfg.LLM.Model)

	// Default repos — can be extended via config in the future.
	repos := []api.RepoInfo{
		{Owner: "matrixorigin", Name: "matrixone", DisplayName: "MatrixOne"},
		{Owner: "matrixorigin", Name: "matrixflow", DisplayName: "MatrixFlow"},
	}

	srv := &api.Server{
		Store:     store,
		Analyzer:  analyzer,
		GitHub:    gh,
		LLM:       llmClient,
		Repos:     repos,
		Workflows: api.NewWorkflowManager(),
	}

	r := gin.New()
	r.Use(gin.Logger())
	r.Use(api.ErrorMiddleware())
	r.Use(api.CORSMiddleware(api.DefaultCORSConfig()))
	srv.RegisterRoutes(r)

	fmt.Fprintf(os.Stdout, "api-server listening on %s\n", *addr)
	if err := r.Run(*addr); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
