package orchestrator

import "traning_ai/backend/internal/domain"

// StageOrder — thứ tự cứng §5 (ponytail: slice, không saga engine).
var StageOrder = []domain.Stage{
	domain.StageSplittingFrames,
	domain.StageEmbedding,
	domain.StageAsrExtracting,
	domain.StageHighlightScoring,
	domain.StageSummarizing,
	domain.StageCompleted,
}

var stageIndex = func() map[domain.Stage]int {
	m := map[domain.Stage]int{}
	for i, s := range StageOrder {
		m[s] = i
	}
	return m
}()

func NextStage(cur domain.Stage) (domain.Stage, bool) {
	i, ok := stageIndex[cur]
	if !ok || i+1 >= len(StageOrder) {
		return "", false
	}
	return StageOrder[i+1], true
}
