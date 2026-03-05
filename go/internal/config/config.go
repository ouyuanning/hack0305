package config

import (
	"errors"
	"fmt"
	"os"
	"strconv"
	"strings"

	"gopkg.in/yaml.v3"
)

type Config struct {
	MOI     MOIConfig     `yaml:"moi"`
	GitHub  GitHubConfig  `yaml:"github"`
	LLM     LLMConfig     `yaml:"llm"`
	SMTP    SMTPConfig    `yaml:"smtp"`
	Storage StorageConfig `yaml:"storage"`
	Report  ReportConfig  `yaml:"report"`
	Browser BrowserConfig `yaml:"browser"`
}

type MOIConfig struct {
	BaseURL     string `yaml:"base_url"`
	APIKey      string `yaml:"api_key"`
	WorkspaceID string `yaml:"workspace_id"`
	DatabaseID  int64  `yaml:"database_id"`
	VolumeName  string `yaml:"volume_name"`
}

type GitHubConfig struct {
	Token   string `yaml:"token"`
	BaseURL string `yaml:"base_url"`
}

type LLMConfig struct {
	Model string `yaml:"model"`
}

type SMTPConfig struct {
	Host      string `yaml:"host"`
	Port      int    `yaml:"port"`
	User      string `yaml:"user"`
	Password  string `yaml:"password"`
	From      string `yaml:"from"`
	FromName  string `yaml:"from_name"`
	DefaultTo string `yaml:"default_to"`
}

type StorageConfig struct {
	BasePath string `yaml:"base_path"`
}

type ReportConfig struct {
	MirrorLocal bool   `yaml:"mirror_local"`
	MirrorPath  string `yaml:"mirror_path"`
}

type BrowserConfig struct {
	CDPURL     string `yaml:"cdp_url"`
	CDPEnabled bool   `yaml:"cdp_enabled"`
}

func Load(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read config: %w", err)
	}
	// Expand ${VAR} placeholders in the YAML with environment variables
	expanded := os.ExpandEnv(string(data))
	var cfg Config
	if err := yaml.Unmarshal([]byte(expanded), &cfg); err != nil {
		return nil, fmt.Errorf("parse config: %w", err)
	}
	overlayEnv(&cfg)
	if err := validate(&cfg); err != nil {
		return nil, err
	}
	return &cfg, nil
}

func overlayEnv(cfg *Config) {
	setStr(&cfg.MOI.BaseURL, "MOI_BASE_URL")
	setStr(&cfg.MOI.APIKey, "MOI_API_KEY")
	setStr(&cfg.MOI.WorkspaceID, "MOI_WORKSPACE_ID")
	setInt64(&cfg.MOI.DatabaseID, "MOI_DATABASE_ID")
	setStr(&cfg.MOI.VolumeName, "MOI_VOLUME_NAME")

	setStr(&cfg.GitHub.Token, "GITHUB_TOKEN")
	setStr(&cfg.GitHub.BaseURL, "GITHUB_API_BASE_URL")

	setStr(&cfg.LLM.Model, "LLM_MODEL")

	setStr(&cfg.SMTP.Host, "SMTP_HOST")
	setInt(&cfg.SMTP.Port, "SMTP_PORT")
	setStr(&cfg.SMTP.User, "SMTP_USER")
	setStr(&cfg.SMTP.Password, "SMTP_PASSWORD")
	setStr(&cfg.SMTP.From, "EMAIL_FROM")
	setStr(&cfg.SMTP.FromName, "EMAIL_FROM_NAME")
	setStr(&cfg.SMTP.DefaultTo, "DEFAULT_EMAIL_TO")

	setStr(&cfg.Storage.BasePath, "STORAGE_BASE_PATH")
	setBool(&cfg.Report.MirrorLocal, "REPORT_MIRROR_LOCAL")
	setStr(&cfg.Report.MirrorPath, "REPORT_MIRROR_PATH")
	setStr(&cfg.Browser.CDPURL, "CDP_URL")
	setBool(&cfg.Browser.CDPEnabled, "CDP_ENABLED")
}

func validate(cfg *Config) error {
	var missing []string
	if cfg.MOI.BaseURL == "" {
		missing = append(missing, "moi.base_url")
	}
	if cfg.MOI.APIKey == "" {
		missing = append(missing, "moi.api_key")
	}
	if cfg.MOI.WorkspaceID == "" {
		missing = append(missing, "moi.workspace_id")
	}
	if cfg.MOI.DatabaseID == 0 {
		missing = append(missing, "moi.database_id")
	}
	if cfg.MOI.VolumeName == "" {
		missing = append(missing, "moi.volume_name")
	}
	if cfg.GitHub.Token == "" {
		missing = append(missing, "github.token")
	}
	if cfg.GitHub.BaseURL == "" {
		cfg.GitHub.BaseURL = "https://api.github.com"
	}
	if cfg.LLM.Model == "" {
		cfg.LLM.Model = "gpt-4"
	}
	if cfg.Storage.BasePath == "" {
		cfg.Storage.BasePath = "repos"
	}
	if cfg.Report.MirrorPath == "" {
		cfg.Report.MirrorPath = "data/reports"
	}
	if cfg.Browser.CDPURL == "" {
		cfg.Browser.CDPURL = "http://127.0.0.1:9222"
	}
	if v := os.Getenv("CDP_ENABLED"); v != "" {
		cfg.Browser.CDPEnabled = strings.ToLower(v) != "false"
	}
	if len(missing) > 0 {
		return errors.New("missing required config: " + strings.Join(missing, ", "))
	}
	return nil
}

func setStr(target *string, key string) {
	if v := os.Getenv(key); v != "" {
		*target = v
	}
}

func setInt(target *int, key string) {
	if v := os.Getenv(key); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			*target = n
		}
	}
}

func setInt64(target *int64, key string) {
	if v := os.Getenv(key); v != "" {
		if n, err := strconv.ParseInt(v, 10, 64); err == nil {
			*target = n
		}
	}
}

func setBool(target *bool, key string) {
	if v := os.Getenv(key); v != "" {
		if b, err := strconv.ParseBool(v); err == nil {
			*target = b
		}
	}
}
