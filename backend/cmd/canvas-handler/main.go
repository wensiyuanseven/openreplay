// 功能: 处理图形和画布操作的服务入口点，可能涉及图形渲染、用户输入处理等。
// 注意点: 确保画布操作的高性能和低延迟，尤其是在实时互动应用中。处理好不同图形格式和兼容性问题。
// 难点: 实现高效的图形渲染算法，尤其是当需要处理大量图形元素或复杂的用户交互时。还要注意内存管理和渲染性能。
package main

import (
	"context"
	"os"
	"os/signal"
	"syscall"
	"time"

	canvas_handler "openreplay/backend/internal/canvas-handler"
	config "openreplay/backend/internal/config/canvas-handler"
	"openreplay/backend/pkg/logger"
	"openreplay/backend/pkg/messages"
	"openreplay/backend/pkg/metrics"
	storageMetrics "openreplay/backend/pkg/metrics/imagestorage"
	"openreplay/backend/pkg/objectstorage/store"
	"openreplay/backend/pkg/queue"
)

func main() {
	ctx := context.Background()
	log := logger.New()
	cfg := config.New(log)
	metrics.New(log, storageMetrics.List())

	objStore, err := store.NewStore(&cfg.ObjectsConfig)
	if err != nil {
		log.Fatal(ctx, "can't init object storage: %s", err)
	}

	srv, err := canvas_handler.New(cfg, log, objStore)
	if err != nil {
		log.Fatal(ctx, "can't init canvas service: %s", err)
	}

	canvasConsumer := queue.NewConsumer(
		cfg.GroupCanvasImage,
		[]string{
			cfg.TopicCanvasImages,
		},
		messages.NewImagesMessageIterator(func(data []byte, sessID uint64) {
			isSessionEnd := func(data []byte) bool {
				reader := messages.NewBytesReader(data)
				msgType, err := reader.ReadUint()
				if err != nil {
					return false
				}
				if msgType != messages.MsgSessionEnd {
					return false
				}
				_, err = messages.ReadMessage(msgType, reader)
				if err != nil {
					return false
				}
				return true
			}
			sessCtx := context.WithValue(context.Background(), "sessionID", sessID)

			if isSessionEnd(data) {
				if err := srv.PackSessionCanvases(sessCtx, sessID); err != nil {
					log.Error(sessCtx, "can't pack session's canvases: %s", err)
				}
			} else {
				if err := srv.SaveCanvasToDisk(sessCtx, sessID, data); err != nil {
					log.Error(sessCtx, "can't process canvas image: %s", err)
				}
			}
		}, nil, true),
		false,
		cfg.MessageSizeLimit,
	)

	log.Info(ctx, "canvas handler service started")

	sigchan := make(chan os.Signal, 1)
	signal.Notify(sigchan, syscall.SIGINT, syscall.SIGTERM)

	counterTick := time.Tick(time.Second * 30)
	for {
		select {
		case sig := <-sigchan:
			log.Info(ctx, "caught signal %v: terminating", sig)
			srv.Wait()
			canvasConsumer.Close()
			os.Exit(0)
		case <-counterTick:
			srv.Wait()
			if err := canvasConsumer.Commit(); err != nil {
				log.Error(ctx, "can't commit messages: %s", err)
			}
		case msg := <-canvasConsumer.Rebalanced():
			log.Info(ctx, "consumer group rebalanced: %+v", msg)
		default:
			err = canvasConsumer.ConsumeNext()
			if err != nil {
				log.Fatal(ctx, "can't consume next message: %s", err)
			}
		}
	}
}
