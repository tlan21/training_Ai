export const qk = {
  videos: (f: { status?: string; page?: number }) => ["videos", f] as const,
  video: (id: string) => ["video", id] as const,
  analysis: (id: string) => ["analysis", id] as const,
  subtitles: (id: string) => ["subtitles", id] as const,
  jobs: (f: { status?: string }) => ["jobs", f] as const,
  job: (id: string) => ["job", id] as const,
  clips: (f: { video_id?: string; status?: string }) => ["clips", f] as const,
  categories: () => ["categories"] as const,
  users: (p: { page: number }) => ["users", p] as const,
  health: () => ["health"] as const,
  settings: () => ["settings"] as const,
};
