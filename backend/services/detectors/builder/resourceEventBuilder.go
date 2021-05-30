package builder

import (
	"net/url"
	"strings"
	. "openreplay/backend/pkg/messages"
)

type resourceEventBuilder struct {}

func (reb *resourceEventBuilder) HandleMessage(message Message, messageID uint64) *ResourceEvent{
	switch msg := message.(type) {
	case *ResourceTiming:
		tp := getResourceType(msg.Initiator, msg.URL)
		success := msg.Duration != 0
		return &ResourceEvent{
			MessageID:       messageID,
			Timestamp:       msg.Timestamp,
			Duration:        msg.Duration,
			TTFB:            msg.TTFB,
			HeaderSize:      msg.HeaderSize,
			EncodedBodySize: msg.EncodedBodySize,
			DecodedBodySize: msg.DecodedBodySize,
			URL:             msg.URL,
			Type:            tp,
			Success:         success,
		}
	}
	return nil
}

func getURLExtention(URL string) string {
	u, err := url.Parse(URL)
	if err != nil {
		return ""
	}
	i := strings.LastIndex(u.Path, ".")
	return u.Path[i+1:]
}

func getResourceType(initiator string, URL string) string {
	switch initiator {
	case "xmlhttprequest", "fetch":
		return "fetch"
	case "img":
		return "img"
	default:
		switch getURLExtention(URL) {
		case "css":
			return "stylesheet"
		case "js":
			return "script"
		case "png", "gif", "jpg", "jpeg", "svg":
			return "img"
		case "mp4", "mkv", "ogg", "webm", "avi", "mp3":
			return "media"
		default:
			return "other"
		}
	}
}
