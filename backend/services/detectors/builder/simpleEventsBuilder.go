package builder

import (
	. "openreplay/backend/pkg/messages"
)

func (b *builder) HandleSimpleMessages(message Message, messageID uint64) {
	switch msg := message.(type) {
	case *MouseClick:
		if msg.Label != "" {
			b.appendReadyMessage(&ClickEvent{
				MessageID:      messageID,
				Label:          msg.Label,
				HesitationTime: msg.HesitationTime,
				Timestamp:      b.timestamp,
			})
		}
	case *RawErrorEvent:
		b.appendReadyMessage(&ErrorEvent{
			MessageID: messageID,
			Timestamp: msg.Timestamp,
			Source:    msg.Source,
			Name:      msg.Name,
			Message:   msg.Message,
			Payload:   msg.Payload,
		})
	case *JSException:
		b.appendReadyMessage(&ErrorEvent{
			MessageID: messageID,
			Timestamp: b.timestamp,
			Source:    "js_exception",
			Name:      msg.Name,
			Message:   msg.Message,
			Payload:   msg.Payload,
		})
	case *ResourceTiming:
		success := msg.Duration != 0
		tp := getResourceType(msg.Initiator, msg.URL)
		if !success && tp == "fetch" {
			b.appendReadyMessage(&IssueEvent{
				Type:          "bad_request",
				MessageID:     messageID,
				Timestamp:     msg.Timestamp,
				ContextString: msg.URL,
				Context:       "",
				Payload:       "",
			})
		}
	case *RawCustomEvent:
		b.appendReadyMessage(&CustomEvent{
			MessageID: messageID,
			Timestamp: b.timestamp,
			Name:      msg.Name,
			Payload:   msg.Payload,
		})
	case *CustomIssue:
		b.appendReadyMessage(&IssueEvent{
			Type:          "custom",
			Timestamp:     b.timestamp,
			MessageID:     messageID,
			ContextString: msg.Name,
			Payload:       msg.Payload,
		})
	case *Fetch:
		b.appendReadyMessage(&ResourceEvent{
			MessageID: messageID,
			Timestamp: msg.Timestamp,
			Duration:  msg.Duration,
			URL:       msg.URL,
			Type:      "fetch",
			Success:   msg.Status < 300,
			Method:    msg.Method,
			Status:    msg.Status,
		})
	case *StateAction:
		b.appendReadyMessage(&StateActionEvent{
			MessageID: messageID,
			Timestamp: b.timestamp,
			Type:      msg.Type,
		})
	case *GraphQL:
		b.appendReadyMessage(&GraphQLEvent{
			MessageID: messageID,
			Timestamp: b.timestamp,
			Name:      msg.OperationName,
		})
	}

}
