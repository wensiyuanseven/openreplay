package builder

import (
	"log"

	"openreplay/backend/pkg/intervals"
	. "openreplay/backend/pkg/messages"
)

type builder struct {
	readyMsgs           []Message
	timestamp           uint64
	integrationsWaiting bool
	sid                 uint64
}

func NewBuilder() *builder {
	return &builder{
		integrationsWaiting: true,
	}
}

func (b *builder) appendReadyMessage(msg Message) { // interface is never nil even if it holds nil value
	b.readyMsgs = append(b.readyMsgs, msg)
}

func (b *builder) iterateReadyMessage(iter func(msg Message)) {
	for _, readyMsg := range b.readyMsgs {
		iter(readyMsg)
	}
	b.readyMsgs = nil
}

func (b *builder) buildSessionEnd() {
	sessionEnd := &SessionEnd{
		Timestamp: b.timestamp, // + delay?
	}
	b.appendReadyMessage(sessionEnd)
}

func (b *builder) handleMessage(message Message, messageID uint64) {
	switch msg := message.(type) {
	case *SessionDisconnect:
		b.timestamp = msg.Timestamp
	case *SessionStart:
		b.timestamp = msg.Timestamp
	case *Timestamp:
		b.timestamp = msg.Timestamp
	}
	// Start from the first timestamp event.
	if b.timestamp == 0 {
		return
	}
}

func (b *builder) checkTimeouts(ts int64) bool {
	if b.timestamp == 0 {
		return false // There was no timestamp events yet
	}

	lastTsGap := ts - int64(b.timestamp)
	log.Printf("checking timeouts for sess %v: %v now, %v sesstime; gap %v", b.sid, ts, b.timestamp, lastTsGap)
	if lastTsGap > intervals.EVENTS_SESSION_END_TIMEOUT {
		b.buildSessionEnd()
		return true
	}
	return false
}
