package builder

import (
	"encoding/json"
	"math"

	. "openreplay/backend/pkg/messages"
)

const MIN_COUNT = 3
const MEM_RATE_THRESHOLD = 300 // % to average 

type memoryIssueDetector struct {
	startMessageID uint64
	startTimestamp uint64
	rate           int
	count          float64
	sum            float64
	contextString  string
}

func (f *memoryIssueDetector) HandleMessage(message Message, messageID uint64, timestamp uint64) *IssueEvent {
	switch msg := message.(type) {
	case *SetPageLocation:
		f.HandleSetPageLocation(msg)
	case *PerformanceTrack:
		return f.HandlePerformanceTrack(msg, messageID, timestamp)
	case *SessionEnd:
		return f.Build()
	}
	return nil
}

func (f *memoryIssueDetector) Build() *IssueEvent {
	if f.startTimestamp == 0 {
		return nil
	}
	payload, _ := json.Marshal(struct{ Rate int }{f.rate - 100})
	i := &IssueEvent{
		Type:          "memory",
		Timestamp:     f.startTimestamp,
		MessageID:     f.startMessageID,
		ContextString: f.contextString,
		Payload:       string(payload),
	}
	f.startTimestamp = 0
	f.startMessageID = 0
	f.rate = 0
	return i
}

func (f *memoryIssueDetector) HandleSetPageLocation(msg *SetPageLocation) {
	f.contextString = msg.URL
}

func (f *memoryIssueDetector) HandlePerformanceTrack(msg *PerformanceTrack, messageID uint64, timestamp uint64) *IssueEvent {
	if f.count < MIN_COUNT {
		f.sum += float64(msg.UsedJSHeapSize)
		f.count++
		return nil
	}

	average := f.sum / f.count
	rate := int(math.Round(float64(msg.UsedJSHeapSize) / average * 100))

	f.sum += float64(msg.UsedJSHeapSize)
	f.count++

	if rate >= MEM_RATE_THRESHOLD {
		if f.startTimestamp == 0 {
			f.startTimestamp = timestamp
			f.startMessageID = messageID
		}
		if f.rate < rate {
			f.rate = rate
		}
	} else {
		return f.Build()
	}

	return nil
}
