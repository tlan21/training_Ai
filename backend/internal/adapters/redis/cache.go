package redis

// ponytail: stub — go-redis wiring when T2.1.7 needs real cache
type Client struct{ Addr string }

func New(addr string) *Client { return &Client{Addr: addr} }
