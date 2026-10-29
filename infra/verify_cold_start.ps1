# User-approved cold start: preserve containers/images/volumes and the external AI process.
$ErrorActionPreference='Stop'
Set-Location E:/traning_ai-codex
$docker='/mnt/host/wsl/docker-desktop/cli-tools/usr/bin/docker'
$compose='/mnt/host/wsl/docker-desktop/cli-tools/usr/local/lib/docker/cli-plugins/docker-compose'
$socket='unix:///proc/193/root/run/docker.raw.sock'
$priorKey=$env:AI_SERVICE_KEY; $priorTag=$env:APP_IMAGE_TAG; $priorWSL=$env:WSLENV
$stopped=$false; $verified=$false
function Invoke-Compose([string[]]$Arguments) {
    & wsl -d docker-desktop --exec env "DOCKER_HOST=$socket" $compose -p video-ai --project-directory /mnt/host/e/traning_ai-codex -f /mnt/host/e/traning_ai-codex/docker-compose.yml @Arguments
}
function Inspect-Container([string]$Name) {
    $raw=& wsl -d docker-desktop --exec $docker -H $socket inspect $Name
    if($LASTEXITCODE -ne 0){throw "Inspect failed: $Name"}
    return ($raw|ConvertFrom-Json)[0]
}
function Snapshot([string[]]$Services) {
    foreach($service in $Services){
        $c=Inspect-Container "video-ai-$service-1"
        [ordered]@{service=$service;id=$c.Id;image=$c.Config.Image;status=$c.State.Status;health=$c.State.Health.Status;exit_code=$c.State.ExitCode;started=$c.State.StartedAt;restart=$c.HostConfig.RestartPolicy.Name;volumes=@($c.Mounts|Sort-Object Type,Destination,Name|Select-Object Type,Name,Destination,RW)}
    }
}
function Data-Fingerprint {
    $value=& wsl -d docker-desktop --exec $docker -H $socket exec video-ai-postgres-1 psql -X -U app -d video_ai -At -c "select 'videos',count(*),md5(coalesce(string_agg(jsonb_strip_nulls(to_jsonb(v))::text,E'\n' order by id),'')) from videos v; select 'categories',count(*),md5(coalesce(string_agg(jsonb_strip_nulls(to_jsonb(c))::text,E'\n' order by id),'')) from categories c;"
    if($LASTEXITCODE -ne 0){throw 'Data fingerprint query failed'}
    return @($value)
}
try {
    $gateway=Inspect-Container 'video-ai-gateway-1'
    $currentEnv=@{}; foreach($entry in $gateway.Config.Env){$pair=$entry.Split('=',2);$currentEnv[$pair[0]]=$pair[1]}
    $line=[IO.File]::ReadLines('E:/traning_ai/inference-service/.env')|Where-Object {$_ -match '^\s*AI_SERVICE_KEY\s*='}|Select-Object -First 1
    $key=($line -split '=',2)[1].Trim().Trim([char]34).Trim([char]39)
    if(-not $key -or $key -cne $currentEnv.AI_SERVICE_KEY){throw 'Canonical AI key mismatch; no stop'}
    if($currentEnv.AI_BASE_URL -ne 'http://host.docker.internal:8001' -or $currentEnv.AI_ALLOW_STUB -ne '0'){throw 'Wrong AI runtime; no stop'}
    $env:AI_SERVICE_KEY=$key; $env:APP_IMAGE_TAG='latest'; $env:WSLENV='AI_SERVICE_KEY:APP_IMAGE_TAG'
    $raw=Invoke-Compose @('config','--format','json');if($LASTEXITCODE -ne 0){throw 'Compose validation failed'}
    $config=$raw|ConvertFrom-Json
    $services=@($config.services.PSObject.Properties|Where-Object {-not $_.Value.profiles}|Select-Object -ExpandProperty Name)
    if($services.Count -ne 12 -or 'gateway' -notin $services -or $config.services.gateway.depends_on.postgres.condition -ne 'service_healthy'){throw 'Unexpected cold-start scope/dependency'}
    foreach($service in $services){
        $c=Inspect-Container "video-ai-$service-1"
        $configuredImage=& wsl -d docker-desktop --exec $docker -H $socket image inspect --format '{{.Id}}' $config.services.$service.image
        if($LASTEXITCODE -ne 0 -or $c.Image -cne $configuredImage){throw "Image mismatch: $service"}
        $values=@{};foreach($entry in $c.Config.Env){$pair=$entry.Split('=',2);$values[$pair[0]]=$pair[1]}
        foreach($entry in $config.services.$service.environment.PSObject.Properties){
            if(-not $values.ContainsKey($entry.Name) -or [string]$entry.Value -cne $values[$entry.Name]){throw "Environment mismatch: $service/$($entry.Name)"}
        }
    }
    $active=& wsl -d docker-desktop --exec $docker -H $socket exec video-ai-postgres-1 psql -X -U app -d video_ai -At -c "select count(*) from video_processing_jobs where status not in ('completed','failed','cancelled');"
    if($LASTEXITCODE -ne 0 -or [int]$active -ne 0){throw 'Processing active/query failed; no stop'}
    $aiPids=@(Get-NetTCPConnection -State Listen -LocalPort 8001|Select-Object -ExpandProperty OwningProcess -Unique)
    $containerNames=@(& wsl -d docker-desktop --exec $docker -H $socket ps -a --format '{{.Names}}')
    if($LASTEXITCODE -ne 0){throw 'Cannot inventory optional outsider containers'}
    $outsiders=@('video-ai-ai-mock-1','video-ai-inference-service-1','faktory_server')|Where-Object {$_ -in $containerNames}|ForEach-Object {$c=Inspect-Container $_;@{name=$_;id=$c.Id;status=$c.State.Status;started=$c.State.StartedAt}}
    $before=@(Snapshot $services);$fingerprint=Data-Fingerprint
    [ordered]@{checked_at=[DateTime]::UtcNow.ToString('o');services=$before;ai_pids=$aiPids;untouched=$outsiders;data=$fingerprint;gateway_dependencies=$config.services.gateway.depends_on}|ConvertTo-Json -Depth 8|Set-Content coordination/codex/verification/INT-27-before.json
    $stopped=$true
    Invoke-Compose (@('stop','--timeout','60')+$services);if($LASTEXITCODE -ne 0){throw 'Compose stop failed'}
    $down=@(Snapshot $services);$down|ConvertTo-Json -Depth 6|Set-Content coordination/codex/verification/INT-27-stopped.json
    if(@($down|Where-Object status -ne 'exited').Count -gt 0){throw 'Owned services not fully stopped'}
    Write-Output 'ALL_12_DEFAULT_COMPOSE_SERVICES_STOPPED_NO_VOLUME_REMOVAL'
    $timer=[Diagnostics.Stopwatch]::StartNew()
    Invoke-Compose @('up','-d','--no-build','--no-recreate','--pull','never');if($LASTEXITCODE -ne 0){throw 'Compose up failed'}
    do {
        $after=@(Snapshot $services)
        $pending=@($after|Where-Object {if($_.service -eq 'kafka-init'){$_.status -ne 'exited' -or $_.exit_code -ne 0}else{$_.status -ne 'running' -or ($_.health -and $_.health -ne 'healthy')}})
        if($pending.Count -eq 0){break}
        Write-Output "Waiting for healthy: $($pending.service -join ',')"
        Start-Sleep -Seconds 3
    } while($timer.Elapsed.TotalSeconds -lt 240)
    if($pending.Count -gt 0){throw 'Cold startup readiness deadline exceeded'}
    foreach($previous in $before){
        $now=$after|Where-Object service -eq $previous.service
        if($now.id -cne $previous.id -or ($now.volumes|ConvertTo-Json -Compress) -cne ($previous.volumes|ConvertTo-Json -Compress)){throw "Container/volume changed: $($previous.service)"}
    }
    foreach($previous in $outsiders){$now=Inspect-Container $previous.name;if($now.Id -cne $previous.id -or $now.State.StartedAt -cne $previous.started -or $now.State.Status -cne $previous.status){throw "Out-of-scope container changed: $($previous.name)"}}
    $nowPids=@(Get-NetTCPConnection -State Listen -LocalPort 8001|Select-Object -ExpandProperty OwningProcess -Unique)
    if(($nowPids -join ',') -cne ($aiPids -join ',')){throw 'AI PID changed externally'}
    $currentData=Data-Fingerprint;if(($fingerprint -join "`n") -cne ($currentData -join "`n")){throw 'Persistent data fingerprint changed'}
    $health=Invoke-RestMethod http://127.0.0.1:8001/health -TimeoutSec 10
    if($health.stub_mode -or $health.models_loaded.Count -ne 6 -or @($health.degraded).Count -gt 0){throw 'AI health failed after dependency recovery'}
    [ordered]@{verified_at=[DateTime]::UtcNow.ToString('o');elapsed_seconds=[math]::Round($timer.Elapsed.TotalSeconds,2);services=$after;ai_pids=$nowPids;ai_health=$health;data=$currentData;container_ids_preserved=$true;named_volumes_preserved=$true;outsiders_unchanged=$true;gateway=(Invoke-RestMethod http://127.0.0.1:8000/healthz);cms_http=(Invoke-WebRequest http://127.0.0.1:5173/ -TimeoutSec 10).StatusCode;client_http=(Invoke-WebRequest http://127.0.0.1:3000/login -TimeoutSec 10).StatusCode}|ConvertTo-Json -Depth 8|Set-Content coordination/codex/verification/INT-27-after.json
    $verified=$true
    Write-Output 'COLD_COMPOSE_START_VERIFIED_NO_MANUAL_GATEWAY_START'
} finally {
    if($stopped -and -not $verified){Write-Output 'Restoring approved default stack with Compose up';Invoke-Compose @('up','-d','--no-build','--no-recreate','--pull','never')}
    $env:AI_SERVICE_KEY=$priorKey;$env:APP_IMAGE_TAG=$priorTag;$env:WSLENV=$priorWSL
}
