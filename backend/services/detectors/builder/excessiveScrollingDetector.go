package builder

import (
	. "openreplay/backend/pkg/messages"
)

const MAX_SCROLL_PER_PAGE = 20

type excessiveScrollingDetector struct {
	currentPage   string
	scrollsNumber uint64
}

func (exs *excessiveScrollingDetector) HandleMouseClick() {
	exs.scrollsNumber = 0
}

func (exs *excessiveScrollingDetector) HandleSetPageLocation(msg *SetPageLocation) {
	if msg.Referrer != exs.currentPage {
		exs.currentPage = msg.Referrer
		exs.scrollsNumber = 0
	}
}

func (exs *excessiveScrollingDetector) HandleScroll(msg *SetViewportScroll, messageID uint64, timestamp uint64) *IssueEvent {
	if exs.scrollsNumber+1 >= MAX_SCROLL_PER_PAGE {
		return &IssueEvent{
			MessageID:     messageID,
			Type:          "excessive_scrolling",
			Timestamp:     timestamp,
			ContextString: "Number of scrolling per page is above the threshold",
			Context:       exs.currentPage,
		}
	} else {
		exs.scrollsNumber += 1
		return nil
	}
}

func (exs *excessiveScrollingDetector) HandleMessage(message Message, messageID uint64, timestamp uint64) *IssueEvent {
	switch msg := message.(type) {
	case *MouseClick:
		exs.HandleMouseClick()
	case *SetPageLocation:
		if msg.NavigationStart != 0 {
			exs.HandleSetPageLocation(msg)
		}
	case *SetViewportScroll:
		return exs.HandleScroll(msg, messageID, timestamp)
	}
	return nil
}
