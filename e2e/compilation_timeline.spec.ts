import { test, expect } from '@playwright/test';
import { clipSourceTime, sourceClipTime, compilationSubtitles, compilationScores } from '../client/src/lib/clipTimeline';

test('compilation playback maps across removed gaps and keeps legacy offsets', () => {
  const source_segments = [{ start_time: 10, end_time: 12 }, { start_time: 40, end_time: 43 }];
  expect(clipSourceTime({ source_segments }, 1.5)).toBe(11.5);
  expect(clipSourceTime({ source_segments }, 2)).toBe(40);
  expect(clipSourceTime({ source_segments }, 4)).toBe(42);
  expect(clipSourceTime({ start_time: 10 }, 1.5)).toBe(11.5);
  expect(sourceClipTime(source_segments, 41)).toBe(3);
  expect(sourceClipTime(source_segments, 20)).toBeNull();
  expect(compilationScores([{ second: 11, score: 80 }, { second: 30, score: 99 }, { second: 41, score: 90 }], source_segments)).toEqual([{ second: 1, score: 80 }, { second: 3, score: 90 }]);
  const subtitles = compilationSubtitles([{ start_time: 9, end_time: 11, text: 'one' }, { start_time: 20, end_time: 22, text: 'removed' }, { start_time: 41, end_time: 45, text: 'two' }], source_segments);
  expect(subtitles).toEqual([{ segment_index: 0, start_time: 0, end_time: 1, text: 'one' }, { segment_index: 1, start_time: 3, end_time: 5, text: 'two' }]);
  expect(compilationSubtitles(subtitles, [])).toBe(subtitles);
});
