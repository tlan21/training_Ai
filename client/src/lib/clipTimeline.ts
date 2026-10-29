import type { components } from "../api-types";
type Clip = components["schemas"]["Clip"];
type Source = components["schemas"]["ClipSourceSegment"];

export function clipSourceTime(clip: Clip, time: number): number {
    if (!clip.source_segments?.length) return time + (clip.start_time || 0);
    let offset = 0;
    for (const source of clip.source_segments) {
        const duration = source.end_time - source.start_time;
        if (time < offset + duration) return source.start_time + Math.max(0, time - offset);
        offset += duration;
    }
    return clip.source_segments[clip.source_segments.length - 1].end_time;
}

export function sourceClipTime(sources: Source[], time: number): number | null {
    let offset = 0;
    for (const source of sources) {
        if (time >= source.start_time && time < source.end_time) return offset + time - source.start_time;
        offset += source.end_time - source.start_time;
    }
    return null;
}

export function compilationSubtitles(segments: components["schemas"]["SubtitleSegment"][], sources: Source[]) {
    if (!sources.length) return segments;
    const result: components["schemas"]["SubtitleSegment"][] = [];
    let offset = 0;
    for (const source of sources) {
        for (const segment of segments) {
            const start = Math.max(source.start_time, segment.start_time || 0);
            const end = Math.min(source.end_time, segment.end_time || 0);
            if (end > start) result.push({ ...segment, segment_index: result.length, start_time: offset + start - source.start_time, end_time: offset + end - source.start_time });
        }
        offset += source.end_time - source.start_time;
    }
    return result;
}

export function compilationScores(scores: components["schemas"]["TimelineScore"][], sources: Source[]) {
    if (!sources.length) return scores;
    return scores.flatMap(score => {
        const second = sourceClipTime(sources, score.second ?? -1);
        return second === null ? [] : [{ ...score, second }];
    });
}
