# install_4070.ps1 — one-shot Seedance-Replica installer for Windows + RTX 4070 (12 GB)
# Usage: ./scripts/install_4070.ps1 [-Force] [-SkipCuda] [-SkipComfyUI]

[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$SkipCuda,
    [switch]$SkipComfyUI
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "== Seedance-Replica installer (Windows / RTX 4070 12 GB) ==" -ForegroundColor Cyan
Write-Host "Repo root: $Root"

# --- 1. winget basics ----------------------------------------------------------
Write-Host "`n[1/8] Checking winget packages..." -ForegroundColor Yellow
$needed = @{
    "Python.Python.3.11"   = "python --version"
    "Git.Git"              = "git --version"
    "Gyan.FFmpeg"          = "ffmpeg -version"
    "7zip.7zip"            = "7z"
}
foreach ($pkg in $needed.Keys) {
    $checkCmd = $needed[$pkg]
    try { Invoke-Expression "$checkCmd 2>&1" | Out-Null }
    catch {
        Write-Host "  installing $pkg..." -ForegroundColor Gray
        winget install --id $pkg --silent --accept-source-agreements --accept-package-agreements
    }
}

# --- 2. CUDA -------------------------------------------------------------------
if (-not $SkipCuda) {
    Write-Host "`n[2/8] Checking CUDA..." -ForegroundColor Yellow
    $hasCuda = $false
    try {
        $nv = nvidia-smi 2>&1
        if ($LASTEXITCODE -eq 0) { $hasCuda = $true; Write-Host "  GPU detected." }
    } catch {}
    if (-not $hasCuda) {
        Write-Host "  ERROR: nvidia-smi not found. Install NVIDIA driver 555+ then re-run." -ForegroundColor Red
        exit 1
    }
    # We rely on PyTorch's bundled CUDA runtime; system CUDA toolkit not required for inference.
}

# --- 3. venv -------------------------------------------------------------------
Write-Host "`n[3/8] Python virtual env..." -ForegroundColor Yellow
$venv = Join-Path $Root ".venv"
if ((Test-Path $venv) -and $Force) {
    Write-Host "  --Force: removing existing venv"
    Remove-Item -Recurse -Force $venv
}
if (-not (Test-Path $venv)) {
    py -3.11 -m venv $venv
}
& "$venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip wheel setuptools

# --- 4. PyTorch + xformers + sage ----------------------------------------------
Write-Host "`n[4/8] PyTorch 2.5 + CUDA 12.4..." -ForegroundColor Yellow
pip install --upgrade `
    "torch==2.5.1" "torchvision==0.20.1" "torchaudio==2.5.1" `
    --index-url https://download.pytorch.org/whl/cu124
pip install "xformers==0.0.28.post3" --index-url https://download.pytorch.org/whl/cu124

Write-Host "  sage-attention (1.3x speedup on Ada)..."
pip install sageattention --no-build-isolation
if ($LASTEXITCODE -ne 0) {
    Write-Host "  sageattention build failed — continuing without it" -ForegroundColor Yellow
}

# --- 5. Repo requirements ------------------------------------------------------
Write-Host "`n[5/8] Repo requirements..." -ForegroundColor Yellow
pip install -r (Join-Path $Root "requirements.txt")

# --- 6. ComfyUI ----------------------------------------------------------------
if (-not $SkipComfyUI) {
    Write-Host "`n[6/8] ComfyUI + custom nodes..." -ForegroundColor Yellow
    $comfy = Join-Path $HOME "ComfyUI"
    if (-not (Test-Path $comfy)) {
        git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git $comfy
    }
    Push-Location $comfy
    pip install -r requirements.txt

    $customNodes = Join-Path $comfy "custom_nodes"
    $nodes = @{
        "ComfyUI-Manager"            = "https://github.com/ltdrdata/ComfyUI-Manager.git"
        "ComfyUI-GGUF"               = "https://github.com/city96/ComfyUI-GGUF.git"
        "ComfyUI-VideoHelperSuite"   = "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git"
        "ComfyUI-WanVideoWrapper"    = "https://github.com/kijai/ComfyUI-WanVideoWrapper.git"
        "ComfyUI-LTXVideo"           = "https://github.com/Lightricks/ComfyUI-LTXVideo.git"
        "ComfyUI-MMAudio"            = "https://github.com/kijai/ComfyUI-MMAudio.git"
        "ComfyUI-LatentSyncWrapper"  = "https://github.com/ShmuelRonen/ComfyUI-LatentSyncWrapper.git"
        "ComfyUI-Frame-Interpolation"= "https://github.com/Fannovel16/ComfyUI-Frame-Interpolation.git"
    }
    foreach ($n in $nodes.Keys) {
        $dst = Join-Path $customNodes $n
        if (-not (Test-Path $dst)) {
            git clone --depth 1 $nodes[$n] $dst
            $req = Join-Path $dst "requirements.txt"
            if (Test-Path $req) { pip install -r $req }
        }
    }
    Pop-Location
}

# --- 7. CausVid ----------------------------------------------------------------
Write-Host "`n[7/8] CausVid (distillation, optional)..." -ForegroundColor Yellow
$thirdParty = Join-Path $Root "third_party"
New-Item -ItemType Directory -Force -Path $thirdParty | Out-Null
$causvid = Join-Path $thirdParty "CausVid"
if (-not (Test-Path $causvid)) {
    git clone --depth 1 https://github.com/tianweiy/CausVid.git $causvid
}

# --- 8. Smoke test -------------------------------------------------------------
Write-Host "`n[8/8] Smoke test..." -ForegroundColor Yellow
python -c @"
import torch
assert torch.cuda.is_available(), 'CUDA not available'
print('  torch :', torch.__version__)
print('  CUDA  :', torch.version.cuda)
print('  GPU   :', torch.cuda.get_device_name(0))
print('  VRAM  :', round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1), 'GB')
"@

Write-Host "`n== Install complete ==" -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "  1) python scripts/download_models.py --preset balanced"
Write-Host "  2) python scripts/generate.py --preset balanced --prompt 'samurai in cherry blossoms' --out out/first.mp4"
Write-Host "  3) python scripts/add_audio.py --video out/first.mp4 --prompt 'soft wind'"
