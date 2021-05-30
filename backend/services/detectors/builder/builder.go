package builder

import (
	"log"
	"openreplay/backend/pkg/intervals"
	. "openreplay/backend/pkg/messages"
)

type ReducedHandler struct {
	handlers []handler
}

func (rh *ReducedHandler) HandleMessage(msg Message) []Message {
	var resultMessages []Message
	for _, h := range rh.handlers {
		resultMessages = append(resultMessages, h.HandleMessage(msg)...)
	}
	return resultMessages
}

//-------------------------------------------------------------------------

type CombinedHandler struct {
	handlers []handler
}

func (ch *CombinedHandler) HandleMessage(msg Message) []Message {
	resultMessages := []Message{msg}
	for _, h := range ch.handlers {
		var nextResultMessages []Message
		for _, m := resultMessages {
			nextResultMessages = append(nextResultMessages, h.HandleMessage(m)...)
		}
		resultMessages = nextResultMessages
	}
	return resultMessages
}

type builder struct {
	readyMessages       []Message // a collection of built events
	timestamp           uint64    // current timestamp
	peBuilder           *pageEventBuilder
	ptaBuilder          *performanceTrackAggrBuilder
	ieBuilder           *inputEventBuilder
	reBuilder           *resourceEventBuilder
	ciDetector          *cpuIssueDetector
	miDetector          *memoryIssueDetector
	ddDetector          *domDropDetector
	crDetector          *clickRageDetector
	crshDetector        *crashDetector
	dcDetector          *deadClickDetector
	qrdetector          *quickReturnDetector
	ridetector          *repetitiveInputDetector
	exsdetector         *excessiveScrollingDetector
	chdetector          *clickHesitationDetector
	integrationsWaiting bool
	sid                 uint64
	sessionEventsCache  []*IssueEvent // a cache of selected ready messages used to detect events that depend on other events
}

func NewBuilder() *builder {
	return &builder{
		peBuilder:           &pageEventBuilder{},
		ptaBuilder:          &performanceTrackAggrBuilder{},
		ieBuilder:           NewInputEventBuilder(),
		reBuilder:           &resourceEventBuilder{},
		ciDetector:          &cpuIssueDetector{},
		miDetector:          &memoryIssueDetector{},
		ddDetector:          &domDropDetector{},
		crDetector:          &clickRageDetector{},
		crshDetector:        &crashDetector{},
		dcDetector:          &deadClickDetector{},
		qrdetector:          &quickReturnDetector{},
		ridetector:          &repetitiveInputDetector{},
		exsdetector:         &excessiveScrollingDetector{},
		chdetector:          &clickHesitationDetector{},
		integrationsWaiting: true,
	}
}

// Additional methods for builder
func (b *builder) appendReadyMessage(msg Message) { // interface is never nil even if it holds nil value
	b.readyMessages = append(b.readyMessages, msg)
}
func (b *builder) appendSessionEvent(msg *IssueEvent) { // interface is never nil even if it holds nil value
	b.sessionEventsCache = append(b.sessionEventsCache, msg)
}

func (b *builder) iterateReadyMessage(iter func(msg Message)) {
	for _, readyMsg := range b.readyMessages {
		iter(readyMsg)
	}
	b.readyMessages = nil
}

func (b *builder) buildSessionEnd() {
	sessionEnd := &SessionEnd{
		Timestamp: b.timestamp, // + delay?
	}
	b.appendReadyMessage(sessionEnd)
}

// ==================== DETECTORS ====================

func (b *builder) detectCpuIssue(msg Message, messageID uint64) {
	//	handle message and append to ready messages if it's fully composed
	if rm := b.ciDetector.HandleMessage(msg, messageID, b.timestamp); rm != nil {
		b.appendReadyMessage(rm)
	}
}

func (b *builder) detectMemoryIssue(msg Message, messageID uint64) {
	//	handle message and append to ready messages if it's fully composed
	if rm := b.miDetector.HandleMessage(msg, messageID, b.timestamp); rm != nil {
		b.appendReadyMessage(rm)
	}
}

func (b *builder) detectDomDrop(msg Message) {
	//	handle message and append to ready messages if it's fully composed
	if dd := b.ddDetector.HandleMessage(msg, b.timestamp); dd != nil {
		b.appendSessionEvent(dd) // not to ready messages, since we don't put it as anomaly
	}
}

func (b *builder) detectDeadClick(msg Message, messageID uint64) {
	if rm := b.dcDetector.HandleMessage(msg, messageID, b.timestamp); rm != nil {
		b.appendReadyMessage(rm)
	}
}
func (b *builder) detectQuickReturn(msg Message, messageID uint64) {
	if rm := b.qrdetector.HandleMessage(msg, messageID, b.timestamp); rm != nil {
		b.appendReadyMessage(rm)
	}
}
func (b *builder) detectClickHesitation(msg Message, messageID uint64) {
	if rm := b.chdetector.HandleMessage(msg, messageID, b.timestamp); rm != nil {
		b.appendReadyMessage(rm)
	}
}
func (b *builder) detectRepetitiveInput(msg Message, messageID uint64) {
	if rm := b.ridetector.HandleMessage(msg, messageID, b.timestamp); rm != nil {
		b.appendReadyMessage(rm)
	}
}
func (b *builder) detectExcessiveScrolling(msg Message, messageID uint64) {
	if rm := b.exsdetector.HandleMessage(msg, messageID, b.timestamp); rm != nil {
		b.appendReadyMessage(rm)
	}
}

// ==================== BUILDERS ====================

func (b *builder) handlePerformanceTrackAggr(message Message, messageID uint64) {
	if msg := b.ptaBuilder.HandleMessage(message, messageID, b.timestamp); msg != nil {
		b.appendReadyMessage(msg)
	}
}
func (b *builder) buildPerformanceTrackAggr() {
	if msg := b.ptaBuilder.Build(); msg != nil {
		b.appendReadyMessage(msg)
	}
}

func (b *builder) handleInputEvent(message Message, messageID uint64) {
	if msg := b.ieBuilder.HandleMessage(message, messageID, b.timestamp); msg != nil {
		b.appendReadyMessage(msg)
	}
}
func (b *builder) buildInputEvent() {
	if msg := b.ieBuilder.Build(); msg != nil {
		b.appendReadyMessage(msg)
	}
}

func (b *builder) handlePageEvent(message Message, messageID uint64) {
	if msg := b.peBuilder.HandleMessage(message, messageID, b.timestamp); msg != nil {
		b.appendReadyMessage(msg)
	}
}
func (b *builder) buildPageEvent() {
	if msg := b.peBuilder.Build(); msg != nil {
		b.appendReadyMessage(msg)
	}
}

func (b *builder) handleResourceEvent(message Message, messageID uint64) {
	if msg := b.reBuilder.HandleMessage(message, messageID); msg != nil {
		b.appendReadyMessage(msg)
	}
}

func (b *builder) handleMessage(message Message, messageID uint64) {

	// update current timestamp
	switch msg := message.(type) {
	//case *SessionDisconnect:
	//	b.timestamp = msg.Timestamp
	case *SessionStart:
		b.timestamp = msg.Timestamp
	case *Timestamp:
		b.timestamp = msg.Timestamp
	}
	// Start only from the first timestamp event.
	if b.timestamp == 0 {
		return
	}

	// Pass message to detector handlers
	b.detectCpuIssue(message, messageID)
	b.detectMemoryIssue(message, messageID)
	b.detectDomDrop(message)
	b.detectDeadClick(message, messageID)
	b.detectQuickReturn(message, messageID)
	b.detectClickHesitation(message, messageID)
	b.detectRepetitiveInput(message, messageID)
	b.detectExcessiveScrolling(message, messageID)

	// Pass message to eventBuilders handler
	b.handleInputEvent(message, messageID)
	b.handlePageEvent(message, messageID)
	b.handlePerformanceTrackAggr(message, messageID)
	b.handleResourceEvent(message, messageID)

	// Handle messages which translate to events without additional operations
	b.HandleSimpleMessages(message, messageID)
}

func (b *builder) buildEvents(ts int64) {
	if b.timestamp == 0 {
		return // There was no timestamp events yet
	}

	if b.peBuilder.HasInstance() && int64(b.peBuilder.GetTimestamp())+intervals.EVENTS_PAGE_EVENT_TIMEOUT < ts {
		b.buildPageEvent()
	}
	if b.ieBuilder.HasInstance() && int64(b.ieBuilder.GetTimestamp())+intervals.EVENTS_INPUT_EVENT_TIMEOUT < ts {
		b.buildInputEvent()
	}
	if b.ptaBuilder.HasInstance() && int64(b.ptaBuilder.GetStartTimestamp())+intervals.EVENTS_PERFORMANCE_AGGREGATION_TIMEOUT < ts {
		b.buildPerformanceTrackAggr()
	}
}

func (b *builder) checkTimeouts(ts int64) bool {
	if b.timestamp == 0 {
		return false // There was no timestamp events yet
	}
	lastTsGap := ts - int64(b.timestamp)
	log.Printf("checking timeouts for sess %v: %v now, %v sesstime; gap %v", b.sid, ts, b.timestamp, lastTsGap)
	if lastTsGap > intervals.EVENTS_SESSION_END_TIMEOUT {
		return true
	}
	return false
}
