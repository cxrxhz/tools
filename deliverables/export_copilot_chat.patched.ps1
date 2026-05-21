param(
    [string]$SourcePath,
    [string]$WorkspaceStorageRoot,
    [string]$SessionId,
    [string]$OutputPath,
    [switch]$AlsoTxt,
    [switch]$Latest,
    [switch]$Readable
)

Set-StrictMode -Off
$ErrorActionPreference = 'Stop'

function Resolve-TranscriptSource {
    param(
        [string]$ExplicitSource,
        [string]$StorageRoot,
        [string]$Sid,
        [bool]$UseLatest
    )

    if ($ExplicitSource) {
        return (Resolve-Path -LiteralPath $ExplicitSource).Path
    }

    if ($Sid) {
        if (-not $StorageRoot) {
            throw 'When SessionId is provided, WorkspaceStorageRoot is also required.'
        }
        $candidate = Get-ChildItem -LiteralPath $StorageRoot -Directory |
            ForEach-Object {
                Join-Path $_.FullName "GitHub.copilot-chat\transcripts\$Sid.jsonl"
            } |
            Where-Object { Test-Path -LiteralPath $_ } |
            Select-Object -First 1

        if (-not $candidate) {
            throw "Could not find transcript for session id: $Sid"
        }
        return (Resolve-Path -LiteralPath $candidate).Path
    }

    if ($UseLatest) {
        if (-not $StorageRoot) {
            throw 'When -Latest is used, WorkspaceStorageRoot is required.'
        }
        $latestFile = Get-ChildItem -LiteralPath $StorageRoot -Directory |
            ForEach-Object {
                $transcriptDir = Join-Path $_.FullName 'GitHub.copilot-chat\transcripts'
                if (Test-Path -LiteralPath $transcriptDir) {
                    Get-ChildItem -LiteralPath $transcriptDir -File -Filter '*.jsonl'
                }
            } |
            Sort-Object LastWriteTimeUtc -Descending |
            Select-Object -First 1

        if (-not $latestFile) {
            throw 'Could not find any transcript .jsonl files under WorkspaceStorageRoot.'
        }
        return $latestFile.FullName
    }

    throw 'Provide -SourcePath, or (-WorkspaceStorageRoot with -SessionId), or (-WorkspaceStorageRoot with -Latest).'
}

function Ensure-OutputPath {
    param(
        [string]$Path,
        [string]$DefaultName
    )

    if (-not $Path) {
        throw 'OutputPath is required.'
    }

    $expanded = [System.IO.Path]::GetFullPath($Path)
    $looksLikeDirectory = $expanded.EndsWith([System.IO.Path]::DirectorySeparatorChar) -or
        $expanded.EndsWith([System.IO.Path]::AltDirectorySeparatorChar) -or
        -not [System.IO.Path]::GetExtension($expanded)

    if ($looksLikeDirectory) {
        if (-not (Test-Path -LiteralPath $expanded)) {
            New-Item -ItemType Directory -Path $expanded -Force | Out-Null
        }
        return (Join-Path $expanded $DefaultName)
    }

    $parent = Split-Path -Parent $expanded
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    return $expanded
}

function Format-Value {
    param(
        [AllowNull()]$Value
    )

    if ($null -eq $Value) {
        return ''
    }

    if ($Value -is [string]) {
        return $Value
    }

    return ($Value | ConvertTo-Json -Depth 20)
}

function Add-Block {
    param(
        [System.Collections.Generic.List[string]]$Lines,
        [string]$Title,
        [string]$Timestamp,
        [string]$Body
    )

    $Lines.Add(('=' * 80))
    $Lines.Add($Title)
    if ($Timestamp) {
        $Lines.Add("时间: $Timestamp")
    }
    $Lines.Add(('-' * 80))
    if ($Body) {
        foreach ($line in ($Body -split "`r?`n")) {
            $Lines.Add($line)
        }
    }
    else {
        $Lines.Add('')
    }
    $Lines.Add('')
}

function Write-ReadableTranscript {
    param(
        [string]$TranscriptPath,
        [string]$DestinationPath
    )

    $lines = [System.Collections.Generic.List[string]]::new()
    $eventCount = 0
    $messageCount = 0
    $toolStartCount = 0
    $toolCompleteCount = 0
    $sessionId = $null

    $lines.Add('Copilot Chat 可读整理版导出')
    $lines.Add("源文件: $TranscriptPath")
    $lines.Add('')

    Get-Content -LiteralPath $TranscriptPath -Encoding UTF8 | ForEach-Object {
        if ([string]::IsNullOrWhiteSpace($_)) {
            return
        }

        $event = $_ | ConvertFrom-Json -Depth 50
        $eventCount += 1

        if (-not $sessionId -and $event.data.sessionId) {
            $sessionId = [string]$event.data.sessionId
        }

        switch ($event.type) {
            'session.start' {
                Add-Block -Lines $lines -Title '会话开始' -Timestamp $event.timestamp -Body (
                    "sessionId: $($event.data.sessionId)`nversion: $($event.data.version)`nproducer: $($event.data.producer)`ncopilotVersion: $($event.data.copilotVersion)`nvscodeVersion: $($event.data.vscodeVersion)`nstartTime: $($event.data.startTime)"
                )
            }
            'user.message' {
                $messageCount += 1
                $body = Format-Value -Value $event.data.content
                if ($event.data.attachments -and $event.data.attachments.Count -gt 0) {
                    $body += "`n`nattachments:`n" + (Format-Value -Value $event.data.attachments)
                }
                Add-Block -Lines $lines -Title '用户消息' -Timestamp $event.timestamp -Body $body
            }
            'assistant.message' {
                $messageCount += 1
                $parts = [System.Collections.Generic.List[string]]::new()
                $parts.Add('content:')
                $parts.Add((Format-Value -Value $event.data.content))

                if ($event.data.reasoningText) {
                    $parts.Add('')
                    $parts.Add('reasoningText:')
                    $parts.Add((Format-Value -Value $event.data.reasoningText))
                }

                if ($event.data.toolRequests -and $event.data.toolRequests.Count -gt 0) {
                    $parts.Add('')
                    $parts.Add('toolRequests:')
                    $parts.Add((Format-Value -Value $event.data.toolRequests))
                }

                Add-Block -Lines $lines -Title '助手消息' -Timestamp $event.timestamp -Body ($parts -join "`n")
            }
            'assistant.turn_start' {
                Add-Block -Lines $lines -Title '助手回合开始' -Timestamp $event.timestamp -Body ("turnId: $($event.data.turnId)")
            }
            'assistant.turn_end' {
                Add-Block -Lines $lines -Title '助手回合结束' -Timestamp $event.timestamp -Body ("turnId: $($event.data.turnId)")
            }
            'tool.execution_start' {
                $toolStartCount += 1
                $body = "toolCallId: $($event.data.toolCallId)`ntoolName: $($event.data.toolName)"
                if ($event.data.arguments) {
                    $body += "`narguments:`n" + (Format-Value -Value $event.data.arguments)
                }
                Add-Block -Lines $lines -Title '工具执行开始' -Timestamp $event.timestamp -Body $body
            }
            'tool.execution_complete' {
                $toolCompleteCount += 1
                $body = "toolCallId: $($event.data.toolCallId)`nsuccess: $($event.data.success)"
                if ($event.data.PSObject.Properties['error']) {
                    $body += "`nerror:`n" + (Format-Value -Value $event.data.error)
                }
                Add-Block -Lines $lines -Title '工具执行完成' -Timestamp $event.timestamp -Body $body
            }
            default {
                Add-Block -Lines $lines -Title ("事件: " + $event.type) -Timestamp $event.timestamp -Body (Format-Value -Value $event.data)
            }
        }
    }

    $lines.Add(('=' * 80))
    $lines.Add('导出摘要')
    $lines.Add(('=' * 80))
    $lines.Add("sessionId: $sessionId")
    $lines.Add("eventCount: $eventCount")
    $lines.Add("messageCount: $messageCount")
    $lines.Add("toolExecutionStartCount: $toolStartCount")
    $lines.Add("toolExecutionCompleteCount: $toolCompleteCount")

    Set-Content -LiteralPath $DestinationPath -Value $lines -Encoding UTF8

    return [ordered]@{
        SessionId = $sessionId
        EventCount = $eventCount
        MessageCount = $messageCount
        ToolExecutionStartCount = $toolStartCount
        ToolExecutionCompleteCount = $toolCompleteCount
    }
}

$resolvedSource = Resolve-TranscriptSource -ExplicitSource $SourcePath -StorageRoot $WorkspaceStorageRoot -Sid $SessionId -UseLatest:$Latest.IsPresent
$sourceStem = [System.IO.Path]::GetFileNameWithoutExtension($resolvedSource)
$defaultName = if ($Readable) { "$sourceStem.readable.txt" } else { [System.IO.Path]::GetFileName($resolvedSource) }
$resolvedOutput = Ensure-OutputPath -Path $OutputPath -DefaultName $defaultName

$sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $resolvedSource).Hash

if ($Readable) {
    $readableStats = Write-ReadableTranscript -TranscriptPath $resolvedSource -DestinationPath $resolvedOutput
    $outputHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $resolvedOutput).Hash

    $result = [ordered]@{
        Mode = 'readable'
        SourcePath = $resolvedSource
        OutputPath = $resolvedOutput
        SourceBytes = (Get-Item -LiteralPath $resolvedSource).Length
        OutputBytes = (Get-Item -LiteralPath $resolvedOutput).Length
        SourceSHA256 = $sourceHash
        OutputSHA256 = $outputHash
        SessionId = $readableStats.SessionId
        EventCount = $readableStats.EventCount
        MessageCount = $readableStats.MessageCount
        ToolExecutionStartCount = $readableStats.ToolExecutionStartCount
        ToolExecutionCompleteCount = $readableStats.ToolExecutionCompleteCount
    }

    $result | ConvertTo-Json -Depth 5
    return
}

[System.IO.File]::Copy($resolvedSource, $resolvedOutput, $true)

$txtOutput = $null
if ($AlsoTxt) {
    $txtOutput = [System.IO.Path]::ChangeExtension($resolvedOutput, '.txt')
    [System.IO.File]::Copy($resolvedSource, $txtOutput, $true)
}

$outputHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $resolvedOutput).Hash
$txtHash = $null
if ($txtOutput) {
    $txtHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $txtOutput).Hash
}

$result = [ordered]@{
    Mode = 'exact'
    SourcePath = $resolvedSource
    OutputPath = $resolvedOutput
    SourceBytes = (Get-Item -LiteralPath $resolvedSource).Length
    OutputBytes = (Get-Item -LiteralPath $resolvedOutput).Length
    SourceSHA256 = $sourceHash
    OutputSHA256 = $outputHash
    HashMatch = ($sourceHash -eq $outputHash)
}

if ($txtOutput) {
    $result.TxtOutputPath = $txtOutput
    $result.TxtOutputBytes = (Get-Item -LiteralPath $txtOutput).Length
    $result.TxtOutputSHA256 = $txtHash
    $result.TxtHashMatch = ($sourceHash -eq $txtHash)
}

$result | ConvertTo-Json -Depth 5
