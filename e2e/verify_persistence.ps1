$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)

$login = Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/api/auth/login' -ContentType 'application/json' -Body '{"email":"admin@local","password":"admin123"}'
$headers = @{ Authorization = ('Bearer ' + $login.access_token) }
$fixture = Join-Path $PSScriptRoot 'fixtures\video.mp4'
$uploadJson = & curl.exe --silent --show-error --fail -H ('Authorization: Bearer ' + $login.access_token) -F ('file=@' + $fixture) -F 'title=T4.1-REAL-AI-SMOKE' 'http://localhost:8000/api/cms/videos'
if ($LASTEXITCODE -ne 0) { throw 'Upload failed' }
$upload = $uploadJson | ConvertFrom-Json
$videoId = $upload.video.id
$jobId = $upload.job.id

for ($attempt = 0; $attempt -lt 90; $attempt++) {
    $job = Invoke-RestMethod -Uri "http://localhost:8000/api/cms/jobs/$jobId" -Headers $headers
    if ($job.status -eq 'completed') { break }
    if ($job.status -eq 'failed') { throw $job.error_log }
    Start-Sleep -Seconds 1
}
if ($job.status -ne 'completed') { throw 'Processing timed out' }
$before = Invoke-RestMethod -Uri "http://localhost:8000/api/cms/videos/$videoId/analysis" -Headers $headers
$beforeSubtitles = Invoke-RestMethod -Uri "http://localhost:8000/api/videos/$videoId/subtitles" -Headers $headers
if ($before.timeline_scores.Count -ne 8 -or $before.summary_status -ne 'draft') { throw 'Real analysis missing' }

& docker compose --env-file .env -f docker-compose.yml restart gateway
if ($LASTEXITCODE -ne 0) { throw 'Gateway restart failed' }
$ready = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri 'http://localhost:8000/healthz' -TimeoutSec 2
        if ($health.status -eq 'ok') { $ready = $true; break }
    } catch {}
    Start-Sleep -Seconds 1
}
if (-not $ready) { throw 'Gateway did not recover' }
$video = Invoke-RestMethod -Uri "http://localhost:8000/api/cms/videos/$videoId" -Headers $headers
$after = Invoke-RestMethod -Uri "http://localhost:8000/api/cms/videos/$videoId/analysis" -Headers $headers
$afterSubtitles = Invoke-RestMethod -Uri "http://localhost:8000/api/videos/$videoId/subtitles" -Headers $headers
if ($video.status -ne 'processed' -or $after.summary -ne $before.summary) { throw 'Video/summary lost after restart' }
if (($after.timeline_scores | ConvertTo-Json -Compress) -ne ($before.timeline_scores | ConvertTo-Json -Compress)) { throw 'Timeline lost after restart' }
if (($afterSubtitles | ConvertTo-Json -Depth 10 -Compress) -ne ($beforeSubtitles | ConvertTo-Json -Depth 10 -Compress)) { throw 'Subtitles lost after restart' }
$cmsJob = Invoke-RestMethod -Uri "http://localhost:5173/api/cms/jobs/$jobId" -Headers $headers
if ($cmsJob.status -ne 'completed') { throw 'CMS proxy/job did not survive gateway restart' }
$evidence = @{ video_id = $videoId; job_id = $jobId; status = $video.status; duration_seconds = $video.duration_seconds; category_suggestion = $after.category_suggestion; summary = $after.summary; timeline_count = $after.timeline_scores.Count; segments_count = $afterSubtitles.segments.Count; restart_verified = $true }
New-Item -ItemType Directory -Path test-results -Force | Out-Null
$evidence | ConvertTo-Json -Depth 10 | Set-Content -Encoding utf8 test-results/persistence-smoke.json
$evidence | ConvertTo-Json -Depth 10
# Keep this clearly named synthetic sample so the user can inspect the real draft in CMS.
