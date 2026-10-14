package kafka

import (
	"context"
	"encoding/json"
	kafkasdk "github.com/segmentio/kafka-go"
	"log"
	"os"
	"strings"
	"time"
)

type Bus struct {
	brokers []string
	writer  *kafkasdk.Writer
}

func New(brokers string) *Bus {
	addresses := strings.Split(brokers, ",")
	return &Bus{brokers: addresses, writer: &kafkasdk.Writer{Addr: kafkasdk.TCP(addresses...), Balancer: &kafkasdk.Hash{}, RequiredAcks: kafkasdk.RequireAll, AllowAutoTopicCreation: true}}
}
func (b *Bus) Publish(ctx context.Context, topic, key string, payload any) error {
	data, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	return b.writer.WriteMessages(ctx, kafkasdk.Message{Topic: topic, Key: []byte(key), Value: data})
}
func (b *Bus) Consume(ctx context.Context, topic, groupID string, handler func(context.Context, []byte) error) error {
	reader := kafkasdk.NewReader(kafkasdk.ReaderConfig{Brokers: b.brokers, Topic: topic, GroupID: groupID, StartOffset: kafkasdk.FirstOffset, MinBytes: 1, MaxBytes: 10 * 1024 * 1024, WatchPartitionChanges: true, PartitionWatchInterval: 2 * time.Second, ErrorLogger: log.New(os.Stderr, "kafka: ", log.LstdFlags)})
	defer reader.Close()
	for {
		msg, err := reader.FetchMessage(ctx)
		if err != nil {
			return err
		}
		if err := handler(ctx, msg.Value); err != nil {
			return err
		}
		if err := reader.CommitMessages(ctx, msg); err != nil {
			return err
		}
	}
}
