package cmd

import (
	"testing"

	"blog/scripts/mdtools/internal/mdcards"
)

func sampleGaps() []mdcards.Gap {
	return []mdcards.Gap{
		{Path: "content/backend/a.md", Name: "MySQL", Reason: "out-of-scope", Cards: []string{"devops/infra/knowledge-cards/mysql"}},
		{Path: "content/backend/b.md", Name: "DNS", Reason: "out-of-scope", Cards: []string{"devops/infra/knowledge-cards/dns"}},
		{Path: "content/backend/a.md", Name: "Schema", Reason: "config", Cards: []string{"backend/01-database/sql/knowledge-cards/schema-namespace"}},
		{Path: "content/_index.md", Name: "Beacon", Reason: "folder-unscoped", Cards: []string{"backend/knowledge-cards/beacon"}},
	}
}

func TestSummarizeGapsByFolders(t *testing.T) {
	got := summarizeGaps(sampleGaps())
	if got["backend\tout-of-scope\tdevops"] != 2 {
		t.Errorf("backend → devops out-of-scope: got %v", got)
	}
	if got["backend\tconfig\tbackend"] != 1 {
		t.Errorf("excluded names are counted too: got %v", got)
	}
	if got["-\tfolder-unscoped\tbackend"] != 1 {
		t.Errorf("home page folder is \"-\": got %v", got)
	}
}
