package storage

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
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
}

func NewVolumeStore(client *moi.Client, workspaceID string, databaseID int64, volumeName, basePath string) *VolumeStore {
	return &VolumeStore{
		client:      client,
		workspaceID: workspaceID,
		databaseID:  databaseID,
		volumeName:  volumeName,
		basePath:    basePath,
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
	reader := bytes.NewReader(data)
	return s.client.Volumes().Upload(ctx, s.workspaceID, s.volumeID, filePath, reader, moi.WithContentType(contentType))
}

func (s *VolumeStore) Download(ctx context.Context, fileID string) ([]byte, error) {
	rc, err := s.client.Volumes().Download(ctx, s.workspaceID, fileID)
	if err != nil {
		return nil, err
	}
	defer rc.Close()
	return io.ReadAll(rc)
}

func (s *VolumeStore) ListByPrefix(ctx context.Context, prefix string) ([]*catalog.File, error) {
	if _, err := s.EnsureVolume(ctx); err != nil {
		return nil, err
	}
	prefix = s.normalize(prefix)
	return s.client.Volumes().ListFiles(ctx, s.workspaceID, s.volumeID, moi.WithPrefix(prefix))
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
