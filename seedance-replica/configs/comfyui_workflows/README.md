# ComfyUI Workflows

ComfyUI workflow JSONs are environment-specific (they reference node IDs, exact model filenames, and graph layout). Rather than ship JSONs that will break on your install, this directory contains **workflow recipes** describing the node graph for each preset. After installing the listed custom nodes, build the graph once and save it — it'll persist in `~/ComfyUI/user/default/workflows/`.

For each recipe below, the install script (`scripts/install_4070.ps1`) installs the required custom nodes via ComfyUI-Manager or git clone.

---

## t2v_wan22_gguf.json (Quality preset)

Required custom nodes:
- ComfyUI-GGUF (city96)
- ComfyUI-VideoHelperSuite
- ComfyUI-WanVideoWrapper

Node graph:
```
[Unet Loader GGUF] (Wan2_2-T2V-A14B-HighNoise-Q5_K_M.gguf)  ─┐
[Unet Loader GGUF] (Wan2_2-T2V-A14B-LowNoise-Q5_K_M.gguf)   ─┤
                                                              ├─► [WanMoESampler]
[CLIPLoader] (umt5_xxl_fp8)                                  ─┤
[CLIPTextEncode] (prompt)                                    ─┤
[CLIPTextEncode] (negative)                                  ─┤
[VAELoader] (Wan2_2_VAE.safetensors)                         ─┤
[EmptyLatentVideo] (832x480, 81 frames)                      ─┤
                                                              │
                                                  [WanMoESampler]
                                                       │ latents
                                                       ▼
                                                  [VAEDecode]
                                                       │ frames
                                                       ▼
                                                  [VHS_VideoCombine] → mp4
```

Settings:
- Sampler: unipc, 30 steps, CFG 6.0, shift 5.0
- MoE threshold: 0.875

---

## i2v_wan22_gguf.json

Same as above, swap `Wan2_2-T2V-A14B` for `Wan2_2-I2V-A14B`, add:
- `[LoadImage]` → `[VAEEncode]` → connects to sampler init latent
- Set denoise to 0.99 (near-full strength for I2V)

---

## t2v_wan22_5b.json (Balanced)

Required custom nodes:
- ComfyUI-WanVideoWrapper

Node graph:
```
[CheckpointLoaderSimple] (Wan2.2-TI2V-5B.safetensors)
  ├─► [model] ─► [KSampler] ─► [VAEDecode] ─► [VHS_VideoCombine]
  ├─► [clip]   ─► [CLIPTextEncode] (positive/negative) ─► [KSampler]
  └─► [vae]    ─► [VAEDecode]

[EmptyLatentVideo] (1280x720, 81 frames) ─► [KSampler]
```

Settings:
- Sampler: dpmpp_2m_sde, karras scheduler, 30 steps, CFG 6.0, shift 5.0

---

## t2v_ltx_realtime.json (Fast)

Required custom nodes:
- ComfyUI-LTXVideo (Lightricks)

Node graph:
```
[LTXVCheckpointLoader] (ltxv-13b-0.9.8-distilled-fp8.safetensors)
  ├─► [LTXVModel] ─► [LTXVSampler] ─► [VAEDecode] ─► [VHS_VideoCombine]
  └─► [LTXVTextEncoder] ─► [LTXVConditioning] ─► [LTXVSampler]

[LTXVPrompt] (positive) ─► [LTXVTextEncoder]
[LTXVPrompt] (negative) ─► [LTXVTextEncoder]
[EmptyLTXVLatent] (768x512, 97 frames) ─► [LTXVSampler]
```

Settings:
- Sampler: euler, 8 steps, CFG 1.0, shift 3.0

---

## audio_mmaudio.json (V2A post-process)

Required custom nodes:
- ComfyUI-MMAudio

Node graph:
```
[LoadVideo] (input.mp4) ─► [VideoToFrames] ─► [MMAudioGenerator]
[MMAudioPromptEncode] (text prompt) ─► [MMAudioGenerator]
[MMAudioGenerator] ─► audio.wav
[LoadVideo] + audio.wav ─► [VHS_VideoCombine] → mp4 with audio
```

Settings:
- Steps: 25, CFG 4.5, sync_mode: strict

---

## multishot_chained.json

Required custom nodes:
- ComfyUI-WanVideoWrapper
- ComfyUI-Custom-Scripts (for the chained execution)
- ComfyUI-VideoHelperSuite

Pattern:
```
[Shot1 graph] ─► [VHS_VideoCombine] ─► shot1.mp4
                                          │
                                          ▼
                                  [ExtractLastFrame] ─► [LoadImage]
                                                            │
                                                            ▼
[Shot2 graph (I2V)] ─► [VHS_VideoCombine] ─► shot2.mp4
... repeat for N shots ...
[VideoConcat with crossfade] ─► final.mp4
```

This is easier to drive from `scripts/multishot.py` than to build in the visual editor; the CLI script orchestrates ComfyUI API calls for each shot.

---

## lipsync_latentsync.json

Required custom nodes:
- ComfyUI-LatentSyncWrapper

Node graph:
```
[LoadVideo] (face_video.mp4) ─┐
[LoadAudio] (speech.wav)     ─┤
                              ├─► [LatentSyncProcessor]
                              │
                                       │
                                       ▼
                              [VHS_VideoCombine] ─► lipsynced.mp4
```

---

## upscale_rife_resrgan.json

Required custom nodes:
- ComfyUI-Frame-Interpolation (RIFE)
- ComfyUI-Image-Upscaler (Real-ESRGAN)

Node graph:
```
[LoadVideo] (in.mp4) ─► [VideoToFrames] ─► [ImageUpscaleWithModel (RealESRGAN_x2plus)]
                                                    │ upscaled frames
                                                    ▼
                                             [RIFE_Interpolate (2x)]
                                                    │ doubled fps
                                                    ▼
                                             [FramesToVideo] ─► out_1080p_60fps.mp4
```

---

## Generating these workflows

```powershell
# After installing ComfyUI + custom nodes, build each graph once in the UI
# then save via File → Save As → name them per the list above
# Or use the API helper:
python scripts/build_comfyui_workflows.py --output ~/ComfyUI/user/default/workflows/
```

`build_comfyui_workflows.py` is a thin Python that constructs the JSON programmatically using the ComfyUI graph schema and validates node IDs exist in your install.
