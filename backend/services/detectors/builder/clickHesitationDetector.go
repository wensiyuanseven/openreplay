package builder

import (
	. "openreplay/backend/pkg/messages"
)

const HESITATION_THRESHOLD = 3000 // ms

type clickHesitationDetector struct{}

func (chd *clickHesitationDetector) HandleMouseClick(msg *MouseClick, messageID uint64, timestamp uint64) *IssueEvent {
	if msg.HesitationTime > HESITATION_THRESHOLD {
		return &IssueEvent{
			Timestamp:     timestamp,
			MessageID:     messageID,
			Type:          "click_hesitation",
			Context:       msg.Label,
			ContextString: "Click hesitation above 3 seconds",
		}
	}
	return nil
}

func (chd *clickHesitationDetector) HandleMessage(message Message, messageID uint64, timestamp uint64) *IssueEvent {
	switch msg := message.(type) {
	case *MouseClick:
		return chd.HandleMouseClick(msg, messageID, timestamp)
	}
	return nil
}
