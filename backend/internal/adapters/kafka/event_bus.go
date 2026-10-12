package kafka

// ponytail: stub — kafka-go Reader/Writer wiring when T2.1.7 needs real bus
type Bus struct{ Brokers string }

func New(brokers string) *Bus { return &Bus{Brokers: brokers} }
