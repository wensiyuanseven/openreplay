package builder

import (
	. "openreplay/backend/pkg/messages"
)

const MAX_HISTORY_OF_INPUTS = 10

type repetitiveInputDetector struct {
	lastInputs  []string
	currentPage string
}

func (rid *repetitiveInputDetector) HandleMessage(message Message, messageID uint64, timestamp uint64) *IssueEvent {
	switch msg := message.(type) {
	case *InputEvent:
		return rid.HandleInputEvent(msg, messageID, timestamp)
	case *SetPageLocation:
		if msg.NavigationStart != 0 {
			rid.HandleSetPageLocation(msg)
		}
	}
	return nil
}

func (rid *repetitiveInputDetector) HandleInputEvent(msg *InputEvent, messageID uint64, timestamp uint64) *IssueEvent {
	// Check if the input is already in cache
	for i, value := range rid.lastInputs {
		if value == msg.Value {

			// Update cache
			rid.lastInputs = append(rid.lastInputs[:i], rid.lastInputs[i+1:]...)
			rid.lastInputs = append(rid.lastInputs, msg.Value)

			// Build an issue
			return &IssueEvent{
				MessageID:     messageID,
				Timestamp:     timestamp,
				Type:          "repetitive_input",
				Payload:       "",
				Context:       rid.currentPage,
				ContextString: "The same input has recently been typed in"}
		}
	}

	// Append a message value to cache
	rid.lastInputs = append(rid.lastInputs, msg.Value)

	// Discard last element from the queue
	if len(rid.lastInputs) >= MAX_HISTORY_OF_INPUTS {
		rid.lastInputs = rid.lastInputs[:len(rid.lastInputs)-1]
	}
	return nil
}

func (rid *repetitiveInputDetector) HandleSetPageLocation(msg *SetPageLocation) {
	rid.currentPage = msg.Referrer
}
