package workflow

import (
	"context"
	"fmt"

	moi "github.com/matrixflow/moi-core/go-sdk"
	"github.com/matrixflow/moi-core/go-sdk/dsl"
)

type Installer struct {
	client      *moi.Client
	workspaceID string
}

func NewInstaller(client *moi.Client, workspaceID string) *Installer {
	return &Installer{client: client, workspaceID: workspaceID}
}

func (i *Installer) InstallAll(ctx context.Context) error {
	if err := i.installWF001(ctx); err != nil {
		return err
	}
	if err := i.installWF002(ctx); err != nil {
		return err
	}
	if err := i.installWF003(ctx); err != nil {
		return err
	}
	if err := i.installWF004(ctx); err != nil {
		return err
	}
	if err := i.installWF005(ctx); err != nil {
		return err
	}
	if err := i.installWF006(ctx); err != nil {
		return err
	}
	if err := i.installWF007(ctx); err != nil {
		return err
	}
	return nil
}

func (i *Installer) ensureDefinition(ctx context.Context, name, desc string) (string, error) {
	wfsvc := i.client.Workflows(i.workspaceID)
	list, err := wfsvc.List(ctx, moi.WithWorkflowNameFilter(name))
	if err != nil {
		return "", err
	}
	for _, wf := range list {
		if wf.GetName() == name {
			return wf.GetId(), nil
		}
	}
	created, err := wfsvc.Create(ctx, name, moi.WithWorkflowDefDescription(desc))
	if err != nil {
		return "", err
	}
	return created.GetId(), nil
}

func (i *Installer) createVersion(ctx context.Context, wfID string, builder *dsl.WorkflowBuilder, desc string) error {
	versvc := i.client.WorkflowVersions(i.workspaceID)
	ver, err := versvc.CreateByBuilder(ctx, wfID, builder,
		moi.WithVersionDescription(desc),
	)
	if err != nil {
		return err
	}
	return versvc.Publish(ctx, ver.GetId())
}

func (i *Installer) installWF001(ctx context.Context) error {
	wfID, err := i.ensureDefinition(ctx, "wf-001-issue-sync", "Issue 数据采集与存储")
	if err != nil {
		return err
	}
	builder := dsl.Workflow("wf-001-issue-sync", "root").Chain(
		dsl.WorkItem("collect", "issue:github.collect"),
		dsl.WorkItem("parse", "issue:ai.parse"),
		dsl.WorkItem("relations", "issue:relations.extract"),
		dsl.WorkItem("store", "issue:store.snapshot"),
	)
	return i.createVersion(ctx, wfID, builder, "WF-001 v1")
}

func (i *Installer) installWF002(ctx context.Context) error {
	wfID, err := i.ensureDefinition(ctx, "wf-002-knowledge-base", "知识库生成")
	if err != nil {
		return err
	}
	builder := dsl.Workflow("wf-002-knowledge-base", "root").Chain(
		dsl.WorkItem("build", "issue:knowledge.build"),
	)
	return i.createVersion(ctx, wfID, builder, "WF-002 v1")
}

func (i *Installer) installWF003(ctx context.Context) error {
	wfID, err := i.ensureDefinition(ctx, "wf-003-issue-draft", "自动提 Issue 并生成样板")
	if err != nil {
		return err
	}
	builder := dsl.Workflow("wf-003-issue-draft", "root").Chain(
		dsl.WorkItem("draft", "issue:draft.generate"),
	)
	return i.createVersion(ctx, wfID, builder, "WF-003 v1")
}

func (i *Installer) installWF004(ctx context.Context) error {
	wfID, err := i.ensureDefinition(ctx, "wf-004-issue-create", "创建 Issue")
	if err != nil {
		return err
	}
	builder := dsl.Workflow("wf-004-issue-create", "root").Chain(
		dsl.WorkItem("create", "issue:create"),
	)
	return i.createVersion(ctx, wfID, builder, "WF-004 v1")
}

func (i *Installer) installWF005(ctx context.Context) error {
	wfID, err := i.ensureDefinition(ctx, "wf-005-cleanup", "历史数据清洗")
	if err != nil {
		return err
	}
	builder := dsl.Workflow("wf-005-cleanup", "root").Chain(
		dsl.WorkItem("cleanup", "issue:cleanup"),
	)
	return i.createVersion(ctx, wfID, builder, "WF-005 v1")
}

func (i *Installer) installWF006(ctx context.Context) error {
	wfID, err := i.ensureDefinition(ctx, "wf-006-state-track", "特殊状态记录")
	if err != nil {
		return err
	}
	builder := dsl.Workflow("wf-006-state-track", "root").Chain(
		dsl.WorkItem("track", "issue:state.track"),
	)
	return i.createVersion(ctx, wfID, builder, "WF-006 v1")
}

func (i *Installer) installWF007(ctx context.Context) error {
	wfID, err := i.ensureDefinition(ctx, "wf-007-report", "Issue 分析报告生成")
	if err != nil {
		return err
	}
	builder := dsl.Workflow("wf-007-report", "root").Chain(
		dsl.WorkItem("report", "issue:report.generate"),
	)
	return i.createVersion(ctx, wfID, builder, "WF-007 v1")
}

func MustResult(err error, name string) {
	if err != nil {
		panic(fmt.Sprintf("%s failed: %v", name, err))
	}
}
