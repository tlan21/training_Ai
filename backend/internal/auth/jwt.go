package auth

import (
	"time"

	"github.com/golang-jwt/jwt/v5"
)

type JWT struct{ secret []byte }

func NewJWT(secret string) *JWT { return &JWT{secret: []byte(secret)} }

type Claims struct {
	UserID string `json:"uid"`
	Role   string `json:"role"`
	jwt.RegisteredClaims
}

func (j *JWT) Sign(userID, role string, ttl time.Duration) (string, error) {
	now := time.Now()
	claims := Claims{
		UserID: userID,
		Role:   role,
		RegisteredClaims: jwt.RegisteredClaims{
			Subject:   userID,
			IssuedAt:  jwt.NewNumericDate(now),
			ExpiresAt: jwt.NewNumericDate(now.Add(ttl)),
		},
	}
	tok := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return tok.SignedString(j.secret)
}

func (j *JWT) Verify(token string) (*Claims, error) {
	claims := &Claims{}
	_, err := jwt.ParseWithClaims(token, claims, func(t *jwt.Token) (any, error) {
		return j.secret, nil
	})
	if err != nil {
		return nil, err
	}
	return claims, nil
}
