package storage

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/matrixflow/moi-core/model/catalog"
)

type Manifest struct {
	SnapshotTime string                 `json:"snapshot_time"`
	Files        map[string]ManifestRef `json:"files"`
}

type ManifestRef struct {
	ID   string `json:"id"`
	Name string `json:"name"`
	Size int64  `json:"size"`
}

func (s *VolumeStore) UploadManifest(ctx context.Context, path string, manifest Manifest) (*catalog.File, error) {
	return s.UploadJSON(ctx, path, manifest)
}

func (s *VolumeStore) ReadManifest(ctx context.Context, fileID string) (*Manifest, error) {
	data, err := s.Download(ctx, fileID)
	if err != nil {
		return nil, err
	}
	var m Manifest
	if err := json.Unmarshal(data, &m); err != nil {
		return nil, err
	}
	if m.Files == nil {
		return nil, fmt.Errorf("invalid manifest: missing files")
	}
	return &m, nil
}
