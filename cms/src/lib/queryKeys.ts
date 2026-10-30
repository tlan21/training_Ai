import type { paths } from "../api-types";
export const qk = {
  videos: (f: NonNullable<paths["/api/cms/videos"]["get"]["parameters"]["query"]>) => ["videos", f] as const,
  video: (id: string) => ["video", id] as const,
  analysis: (id: string) => ["analysis", id] as const,
  subtitles: (id: string) => ["subtitles", id] as const,
  jobs: (f: NonNullable<paths["/api/cms/jobs"]["get"]["parameters"]["query"]>) => ["jobs", f] as const,
  job: (id: string) => ["job", id] as const,
  clips: (f: NonNullable<paths["/api/cms/clips"]["get"]["parameters"]["query"]>) => ["clips", f] as const,
  categories: () => ["categories"] as const,
  users: (p: { page: number; q?: string }) => ["users", p] as const,
  health: () => ["health"] as const,
  settings: () => ["settings"] as const,
};
