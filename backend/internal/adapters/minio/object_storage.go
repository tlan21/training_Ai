package minio

// ponytail: stub — minio-go wiring when T2.1.7 needs real storage
type Client struct{ Endpoint, Access, Secret string }

func New(endpoint, access, secret string) *Client { return &Client{Endpoint: endpoint, Access: access, Secret: secret} }
