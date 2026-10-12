package milvus

// ponytail: stub — milvus-sdk wiring when T2.1.6 needs real store
type Client struct{ Host, Port string }

func New(host, port string) *Client { return &Client{Host: host, Port: port} }
