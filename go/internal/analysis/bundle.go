package analysis

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/matrixorigin/issue-manager/internal/issue"
	"github.com/matrixorigin/issue-manager/internal/storage"
)

type Bundle struct {
	Snapshots []issue.Snapshot
	Relations []issue.Relation
	AIParse   []map[string]any
}

func (g *Generator) LoadLatestBundle(ctx context.Context, owner, repo string) (*Bundle, error) {
	manifest, err := g.loadLatestManifest(ctx, owner, repo)
	if err != nil {
		return nil, err
	}
	bundle := &Bundle{}
	if ref, ok := manifest.Files["issues"]; ok {
		data, err := g.store.Download(ctx, ref.ID)
		if err != nil {
			return nil, err
		}
		items, err := decodeSnapshots(data)
		if err != nil {
			return nil, err
		}
		bundle.Snapshots = items
	}
	if ref, ok := manifest.Files["relations"]; ok {
		data, err := g.store.Download(ctx, ref.ID)
		if err != nil {
			return nil, err
		}
		items, err := decodeRelations(data)
		if err != nil {
			return nil, err
		}
		bundle.Relations = items
	}
	if ref, ok := manifest.Files["ai_parse"]; ok {
		data, err := g.store.Download(ctx, ref.ID)
		if err != nil {
			return nil, err
		}
		items, err := decodeAIParse(data)
		if err != nil {
			return nil, err
		}
		bundle.AIParse = items
	}
	return bundle, nil
}

func (g *Generator) loadLatestManifest(ctx context.Context, owner, repo string) (*storage.Manifest, error) {
	latestPrefix := g.store.LatestPath(owner, repo)
	files, err := g.store.ListByPrefix(ctx, latestPrefix+"/manifest.json")
	if err != nil {
		return nil, err
	}
	if len(files) == 0 {
		return nil, fmt.Errorf("latest manifest not found")
	}
	return g.store.ReadManifest(ctx, files[0].GetId())
}

func decodeRelations(data []byte) ([]issue.Relation, error) {
	sc := bufio.NewScanner(strings.NewReader(string(data)))
	sc.Buffer(make([]byte, 0, 64*1024), 10*1024*1024)
	var out []issue.Relation
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" {
			continue
		}
		var s issue.Relation
		if err := json.Unmarshal([]byte(line), &s); err != nil {
			return nil, err
		}
		out = append(out, s)
	}
	if err := sc.Err(); err != nil {
		return nil, err
	}
	return out, nil
}

func decodeAIParse(data []byte) ([]map[string]any, error) {
	sc := bufio.NewScanner(strings.NewReader(string(data)))
	sc.Buffer(make([]byte, 0, 64*1024), 10*1024*1024)
	var out []map[string]any
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" {
			continue
		}
		var s map[string]any
		if err := json.Unmarshal([]byte(line), &s); err != nil {
			return nil, err
		}
		out = append(out, s)
	}
	if err := sc.Err(); err != nil {
		return nil, err
	}
	return out, nil
}
