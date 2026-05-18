# update_law_corpus.ps1
# HaqDar AI - Automated Law Corpus Update Script
# Usage: .\update_law_corpus.ps1

Write-Host "⚖️  HaqDar AI - Law Corpus Updater" -ForegroundColor Cyan

# ------------------------------
# 1. Setup Paths and Variables
# ------------------------------
$ProjectRoot = "C:\Users\musta\haqdar-ai-backend"
$RealLawsFolder = "$ProjectRoot\real_laws"
$EmbeddingsFile = "$ProjectRoot\law-embeddings-real.json"
$BucketUri = "gs://haqdar-law-corpus-1"
$ProjectId = "haqdar-ai"
$Region = "asia-south1"
$EndpointId = "5323967243086725120"
$ProjectNumber = "1052663637521"
$GcloudPath = "C:\Users\musta\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

# Check if gcloud is available
if (-not (Test-Path $GcloudPath)) {
    $GcloudPath = "gcloud"  # Try system PATH
}

# ------------------------------
# 2. Activate Virtual Environment
# ------------------------------
Write-Host "`n🐍 Activating Python virtual environment..." -ForegroundColor Yellow
$VenvActivate = "$ProjectRoot\venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    & $VenvActivate
} else {
    Write-Host "❌ Virtual environment not found at $VenvActivate" -ForegroundColor Red
    exit 1
}

# ------------------------------
# 3. Run Python Processing Script
# ------------------------------
Write-Host "`n📄 Running OCR and embedding generation..." -ForegroundColor Yellow
python "$ProjectRoot\process_real_laws_ocr.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Python script failed. Check errors above." -ForegroundColor Red
    exit 1
}

# ------------------------------
# 4. Upload to Cloud Storage
# ------------------------------
Write-Host "`n☁️  Uploading embeddings to Cloud Storage..." -ForegroundColor Yellow
& $GcloudPath storage cp $EmbeddingsFile $BucketUri/
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Upload failed. Check gcloud authentication." -ForegroundColor Red
    exit 1
}

# ------------------------------
# 5. Create New Index (with timestamp)
# ------------------------------
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$IndexDisplayName = "haqdar-law-index-$Timestamp"
Write-Host "`n🔨 Creating new Vector Search Index: $IndexDisplayName" -ForegroundColor Yellow

$IndexConfig = @"
{
    "contentsDeltaUri": "$BucketUri",
    "config": {
        "dimensions": 768,
        "approximateNeighborsCount": 100,
        "algorithmConfig": {
            "treeAhConfig": {}
        }
    }
}
"@

# Save config to temp file
$ConfigFile = "$ProjectRoot\index_config_temp.json"
$IndexConfig | Out-File -FilePath $ConfigFile -Encoding utf8

$CreateOutput = & $GcloudPath ai indexes create `
    --display-name="$IndexDisplayName" `
    --region=$Region `
    --metadata-file=$ConfigFile 2>&1
Remove-Item $ConfigFile

# Extract Index ID from output
$IndexId = $null
if ($CreateOutput -match "indexes/(\d+)") {
    $IndexId = $Matches[1]
    Write-Host "✅ Index created with ID: $IndexId" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to create index or extract ID." -ForegroundColor Red
    Write-Host $CreateOutput
    exit 1
}

# ------------------------------
# 6. Wait for Index to be READY
# ------------------------------
Write-Host "`n⏳ Waiting for index to become READY (this may take 10-30 minutes)..." -ForegroundColor Yellow
do {
    Start-Sleep -Seconds 60
    $StatusOutput = & $GcloudPath ai indexes describe $IndexId --region=$Region --format="value(state)" 2>$null
    Write-Host "   Current state: $StatusOutput"
} while ($StatusOutput -ne "READY")

Write-Host "✅ Index is READY." -ForegroundColor Green

# ------------------------------
# 7. Deploy Index to Endpoint
# ------------------------------
$DeployedIndexId = "law_v$Timestamp"
Write-Host "`n🚀 Deploying index as $DeployedIndexId to endpoint..." -ForegroundColor Yellow

$DeployOutput = & $GcloudPath ai index-endpoints deploy-index `
    "projects/$ProjectNumber/locations/$Region/indexEndpoints/$EndpointId" `
    --deployed-index-id="$DeployedIndexId" `
    --display-name="$DeployedIndexId-display" `
    --index="projects/$ProjectNumber/locations/$Region/indexes/$IndexId" `
    --region=$Region 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Deployment failed." -ForegroundColor Red
    Write-Host $DeployOutput
    exit 1
}

Write-Host "✅ Deployment submitted. Waiting for completion..." -ForegroundColor Yellow
Start-Sleep -Seconds 30  # Give it a moment

# Check deployment status
$DeployDone = $false
do {
    Start-Sleep -Seconds 30
    $EndpointDesc = & $GcloudPath ai index-endpoints describe $EndpointId --region=$Region 2>$null
    if ($EndpointDesc -match "id: $DeployedIndexId") {
        $DeployDone = $true
    }
} while (-not $DeployDone)

Write-Host "✅ Index deployed successfully." -ForegroundColor Green

# ------------------------------
# 8. Update .env File
# ------------------------------
$EnvFile = "$ProjectRoot\.env"
Write-Host "`n📝 Updating .env file with DEPLOYED_INDEX_ID=$DeployedIndexId" -ForegroundColor Yellow
(Get-Content $EnvFile) -replace 'DEPLOYED_INDEX_ID=.*', "DEPLOYED_INDEX_ID=$DeployedIndexId" | Set-Content $EnvFile

# ------------------------------
# 9. Restart FastAPI Server (optional - user can do manually)
# ------------------------------
Write-Host "`n🔄 Please restart your FastAPI server manually with:" -ForegroundColor Cyan
Write-Host "   uvicorn app.main:app --reload" -ForegroundColor White
Write-Host "`n🎉 HaqDar AI law corpus update complete!" -ForegroundColor Green