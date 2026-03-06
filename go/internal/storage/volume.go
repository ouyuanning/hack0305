package storage

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"path"
	"strings"
	"time"

	moi "github.com/matrixflow/moi-core/go-sdk"
	"github.com/matrixflow/moi-core/model/catalog"
)

type VolumeStore struct {
	client      *moi.Client
	workspaceID string
	databaseID  int64
	volumeName  string
	volumeID    int64
	basePath    string
	baseURL     string
	apiKey      string
}

func NewVolumeStore(client *moi.Client, workspaceID string, databaseID int64, volumeName, basePath, baseURL, apiKey string) *VolumeStore {
	return &VolumeStore{
		client:      client,
		workspaceID: workspaceID,
		databaseID:  databaseID,
		volumeName:  volumeName,
		basePath:    basePath,
		baseURL:     strings.TrimRight(baseURL, "/"),
		apiKey:      apiKey,
	}
}

func (s *VolumeStore) EnsureVolume(ctx context.Context) (int64, error) {
	if s.volumeID != 0 {
		return s.volumeID, nil
	}
	vols, err := s.client.Volumes().List(ctx, s.workspaceID, s.databaseID, moi.WithPageSize(200))
	if err != nil {
		return 0, err
	}
	for _, v := range vols.Items {
		if v.GetName() == s.volumeName {
			s.volumeID = v.GetId()
			return s.volumeID, nil
		}
	}
	created, err := s.client.Volumes().Create(ctx, s.workspaceID, s.databaseID, s.volumeName, moi.WithVolumeComment("issue manager data"))
	if err != nil {
		return 0, err
	}
	s.volumeID = created.GetId()
	return s.volumeID, nil
}

func (s *VolumeStore) UploadJSON(ctx context.Context, filePath string, v any) (*catalog.File, error) {
	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return nil, err
	}
	return s.UploadBytes(ctx, filePath, data, "application/json")
}

func (s *VolumeStore) UploadNDJSON(ctx context.Context, filePath string, lines [][]byte) (*catalog.File, error) {
	var buf bytes.Buffer
	for _, line := range lines {
		buf.Write(line)
		buf.WriteByte('\n')
	}
	return s.UploadBytes(ctx, filePath, buf.Bytes(), "application/x-ndjson")
}

func (s *VolumeStore) UploadBytes(ctx context.Context, filePath string, data []byte, contentType string) (*catalog.File, error) {
	if _, err := s.EnsureVolume(ctx); err != nil {
		return nil, err
	}
	filePath = s.normalize(filePath)
	// Encode path separators into filename since Volume API uses flat storage
	flatName := strings.ReplaceAll(filePath, "/", "__")

	// Step 1: Upload file content via Files API (multipart)
	uploaded, err := s.client.Files().Upload(ctx, s.workspaceID, flatName, bytes.NewReader(data))
	if err != nil {
		return nil, fmt.Errorf("file upload: %w", err)
	}

	// Step 2: Associate the file with the volume
	if err := s.client.VolumeFiles().AddFiles(ctx, s.workspaceID, s.volumeID, []string{uploaded.FileID}); err != nil {
		return nil, fmt.Errorf("add file to volume: %w", err)
	}

	// Return a catalog.File-compatible value using the uploaded file ID
	return &catalog.File{Id: uploaded.FileID, Name: flatName}, nil
}

func (s *VolumeStore) Download(ctx context.Context, fileID string) ([]byte, error) {
	rc, err := s.client.Volumes().Download(ctx, s.workspaceID, fileID)
	if err != nil {
		return nil, err
	}
	defer rc.Close()
	return io.ReadAll(rc)
}

// volumeFileRecord matches the actual JSON returned by the volume files API.
type volumeFileRecord struct {
	FileID   string `json:"file_id"`
	FileName string `json:"file_name"`
}

// ListByPrefix lists volume files whose flat name starts with the given prefix.
// The SDK's WithPrefix filter is not reliably applied server-side, so we fetch
// all files and filter client-side.
func (s *VolumeStore) ListByPrefix(ctx context.Context, prefix string) ([]*catalog.File, error) {
	if _, err := s.EnsureVolume(ctx); err != nil {
		return nil, err
	}
	prefix = s.normalize(prefix)
	flatPrefix := strings.ReplaceAll(prefix, "/", "__")

	// Fetch all files via raw HTTP to get the correct file_id field.
	all, err := s.listAllVolumeFiles(ctx)
	if err != nil {
		return nil, err
	}

	var out []*catalog.File
	for _, r := range all {
		if strings.HasPrefix(r.FileName, flatPrefix) {
			out = append(out, &catalog.File{Id: r.FileID, Name: r.FileName})
		}
	}
	return out, nil
}

// listAllVolumeFiles fetches every file record in the volume using cursor pagination.
func (s *VolumeStore) listAllVolumeFiles(ctx context.Context) ([]volumeFileRecord, error) {
	baseURL := fmt.Sprintf("%s/api/v1/workspaces/%s/volumes/%d/files",
		s.baseURL, s.workspaceID, s.volumeID)

	type response struct {
		Code int `json:"code"`
		Data struct {
			Items         []volumeFileRecord `json:"items"`
			NextPageToken string             `json:"next_page_token"`
		} `json:"data"`
	}

	var all []volumeFileRecord
	pageToken := ""
	for {
		u := baseURL + "?page_size=200"
		if pageToken != "" {
			u += "&page_token=" + pageToken
		}
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, u, nil)
		if err != nil {
			return nil, err
		}
		req.Header.Set("X-API-Key", s.apiKey)

		resp, err := http.DefaultClient.Do(req)
		if err != nil {
			return nil, err
		}
		var result response
		if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
			resp.Body.Close()
			return nil, err
		}
		resp.Body.Close()

		all = append(all, result.Data.Items...)
		if result.Data.NextPageToken == "" {
			break
		}
		pageToken = result.Data.NextPageToken
	}
	return all, nil
}

func (s *VolumeStore) PathForRepo(owner, repo string) string {
	return path.Join(s.basePath, owner, repo)
}

func (s *VolumeStore) SnapshotPath(owner, repo string, t time.Time) string {
	ts := t.Format("20060102_150405")
	return path.Join(s.PathForRepo(owner, repo), "snapshots", ts)
}

func (s *VolumeStore) LatestPath(owner, repo string) string {
	return path.Join(s.PathForRepo(owner, repo), "latest")
}

func (s *VolumeStore) normalize(p string) string {
	p = strings.TrimPrefix(p, "/")
	return p
}

func BuildManifest(snapshot time.Time, files map[string]*catalog.File) map[string]any {
	manifest := map[string]any{
		"snapshot_time": snapshot.Format(time.RFC3339),
		"files":         map[string]any{},
	}
	m := manifest["files"].(map[string]any)
	for k, f := range files {
		m[k] = map[string]any{
			"id":   f.GetId(),
			"name": f.GetName(),
			"size": f.GetSize(),
		}
	}
	return manifest
}

// ClearAllData deletes the entire volume and recreates it to reset all data.
func (s *VolumeStore) ClearAllData(ctx context.Context) error {
	if _, err := s.EnsureVolume(ctx); err != nil {
		return err
	}

	// Delete the entire volume
	volSvc := s.client.Volumes()
	if err := volSvc.Delete(ctx, s.workspaceID, s.volumeID); err != nil {
		return fmt.Errorf("failed to delete volume: %w", err)
	}

	// Reset volume ID so it will be recreated on next use
	s.volumeID = 0

	// Recreate the volume
	if _, err := s.EnsureVolume(ctx); err != nil {
		return fmt.Errorf("failed to recreate volume: %w", err)
	}

	return nil
}
