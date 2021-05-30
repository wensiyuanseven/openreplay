package builder

import (
	. "openreplay/backend/pkg/messages"
)

const QUICK_RETURN_THRESHOLD = 3 * 1000

type quickReturnDetector struct {
	timestamp   uint64
	currentPage string
	basePage    string
}

func (qrd *quickReturnDetector) HandleMessage(message Message, messageID uint64, timestamp uint64) *IssueEvent {
	switch msg := message.(type) {
	case *SetPageLocation:
		if msg.NavigationStart != 0 {
			return qrd.HandleSetPageLocation(msg, messageID, timestamp)
		}
	}
	return nil
}

func (qrd *quickReturnDetector) HandleSetPageLocation(msg *SetPageLocation, messageID uint64, timestamp uint64) *IssueEvent {

	if (timestamp-qrd.timestamp > 0) && (timestamp-qrd.timestamp < QUICK_RETURN_THRESHOLD) && (
		msg.Referrer == qrd.basePage) {
		i := &IssueEvent{
			Type:          "quick_return",
			Timestamp:     timestamp,
			MessageID:     messageID,
			ContextString: "Quick return from a page",
			Context:       msg.Referrer + ", " + qrd.currentPage,
			Payload:       ""}
		qrd.basePage = qrd.currentPage
		qrd.currentPage = msg.Referrer
		qrd.timestamp = timestamp
		return i
	}

	if msg.Referrer != qrd.currentPage {
		qrd.timestamp = timestamp
		qrd.basePage = qrd.currentPage
		qrd.currentPage = msg.Referrer
	}
	return nil
}
