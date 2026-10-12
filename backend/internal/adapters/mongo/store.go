package mongo

// ponytail: stub — mongo wiring when T2.1.5 needs real DB
type Client struct{ URI, DB string }

func New(uri, db string) *Client { return &Client{URI: uri, DB: db} }
