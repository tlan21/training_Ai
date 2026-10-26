# INT-02: real storage/ingest/cutter, HTTP mock AI. Never evidence of real AI quality.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$base = 'http://localhost:8000'
$mock = Invoke-RestMethod 'http://localhost:18001/health'
if (-not $mock.stub_mode) { throw 'This script requires the explicit mock stack' }
$admin = Invoke-RestMethod -Method Post "$base/api/auth/login" -ContentType 'application/json' -Body '{"email":"admin@local","password":"admin123"}'
$headers = @{ Authorization = "Bearer $($admin.access_token)" }
$settings = Invoke-RestMethod "$base/api/cms/settings" -Headers $headers
$threshold = if ($settings.highlight_threshold -eq 100) { 99 } else { $settings.highlight_threshold + 1 }
$videoId = $null
$settingsChanged = $false
$name = 'int02-mock-' + [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
$viewer = Invoke-RestMethod -Method Post "$base/api/auth/register" -ContentType 'application/json' -Body (@{username=$name;email="$name@example.test";password='E2e-test-123!'} | ConvertTo-Json)
$viewerHeaders = @{ Authorization = "Bearer $($viewer.access_token)" }

try {
    $upload = Invoke-RestMethod -Method Post "$base/api/cms/videos" -Headers $headers -Form @{file=Get-Item (Join-Path $PSScriptRoot 'fixtures/video.mp4');title="INT-02-MOCK_ONLY-$name"}
    $videoId = $upload.video.id
    for ($attempt=0; $attempt -lt 90; $attempt++) {
        $job = Invoke-RestMethod "$base/api/cms/jobs/$($upload.job.id)" -Headers $headers
        if ($job.status -eq 'completed') { break }
        if ($job.status -eq 'failed') { throw "Mock pipeline failed: $($job.error_log)" }
        Start-Sleep -Milliseconds 500
    }
    if ($job.status -ne 'completed') { throw 'Mock processing timed out' }
    Write-Host 'MOCK_ONLY upload/ingest/HTTP AI pipeline PASS'
    $clip = Invoke-RestMethod -Method Post "$base/api/cms/clips" -Headers $headers -ContentType 'application/json' -Body (@{video_id=$videoId;title=$name;start_time=0;end_time=3} | ConvertTo-Json)
    $watch = @{video_id=$videoId;clip_id=$clip.id;interaction_type='watch_time';duration_watched=2} | ConvertTo-Json
    $private = Invoke-WebRequest -Method Post "$base/api/interactions" -Headers $viewerHeaders -ContentType 'application/json' -Body $watch -SkipHttpErrorCheck
    if ($private.StatusCode -ne 404) { throw 'Unpublished interaction accepted' }
    for ($attempt=0; $attempt -lt 60; $attempt++) {
        $clips = Invoke-RestMethod "$base/api/cms/clips?video_id=$videoId" -Headers $headers
        if (($clips | Where-Object id -eq $clip.id).status -eq 'draft') { break }
        Start-Sleep -Milliseconds 500
    }
    Invoke-RestMethod -Method Post "$base/api/cms/clips/$($clip.id)/publish" -Headers $headers | Out-Null
    Invoke-RestMethod -Method Post "$base/api/interactions" -Headers $viewerHeaders -ContentType 'application/json' -Body $watch | Out-Null
    Invoke-RestMethod -Method Post "$base/api/interactions" -Headers $viewerHeaders -ContentType 'application/json' -Body (@{video_id=$videoId;clip_id=$clip.id;interaction_type='like'} | ConvertTo-Json) | Out-Null
    Invoke-RestMethod -Method Put "$base/api/cms/settings" -Headers $headers -ContentType 'application/json' -Body (@{highlight_threshold=$threshold} | ConvertTo-Json) | Out-Null
    $settingsChanged = $true

    & docker restart video-ai-gateway-1
    if ($LASTEXITCODE -ne 0) { throw 'Gateway restart failed' }
    $ready = $false
    for ($attempt=0; $attempt -lt 60; $attempt++) {
        try {
            if ((Invoke-RestMethod "$base/healthz" -TimeoutSec 2).status -eq 'ok') { $ready=$true; break }
        } catch {}
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) { throw 'Gateway did not recover' }
    $history = Invoke-RestMethod "$base/api/users/me/history" -Headers $viewerHeaders
    $likes = Invoke-RestMethod "$base/api/users/me/likes" -Headers $viewerHeaders
    $after = Invoke-RestMethod "$base/api/cms/settings" -Headers $headers
    if ($history.items.Count -ne 1 -or $history.items[0].clip.id -ne $clip.id -or $history.items[0].duration_watched -ne 2) { throw 'Watch history lost after restart' }
    if ($likes.items.Count -ne 1 -or $likes.items[0].id -ne $clip.id) { throw 'Likes lost after restart' }
    if ($after.highlight_threshold -ne $threshold -or $after.ai_service_api_key -ne 'sk-local-••••') { throw 'Settings lost or key exposed' }
    $feed = Invoke-RestMethod "$base/api/feed" -Headers $viewerHeaders
    if ($clip.id -notin $feed.items.id) { throw 'Popularity fallback failed with recommendation 503' }
    foreach ($url in @($history.items[0].clip.playback_url, $likes.items[0].playback_url)) {
        if (-not $url) { throw 'Playback URL missing' }
        $media = Invoke-WebRequest $url -Headers @{Range='bytes=0-1023'} -SkipHttpErrorCheck
        if ($media.StatusCode -ne 206) { throw 'Stored history/likes playback failed' }
    }
    Invoke-RestMethod -Method Delete "$base/api/cms/videos/$videoId" -Headers $headers | Out-Null
    $videoId = $null
    $hiddenHistory = Invoke-RestMethod "$base/api/users/me/history" -Headers $viewerHeaders
    $hiddenLikes = Invoke-RestMethod "$base/api/users/me/likes" -Headers $viewerHeaders
    if ($hiddenHistory.items.Count -ne 0 -or $hiddenLikes.items.Count -ne 0) { throw 'Deleted content leaked through history/likes' }
    $evidence = [ordered]@{mode='MOCK_ONLY';user_id=$viewer.user.id;clip_id=$clip.id;restart_verified=$true;history_count=$history.items.Count;duration_watched=$history.items[0].duration_watched;likes_count=$likes.items.Count;settings_persisted=$true;key_masked=$true;playback_range_status=206;unpublished_interaction_status=$private.StatusCode;deleted_content_hidden=$true;recommendation_fallback=$true}
    $evidence | ConvertTo-Json | Set-Content -Encoding utf8 coordination/codex/verification/INT-02-persistence.json
    $evidence | ConvertTo-Json
} finally {
    if ($settingsChanged) {
        $current = Invoke-RestMethod "$base/api/cms/settings" -Headers $headers
        if ($current.highlight_threshold -eq $threshold) {
            Invoke-RestMethod -Method Put "$base/api/cms/settings" -Headers $headers -ContentType 'application/json' -Body (@{highlight_threshold=$settings.highlight_threshold} | ConvertTo-Json) | Out-Null
        } else { Write-Warning 'Threshold changed by another caller; leaving their value intact' }
    }
    if ($videoId) { Invoke-RestMethod -Method Delete "$base/api/cms/videos/$videoId" -Headers $headers | Out-Null }
}
# Only this test's video is soft-deleted; its viewer and MinIO objects remain per existing E2E policy.
