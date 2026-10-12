package pg

// ponytail: stub pool — pgx wiring when T2.1.4 needs real DB, currently uses mocks
type Pool struct{ DSN string }

func New(dsn string) *Pool { return &Pool{DSN: dsn} }
