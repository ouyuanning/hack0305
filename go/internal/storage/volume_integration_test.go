//go:build integration

package storage_test

import (
	"context"
	"os"
	"strconv"
	"testing"

	moi "github.com/matrixflow/moi-core/go-sdk"
	"github.com/matrixorigin/issue-manager/internal/storage"
)

// Run with: go test -tags integration -v ./internal/storage/ -run TestUpload
// Requires env vars: MOI_BASE_URL, MOI_API_KEY, MOI_WORKSPACE_ID, MOI_DATABASE_ID, MOI_VOLUME_NAME

func TestUploadIntegration(t *testing.T) {
	baseURL := env(t, "MOI_BASE_URL")
	apiKey := env(t, "MOI_API_KEY")
	workspaceID := env(t, "MOI_WORKSPACE_ID")
	databaseID := envInt64(t, "MOI_DATABASE_ID")
	volumeName := env(t, "MOI_VOLUME_NAME")

	client, err := moi.New(baseURL, apiKey)
	if err != nil {
		t.Fatalf("moi client: %v", err)
	}
	defer client.Close()

	store := storage.NewVolumeStore(client, workspaceID, databaseID, volumeName, "repos", baseURL, apiKey)
	ctx := context.Background()

	// Test 1: upload small JSON
	t.Run("upload_json", func(t *testing.T) {
		f, err := store.UploadJSON(ctx, "test/integration/hello.json", map[string]any{"hello": "world"})
		if err != nil {
			t.Fatalf("UploadJSON: %v", err)
		}
		t.Logf("uploaded: id=%s name=%s", f.GetId(), f.GetName())
	})

	// Test 2: upload NDJSON
	t.Run("upload_ndjson", func(t *testing.T) {
		lines := [][]byte{
			[]byte(`{"issue_number":1,"title":"test"}`),
			[]byte(`{"issue_number":2,"title":"test2"}`),
		}
		f, err := store.UploadNDJSON(ctx, "test/integration/issues.ndjson", lines)
		if err != nil {
			t.Fatalf("UploadNDJSON: %v", err)
		}
		t.Logf("uploaded: id=%s name=%s", f.GetId(), f.GetName())
	})

	// Test 3: download what we uploaded
	t.Run("download", func(t *testing.T) {
		f, err := store.UploadJSON(ctx, "test/integration/download_test.json", map[string]any{"key": "value"})
		if err != nil {
			t.Fatalf("upload: %v", err)
		}
		data, err := store.Download(ctx, f.GetId())
		if err != nil {
			t.Fatalf("download: %v", err)
		}
		t.Logf("downloaded %d bytes: %s", len(data), string(data))
	})
}

func env(t *testing.T, key string) string {
	t.Helper()
	v := os.Getenv(key)
	if v == "" {
		t.Skipf("skipping: %s not set", key)
	}
	return v
}

func envInt64(t *testing.T, key string) int64 {
	t.Helper()
	v := env(t, key)
	n, err := strconv.ParseInt(v, 10, 64)
	if err != nil {
		t.Fatalf("%s must be an integer: %v", key, err)
	}
	return n
}
