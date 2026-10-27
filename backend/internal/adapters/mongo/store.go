package mongo

import (
	"context"
	"errors"
	"go.mongodb.org/mongo-driver/v2/bson"
	"go.mongodb.org/mongo-driver/v2/mongo"
	"go.mongodb.org/mongo-driver/v2/mongo/options"
	"go.mongodb.org/mongo-driver/v2/mongo/readpref"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/startup"
)

type AnalysisStore struct{ Collection *mongo.Collection }
type SubtitleStore struct{ Collection *mongo.Collection }

func New(ctx context.Context, uri, name string) (*mongo.Database, error) {
	client, err := mongo.Connect(options.Client().ApplyURI(uri))
	if err != nil {
		return nil, err
	}
	if err := startup.Wait(ctx, "MongoDB", func(probe context.Context) error { return client.Ping(probe, readpref.Primary()) }); err != nil {
		_ = client.Disconnect(ctx)
		return nil, err
	}
	db := client.Database(name)
	for _, collection := range []string{"video_analyses", "subtitles"} {
		_, err := db.Collection(collection).Indexes().CreateOne(ctx, mongo.IndexModel{Keys: bson.D{{Key: "video_id", Value: 1}}, Options: options.Index().SetUnique(true)})
		if err != nil {
			return nil, err
		}
	}
	// `language: vi` is transcript metadata, not a supported MongoDB stemmer name.
	indexes, err := db.Collection("subtitles").Indexes().List(ctx)
	if err != nil {
		return nil, err
	}
	var existing []struct {
		Name             string `bson:"name"`
		DefaultLanguage  string `bson:"default_language"`
		LanguageOverride string `bson:"language_override"`
	}
	if err := indexes.All(ctx, &existing); err != nil {
		return nil, err
	}
	for _, index := range existing {
		if index.Name == "segments.text_text" && (index.DefaultLanguage != "none" || index.LanguageOverride != "_text_language") {
			if err := db.Collection("subtitles").Indexes().DropOne(ctx, index.Name); err != nil {
				return nil, err
			}
		}
	}
	if _, err := db.Collection("subtitles").Indexes().CreateOne(ctx, mongo.IndexModel{Keys: bson.D{{Key: "segments.text", Value: "text"}}, Options: options.Index().SetDefaultLanguage("none").SetLanguageOverride("_text_language")}); err != nil {
		return nil, err
	}
	return db, nil
}
func missing(err error) error {
	if errors.Is(err, mongo.ErrNoDocuments) {
		return domain.ErrNotFound
	}
	return err
}
func videoFilter(id string) bson.M { return bson.M{"video_id": id} }

func (s *AnalysisStore) Put(ctx context.Context, id string, scores []domain.SecondScore, clips []domain.AIClip, category *string) error {
	_, err := s.Collection.UpdateOne(ctx, videoFilter(id), bson.M{"$set": bson.M{"timeline_scores": scores, "ai_generated_clips": clips, "category_suggestion": category}}, options.UpdateOne().SetUpsert(true))
	return err
}
func (s *AnalysisStore) Get(ctx context.Context, id string) (*domain.VideoAnalysis, error) {
	var result domain.VideoAnalysis
	err := s.Collection.FindOne(ctx, videoFilter(id)).Decode(&result)
	return &result, missing(err)
}
func (s *AnalysisStore) SetSummary(ctx context.Context, id, summary, status string) error {
	_, err := s.Collection.UpdateOne(ctx, videoFilter(id), bson.M{"$set": bson.M{"summary": summary, "summary_status": status}}, options.UpdateOne().SetUpsert(true))
	return err
}
func (s *AnalysisStore) Delete(ctx context.Context, id string) error {
	_, err := s.Collection.DeleteOne(ctx, videoFilter(id))
	return err
}

func (s *SubtitleStore) Put(ctx context.Context, id, language, transcript string, segments []domain.Segment) error {
	_, err := s.Collection.UpdateOne(ctx, videoFilter(id), bson.M{"$set": bson.M{"language": language, "full_transcript": transcript, "segments": segments}}, options.UpdateOne().SetUpsert(true))
	return err
}
func (s *SubtitleStore) Get(ctx context.Context, id string) (*domain.Subtitle, error) {
	var result domain.Subtitle
	err := s.Collection.FindOne(ctx, videoFilter(id)).Decode(&result)
	return &result, missing(err)
}
func (s *SubtitleStore) UpdateSegments(ctx context.Context, id string, segments []domain.Segment) error {
	result, err := s.Collection.UpdateOne(ctx, videoFilter(id), bson.M{"$set": bson.M{"segments": segments}})
	if err != nil {
		return err
	}
	if result.MatchedCount == 0 {
		return domain.ErrNotFound
	}
	return nil
}
func (s *SubtitleStore) TextSearch(ctx context.Context, q string) ([]domain.SubtitleMatch, error) {
	cursor, err := s.Collection.Find(ctx, bson.M{"$text": bson.M{"$search": q}})
	if err != nil {
		return nil, err
	}
	defer cursor.Close(ctx)
	var subtitles []domain.Subtitle
	if err := cursor.All(ctx, &subtitles); err != nil {
		return nil, err
	}
	items := []domain.SubtitleMatch{}
	for _, sub := range subtitles {
		for _, segment := range sub.Segments {
			items = append(items, domain.SubtitleMatch{VideoID: sub.VideoID, Timestamp: segment.StartTime, Text: segment.Text})
		}
	}
	return items, nil
}
func (s *SubtitleStore) Delete(ctx context.Context, id string) error {
	_, err := s.Collection.DeleteOne(ctx, videoFilter(id))
	return err
}
