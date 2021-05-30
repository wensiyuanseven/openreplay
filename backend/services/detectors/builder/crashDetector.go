package builder

import (
	. "openreplay/backend/pkg/messages"
)

const CPU_ISSUE_WINDOW = 3000
const MEM_ISSUE_WINDOW = 4 * 1000
const DOM_DROP_WINDOW = 200
//const CLICK_RELATION_DISTANCE = 1200

type crashDetector struct {
	startTimestamp uint64
}

func (*crashDetector) buildCrashEvent(s []*IssueEvent) *IssueEvent{
	var cpuIssues []*IssueEvent
	var memIssues []*IssueEvent
	var domDrops []*IssueEvent
	for _, e := range s {
		if e.Type == "cpu" {
			cpuIssues = append(cpuIssues, e)
		}
		if e.Type == "memory" {
			memIssues = append(memIssues, e)
		}
		if e.Type == "dom_drop" {
			domDrops = append(domDrops, e)
		}
	}
	var i, j, k int
	for _, e := range s {
		for i < len(cpuIssues) && cpuIssues[i].Timestamp+CPU_ISSUE_WINDOW < e.Timestamp {
			i++
		}
		for j < len(memIssues) && memIssues[j].Timestamp+MEM_ISSUE_WINDOW < e.Timestamp {
			j++
		}
		for k < len(domDrops) && domDrops[k].Timestamp+DOM_DROP_WINDOW < e.Timestamp { //Actually different type of issue
			k++
		}
		if i == len(cpuIssues) && j == len(memIssues) && k == len(domDrops) {
			break
		}
		if (i < len(cpuIssues) && cpuIssues[i].Timestamp < e.Timestamp+CPU_ISSUE_WINDOW) ||
			(j < len(memIssues) && memIssues[j].Timestamp < e.Timestamp+MEM_ISSUE_WINDOW) ||
			(k < len(domDrops) && domDrops[k].Timestamp < e.Timestamp+DOM_DROP_WINDOW) {
			contextString := "UNKNOWN"
			return &IssueEvent{
				MessageID: e.MessageID,
				Timestamp: e.Timestamp,
				Type: "crash",
				ContextString: contextString,
				Context: "",
			}
		}
	}
	return nil
}

func (cr *crashDetector) HandleMessage(message Message, s []*IssueEvent) *IssueEvent{
	// Only several message types can trigger crash
	//	which is by our definition, a combination of DomDrop event, CPU and Memory issues
	switch message.(type) {
	case *SessionEnd:
		return cr.buildCrashEvent(s)
	case *PerformanceTrack:
		return cr.buildCrashEvent(s)
	}
	return nil
}
