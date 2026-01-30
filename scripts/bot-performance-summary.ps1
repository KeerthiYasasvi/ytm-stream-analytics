param(
    [string]$Owner,
    [string]$Repo,
    [int]$SinceDays = 7,
    [string]$OutputDir = "artifacts/perf",
    [string]$WorkflowFile = "supportbot.yml",
    [string]$PerformanceLabel = "bot:performance",
    [string]$SummaryIssueTitle = "Bot Performance Summary"
)

$ErrorActionPreference = "Stop"

if (-not $Owner -or -not $Repo) {
    throw "Owner and Repo are required"
}

$token = $env:GITHUB_TOKEN
if (-not $token) {
    throw "GITHUB_TOKEN is required"
}

$headers = @{ Authorization = "token $token"; Accept = "application/vnd.github+json" }
$baseUrl = "https://api.github.com"
$since = (Get-Date).ToUniversalTime().AddDays(-$SinceDays).ToString("yyyy-MM-ddTHH:mm:ssZ")

function Invoke-GitHubGet([string]$url) {
    return Invoke-RestMethod -Uri $url -Headers $headers -Method Get
}

function Invoke-GitHubPost([string]$url, $body) {
    $json = $body | ConvertTo-Json -Depth 6
    return Invoke-RestMethod -Uri $url -Headers $headers -Method Post -ContentType "application/json" -Body $json
}

function Get-IssuesSince([string]$owner, [string]$repo, [string]$sinceDate) {
    $results = @()
    $page = 1
    while ($true) {
        $url = "$baseUrl/repos/$owner/$repo/issues?state=all&since=$sinceDate&per_page=100&page=$page"
        $batch = Invoke-GitHubGet $url
        if (-not $batch -or $batch.Count -eq 0) { break }
        $results += $batch
        $page++
    }
    return $results | Where-Object { -not $_.pull_request }
}

function Get-WorkflowRuns([string]$owner, [string]$repo, [string]$workflowFile, [string]$sinceDate) {
    $page = 1
    $runs = @()
    while ($true) {
        $url = "$baseUrl/repos/$owner/$repo/actions/workflows/$workflowFile/runs?per_page=50&page=$page"
        $resp = Invoke-GitHubGet $url
        if (-not $resp.workflow_runs -or $resp.workflow_runs.Count -eq 0) { break }
        $runs += $resp.workflow_runs | Where-Object { $_.created_at -ge $sinceDate }
        $page++
    }
    return $runs
}

function Get-RunArtifacts([string]$owner, [string]$repo, [int]$runId) {
    $url = "$baseUrl/repos/$owner/$repo/actions/runs/$runId/artifacts"
    $resp = Invoke-GitHubGet $url
    return $resp.artifacts
}

function Download-Artifact([string]$url, [string]$path) {
    Invoke-WebRequest -Uri $url -Headers $headers -OutFile $path
}

function Extract-Telemetry([string]$zipPath, [string]$dest) {
    Expand-Archive -Path $zipPath -DestinationPath $dest -Force
    return Get-ChildItem -Path $dest -Filter *.json -Recurse | ForEach-Object {
        Get-Content -Path $_.FullName | ConvertFrom-Json
    }
}

$issues = Get-IssuesSince -owner $Owner -repo $Repo -sinceDate $since

$labelCounts = @{
    "bot:helpful" = 0
    "bot:needs-work" = 0
    "bot:wrong-category" = 0
    "bot:off-topic-correct" = 0
    "bot:off-topic-wrong" = 0
    "bot:resolved" = 0
    "bot:escalated" = 0
}

foreach ($issue in $issues) {
    foreach ($label in $issue.labels) {
        $name = $label.name
        if ($labelCounts.ContainsKey($name)) { $labelCounts[$name]++ }
    }
}

$score = 0
$score += $labelCounts["bot:helpful"] * 2
$score += $labelCounts["bot:resolved"] * 2
$score += $labelCounts["bot:off-topic-correct"] * 1
$score -= $labelCounts["bot:needs-work"] * 2
$score -= $labelCounts["bot:wrong-category"] * 2
$score -= $labelCounts["bot:off-topic-wrong"] * 1

$runs = Get-WorkflowRuns -owner $Owner -repo $Repo -workflowFile $WorkflowFile -sinceDate $since

$totalTokens = 0
$totalComments = 0
$totalLoops = 0
$totalTelemetryRuns = 0

$tempRoot = Join-Path $env:TEMP ("bot-telemetry-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null

foreach ($run in $runs) {
    $artifacts = Get-RunArtifacts -owner $Owner -repo $Repo -runId $run.id
    $telemetry = $artifacts | Where-Object { $_.name -eq "supportbot-telemetry" }
    if (-not $telemetry) { continue }

    $zipPath = Join-Path $tempRoot ("telemetry_$($run.id).zip")
    Download-Artifact -url $telemetry.archive_download_url -path $zipPath

    $dest = Join-Path $tempRoot ("run_$($run.id)")
    $records = Extract-Telemetry -zipPath $zipPath -dest $dest

    foreach ($record in $records) {
        $totalTelemetryRuns++
        if ($record.tokenUsage -and $record.tokenUsage.totalTokens) {
            $totalTokens += [int]$record.tokenUsage.totalTokens
        }
        if ($record.commentCount) { $totalComments += [int]$record.commentCount }
        if ($record.loopCount) { $totalLoops += [int]$record.loopCount }
    }
}

$avgTokensPerComment = if ($totalComments -gt 0) { [math]::Round($totalTokens / $totalComments, 2) } else { 0 }
$avgTokensPerLoop = if ($totalLoops -gt 0) { [math]::Round($totalTokens / $totalLoops, 2) } else { 0 }

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$summary = [ordered]@{
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    window_days = $SinceDays
    issue_count = $issues.Count
    labels = $labelCounts
    score = $score
    telemetry_runs = $totalTelemetryRuns
    total_tokens = $totalTokens
    total_comments = $totalComments
    total_loops = $totalLoops
    avg_tokens_per_comment = $avgTokensPerComment
    avg_tokens_per_loop = $avgTokensPerLoop
}

$summaryPath = Join-Path $OutputDir "bot_performance_summary.json"
$summary | ConvertTo-Json -Depth 6 | Set-Content -Path $summaryPath

$commentLines = @(
    "Summary: Bot performance (last $SinceDays days)",
    "",
    "Key signals:",
    "- Issues reviewed: $($issues.Count)",
    "- Score: $score",
    "- Helpful labels: $($labelCounts["bot:helpful"])",
    "- Needs work: $($labelCounts["bot:needs-work"])",
    "- Wrong category: $($labelCounts["bot:wrong-category"])",
    "- Off-topic correct: $($labelCounts["bot:off-topic-correct"])",
    "- Off-topic wrong: $($labelCounts["bot:off-topic-wrong"])",
    "- Resolved: $($labelCounts["bot:resolved"])",
    "- Escalated: $($labelCounts["bot:escalated"])",
    "",
    "Token usage:",
    "- Total tokens: $totalTokens",
    "- Avg tokens/comment: $avgTokensPerComment",
    "- Avg tokens/loop: $avgTokensPerLoop",
    "",
    "Artifacts:",
    "- Summary JSON: $summaryPath"
)

# Find or create summary issue
$existing = Invoke-GitHubGet "$baseUrl/repos/$Owner/$Repo/issues?state=open&labels=$PerformanceLabel&per_page=100" |
    Where-Object { $_.title -eq $SummaryIssueTitle } | Select-Object -First 1

if (-not $existing) {
    $body = @(
        "This issue tracks weekly bot performance summaries.",
        "",
        "Labels used for scoring:",
        "- bot:helpful (+2)",
        "- bot:resolved (+2)",
        "- bot:off-topic-correct (+1)",
        "- bot:needs-work (-2)",
        "- bot:wrong-category (-2)",
        "- bot:off-topic-wrong (-1)",
        "",
        "Update cadence: weekly via GitHub Actions."
    ) -join "`n"

    $created = Invoke-GitHubPost "$baseUrl/repos/$Owner/$Repo/issues" @{ title = $SummaryIssueTitle; body = $body; labels = @($PerformanceLabel) }
    $issueNumber = $created.number
} else {
    $issueNumber = $existing.number
}

$commentBody = $commentLines -join "`n"
Invoke-GitHubPost "$baseUrl/repos/$Owner/$Repo/issues/$issueNumber/comments" @{ body = $commentBody }

Write-Output "Wrote summary to $summaryPath and commented on issue #$issueNumber"
