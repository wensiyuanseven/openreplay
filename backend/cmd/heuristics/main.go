// 功能: 启发式算法服务的入口点，可能用于数据分析、预测或实时决策。
// 注意点: 需要确保算法的准确性和效率，处理好算法的边界情况和异常输入。
// 确保服务的高可用性和低延迟，尤其是在实时数据分析场景中。
// 难点: 实现复杂的算法优化和性能调优。确保算法在大数据集上的高效性和扩展性，同时也要考虑内存和 CPU 使用。
package main

import (
	"context"
	config "openreplay/backend/internal/config/heuristics"
	"openreplay/backend/internal/heuristics"
	"openreplay/backend/pkg/builders"
	"openreplay/backend/pkg/handlers"
	"openreplay/backend/pkg/handlers/custom"
	"openreplay/backend/pkg/handlers/mobile"
	"openreplay/backend/pkg/handlers/web"
	"openreplay/backend/pkg/logger"
	"openreplay/backend/pkg/memory"
	"openreplay/backend/pkg/messages"
	"openreplay/backend/pkg/metrics"
	heuristicsMetrics "openreplay/backend/pkg/metrics/heuristics"
	"openreplay/backend/pkg/queue"
	"openreplay/backend/pkg/terminator"
)

func main() {
	ctx := context.Background()
	log := logger.New()
	cfg := config.New(log)
	metrics.New(log, heuristicsMetrics.List())

	// HandlersFabric returns the list of message handlers we want to be applied to each incoming message.
	handlersFabric := func() []handlers.MessageProcessor {
		return []handlers.MessageProcessor{
			custom.NewPageEventBuilder(),
			web.NewDeadClickDetector(),
			&web.ClickRageDetector{},
			&web.CpuIssueDetector{},
			&web.MemoryIssueDetector{},
			&web.NetworkIssueDetector{},
			&web.PerformanceAggregator{},
			web.NewAppCrashDetector(),
			&mobile.TapRageDetector{},
			mobile.NewViewComponentDurations(),
		}
	}

	eventBuilder := builders.NewBuilderMap(log, handlersFabric)
	producer := queue.NewProducer(cfg.MessageSizeLimit, true)
	consumer := queue.NewConsumer(
		cfg.GroupHeuristics,
		[]string{
			cfg.TopicRawWeb,
			cfg.TopicRawMobile,
		},
		messages.NewMessageIterator(log, eventBuilder.HandleMessage, nil, true),
		false,
		cfg.MessageSizeLimit,
	)

	// Init memory manager
	memoryManager, err := memory.NewManager(log, cfg.MemoryLimitMB, cfg.MaxMemoryUsage)
	if err != nil {
		log.Fatal(ctx, "can't init memory manager: %s", err)
		return
	}

	// Run service and wait for TERM signal
	service := heuristics.New(log, cfg, producer, consumer, eventBuilder, memoryManager)
	log.Info(ctx, "Heuristics service started")
	terminator.Wait(log, service)
}
