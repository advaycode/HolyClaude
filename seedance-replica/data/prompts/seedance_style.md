# Seedance-Style Prompts

ByteDance Seedance models respond best to prompts that read like a shot description from a cinematographer's notebook. The four-part structure below gives you most of Seedance's prompt-faithfulness on the open replica.

## The four-part structure

```
[Subject + action] · [Camera] · [Lighting + atmosphere] · [Aesthetic + style]
```

Each clause separated by a comma. Keep total length 30–80 words. Avoid filler.

---

## Examples

### Cinematic narrative

> A weary samurai pauses at the gate of an abandoned temple, his hand on his sword. Slow dolly forward, low angle, 35 mm. Golden hour, dust motes drifting through shafts of light, long shadows. Akira Kurosawa influence, Eastman color grade.

### Sci-fi action

> A cyberpunk hacker yanks a data jack from her temple, sparks fly. Whip pan from monitor wall to her face, handheld, 50 mm. Magenta and cyan neon, harsh practicals, smoke. Blade Runner 2049 grade, anamorphic flares.

### Nature documentary

> A snow leopard crosses a ridge against a vast snowfield, deliberate paw placement. Locked-off telephoto, 200 mm, compressed perspective. Soft overcast light, slate-blue palette, gentle wind catching the fur. Planet Earth style, smooth slow motion.

### Animation / stylized

> A red origami crane unfolds into a real bird mid-flight over a sunset lake. Tracking shot, low altitude, 24 mm wide. Warm magenta sky, water reflecting fire. Hayao Miyazaki palette, hand-painted texture, soft outlines.

### Talking head / portrait

> A young woman with freckles and short black hair speaks directly to the camera, calm and curious. Static medium shot, 85 mm, eye-level. Soft north-facing window light, cool background falloff. Documentary realism, natural skin tones, subtle lens halation.

### Foley / action close-up

> Close-up of hands kneading bread dough on a floured wooden surface. Static macro shot, 100 mm. Warm overhead window light, golden flour dust suspended. Tactile food photography, shallow depth, slight motion blur on the kneading rhythm.

---

## Words that consistently work

**Camera movement**: dolly in/out, push in/out, pan, tilt, tracking, locked-off, handheld, whip pan, crane up/down, orbital, drone

**Lens / framing**: 24 mm wide, 35 mm, 50 mm, 85 mm portrait, 100 mm macro, 200 mm telephoto, close-up, medium shot, wide shot, extreme close-up, two-shot, over-the-shoulder

**Lighting**: golden hour, blue hour, magic hour, harsh sun, overcast, soft window light, rim light, key + fill, low-key, high-key, practical lighting, neon practicals

**Mood**: cinematic, documentary, dreamlike, melancholic, hopeful, tense, intimate, vast, mundane, ethereal

**Color grade**: Kodachrome, Eastman, Fuji, Arri Alexa look, anamorphic, teal-and-orange, desaturated, monochrome, pastel

**Motion**: slow motion, real-time, time-lapse, slow dolly, gentle camera drift, locked, frenetic, hyperreal

---

## Words to AVOID

These trigger artifacts in Wan / LTX:
- "Beautiful," "amazing," "stunning," "best quality" — empty, no visual signal
- "4K, 8K, ultra-realistic, hyperrealistic" — model is trained on real footage, redundant
- "Award-winning, masterpiece" — old SD vocabulary, no effect here
- Long lists of irrelevant adjectives — dilutes signal
- Contradictory descriptions (e.g., "static handheld") — model picks one randomly

---

## Negative prompt template

Use this default negative across all generations:

```
blurry, low quality, distorted, warped, choppy motion, jittery, watermark, text, subtitles, signature, frame artifacts, extra limbs, deformed hands, missing fingers, mutated, glitch, oversaturated, banding, jpeg artifacts
```

For specific failure modes:

| If you see | Add to negative |
|---|---|
| Plasticky faces | "plastic skin, doll-like, waxy" |
| Wobbly hands | "distorted hands, extra fingers, melted hands" |
| Choppy motion | "choppy motion, frame skipping, juddery" |
| Watermarks (rare) | "watermark, logo, signature" |
| Oversaturation | "oversaturated, neon-burn" |

---

## Prompt expansion via Qwen2.5-7B

If you have the quality preset configured, the `--prompt-expander qwen2.5-7b` flag will auto-rewrite your short prompt into the four-part structure above. Example:

```
input:  "samurai in cherry blossoms"
output: "A lone samurai stands beneath a canopy of cherry blossoms, petals drifting around him. Slow dolly forward, low angle, 50 mm. Soft pink afternoon light, gentle haze, long shadows. Akira Kurosawa influence, painterly cinematic palette."
```

Run with `--show-expanded` to inspect what the expander produced before generation.
