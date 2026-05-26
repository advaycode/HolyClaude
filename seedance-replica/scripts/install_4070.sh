#!/usr/bin/env bash
# install_4070.sh — Seedance-Replica installer for Linux + RTX 4070 (12 GB)
# Tested on Ubuntu 22.04. Usage: ./scripts/install_4070.sh [--force] [--skip-comfy]

set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." &>/dev/null && pwd)"
cd "$ROOT"

FORCE=0
SKIP_COMFY=0
for a in "$@"; do
    case "$a" in
        --force) FORCE=1 ;;
        --skip-comfy) SKIP_COMFY=1 ;;
    esac
done

say() { echo -e "\033[36m== $* ==\033[0m"; }
warn(){ echo -e "\033[33m$*\033[0m"; }
err() { echo -e "\033[31m$*\033[0m" >&2; }

say "Seedance-Replica installer (Linux / RTX 4070 12 GB)"
echo "Repo root: $ROOT"

# 1. system packages
say "[1/8] System packages"
sudo apt-get update -qq
sudo apt-get install -y -qq python3.11 python3.11-venv python3.11-dev git ffmpeg p7zip-full build-essential

# 2. CUDA / driver check
say "[2/8] CUDA / driver"
if ! command -v nvidia-smi >/dev/null 2>&1; then
    err "nvidia-smi not found. Install NVIDIA driver 555+ first."
    exit 1
fi
nvidia-smi | head -n 1

# 3. venv
say "[3/8] Python venv"
if [[ -d .venv && $FORCE -eq 1 ]]; then rm -rf .venv; fi
[[ -d .venv ]] || python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel setuptools

# 4. PyTorch + extras
say "[4/8] PyTorch 2.5 + CUDA 12.4"
pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 \
    --index-url https://download.pytorch.org/whl/cu124
pip install xformers==0.0.28.post3 --index-url https://download.pytorch.org/whl/cu124
pip install sageattention --no-build-isolation || warn "sageattention build failed, continuing"

# 5. repo requirements
say "[5/8] Repo requirements"
pip install -r requirements.txt

# 6. ComfyUI
if [[ $SKIP_COMFY -eq 0 ]]; then
    say "[6/8] ComfyUI + custom nodes"
    COMFY="$HOME/ComfyUI"
    [[ -d $COMFY ]] || git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git "$COMFY"
    pushd "$COMFY" >/dev/null
    pip install -r requirements.txt
    mkdir -p custom_nodes
    declare -A NODES=(
        [ComfyUI-Manager]=https://github.com/ltdrdata/ComfyUI-Manager.git
        [ComfyUI-GGUF]=https://github.com/city96/ComfyUI-GGUF.git
        [ComfyUI-VideoHelperSuite]=https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
        [ComfyUI-WanVideoWrapper]=https://github.com/kijai/ComfyUI-WanVideoWrapper.git
        [ComfyUI-LTXVideo]=https://github.com/Lightricks/ComfyUI-LTXVideo.git
        [ComfyUI-MMAudio]=https://github.com/kijai/ComfyUI-MMAudio.git
        [ComfyUI-LatentSyncWrapper]=https://github.com/ShmuelRonen/ComfyUI-LatentSyncWrapper.git
        [ComfyUI-Frame-Interpolation]=https://github.com/Fannovel16/ComfyUI-Frame-Interpolation.git
    )
    for name in "${!NODES[@]}"; do
        dst="custom_nodes/$name"
        if [[ ! -d $dst ]]; then
            git clone --depth 1 "${NODES[$name]}" "$dst"
            [[ -f "$dst/requirements.txt" ]] && pip install -r "$dst/requirements.txt"
        fi
    done
    popd >/dev/null
fi

# 7. CausVid
say "[7/8] CausVid (distillation)"
mkdir -p third_party
[[ -d third_party/CausVid ]] || git clone --depth 1 https://github.com/tianweiy/CausVid.git third_party/CausVid

# 8. smoke test
say "[8/8] Smoke test"
python -c "
import torch
assert torch.cuda.is_available(), 'CUDA not available'
print('  torch :', torch.__version__)
print('  CUDA  :', torch.version.cuda)
print('  GPU   :', torch.cuda.get_device_name(0))
print('  VRAM  :', round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1), 'GB')
"

say "Install complete"
echo "Next:"
echo "  1) python scripts/download_models.py --preset balanced"
echo "  2) python scripts/generate.py --preset balanced --prompt 'samurai in cherry blossoms' --out out/first.mp4"
echo "  3) python scripts/add_audio.py --video out/first.mp4 --prompt 'soft wind'"
