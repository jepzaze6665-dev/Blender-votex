---
name: video-analyzer
description: Break down any video the user sends (animation, anime, game footage, VFX, 3D model showcase, motion graphics, trailers, tutorials, GIFs) and report what it contains, how it was probably made, what Claude can build from it, and exactly what the user should supply, such as generated images or AI 3D models, with ready-to-paste prompts and specs. Use this whenever the user shares, drops, or points to a video or GIF file, or asks "ทำแบบนี้ได้ไหม", "วิเคราะห์วิดีโอ", "ดูคลิปนี้", "คลิปนี้ทำยังไง", "อยากได้แบบในคลิป", "ต้องช่วยอะไรบ้าง", "can you make this", or "how was this made", even if they do not say "analyze". Not for editing or converting a video with no question about recreating or understanding it.
---

# Video Analyzer

The user is a solo creator working across Blender, game VFX, and web 3D. They send a video and want two answers: **what can you do with this**, and **what do you need from me**. Everything below serves those two answers. A beautiful description of the video that leaves them unsure what to do next has failed.

Write to the user in their language (Thai unless they use another). Keep image and 3D generation prompts in English, because those tools respond best to it.

## 1. Get the file

- Local path: continue.
- URL: `yt-dlp` may not be installed, and downloading needs the user's go-ahead. Ask them to save the file locally, or get their OK to fetch it.
- Still image: open it directly and skip the script.
- If the user said what they want from the clip (a single effect, the camera, the style), that is the focus of the whole report. If they did not, cover the whole video and ask at the end.

## 2. Extract

Claude cannot watch video, so the script turns it into frames and measurements:

```bash
python "$HOME/.claude/skills/video-analyzer/scripts/analyze_video.py" "VIDEO" --out "video-analysis/NAME"
```

It writes `analysis.json`, `sheets/` (labelled contact sheets), and `frames/`. Default the output to `video-analysis/<name>` in the working folder, unless that is a repo where the user would not want generated files. Long clips are scanned at a reduced rate automatically.

Then:

1. Read `analysis.json`, then **look at every contact sheet**. The sheets are the evidence; the numbers only tell you where to look.
2. Go frame by frame on the moments that matter. Pick them from `motion_peaks_sec`, `flashes_sec`, and whatever caught your eye:
   ```bash
   python "$HOME/.claude/skills/video-analyzer/scripts/analyze_video.py" "VIDEO" --out "video-analysis/NAME" --burst 1.5-2.0
   ```
   An impact lasts a few frames and sampling usually misses it. Run at least one burst for VFX, combat, and animation. Open full frames from `frames/` when you need detail.
3. If there is speech that matters (tutorial, narration, dialogue), add `--transcribe` to the same command. It reuses the existing analysis. If the model is missing, ask before rerunning with `--allow-model-download`.
4. Check what is available right now. Use ToolSearch for `blender` to see if the Blender MCP is connected; `environment` in `analysis.json` lists the Blender executable, GPU, and speech-to-text. The plan must match this machine, not an ideal one.

### Reading the measurements

These are hints, and each can be wrong. Confirm against the frames before stating anything.

| Field | Meaning | Known failure |
|---|---|---|
| `active_region` | Static bars or app UI were cropped away before measuring; `frames/full_frame` keeps the original | Text in the removed area, such as a username or caption, only appears in that frame. Use `--full-frame` to keep it all |
| `shots`, `flashes_sec` | Hard cuts, and brief flashes that return to the prior image | Dissolves and fades are not detected. A big white bloom or fast camera whip can read as a cut, so check each one against the frames and report real scenes, not the raw count |
| `typical_hold_frames` (per shot) | 2 = on twos, 3 = on threes | Static shots have no cadence. Repeated frames in game footage can mean dropped frames. A re-recorded or re-encoded clip shows the capture rate, not the original |
| `camera_hint` | Pan, push-in, shake, or locked | A large moving subject can read as a pan. Check that the background actually moves |
| `loop` | `looks_seamless` = a loop; `starts_and_ends_empty` = a one-shot effect | A slow scene can look seamless by chance |
| `accent_palette` | Vivid colours without the background | GIF palettes are already reduced |
| `pixel_block_size` | Over 1 means upscaled pixel art at `native_pixel_size_estimate` | Heavy compression hides it |
| `audio_hits_matching_visual_events_sec` | Sound that lands on a cut, flash, or motion peak | Coincidental on busy clips. It shows timing only, not what the sound is |

## 3. Analyze

Read `references/video-types.md` for the section matching this video. A clip can match more than one type, such as gameplay containing VFX. Then split the video into **buildable elements**: the separate things someone would have to make, such as character, environment, sword trail, impact flash, camera shake, HUD. The element is the unit of the report, because each one can have a different answer.

For each element, decide:

- **What it is**, with a timestamp.
- **How it was probably made**, and how sure you are. Separate what you saw from what you inferred: "the trail has hard stepped edges at 12 fps" is an observation, "it is a flipbook" is an inference. Nobody can see a video's source files, so never state a technique as fact from footage alone.
- **Who can build it**, using the tiers in `references/capabilities.md`. Read that file every time, since honest tiers are the point of this skill. Overpromising costs the user days; a stylized character in Blender by Python alone is not the same as the one in the clip.

## 4. Decide what to ask for

The user's time is the scarcest resource, so ask for as little as possible.

- Do not request anything you can make yourself at acceptable quality. Procedural textures, simple props, shaders, particles, and camera work are yours.
- Ask where their input changes the outcome: organic characters, faces, painted concept art, photoreal textures, performances, licensed sound.
- Order requests so the first one unblocks the most work, and mark each as **required** or **optional**, giving the fallback if they skip it.
- Read `references/handoffs.md` for the prompt and spec of each asset. Every request must be usable with no follow-up question: tool type, ready-to-paste prompt, exact spec, save location, and what you will do once it arrives.
- Do not ask for a tool that suits the asset badly just because the user mentioned it. A voxel or pixel asset is better built from a grid than from an AI 3D generator, for example. Say so, since it saves them time.
- Fill prompts with what you measured: real palette hex values, camera angle, frame count, resolution.

**Target platform.** If the deliverable depends on where it will run (Blender render, web, Roblox, Unity, Unreal), and the user has not said, ask in the final question and describe the default you would use.

**Original work.** When the clip comes from a commercial game, film, or series, study the technique and build something original with the same feel. Do not reproduce its characters, logos, or designs, and keep franchise and character names out of generation prompts. If the user asks for a direct copy, say so plainly and offer the original route.

## 5. Report

Save the full report as `report.md` in the output folder, with frames embedded by relative path so the user can see what you mean. In chat, give the short version: the verdict, the tier table, the first request, and a link to the report. Use this structure, in the user's language:

```markdown
# วิเคราะห์: <ชื่อคลิป>

## สรุปสั้น
<ประเภทคลิป, ทำซ้ำได้แค่ไหน (เป็น % ของคลิปโดยประมาณ), งานชิ้นแรกที่ควรเริ่ม>

## ข้อมูลคลิป
<ความยาว, ขนาด, fps, จำนวนช็อต, จังหวะอนิเมชัน, ลูปหรือเล่นครั้งเดียว, พาเลตต์>

## ในคลิปมีอะไร
| ช่วงเวลา | เกิดอะไรขึ้น | จุดที่น่าสนใจ |

## แยกชิ้นงาน
| ชิ้นงาน | น่าจะทำด้วยวิธีไหน | ความมั่นใจ | ใครทำ |
(ใครทำ: 🟢 ผมทำเอง / 🟡 ผมทำได้แต่มีข้อจำกัด / 🔴 ต้องใช้คุณหรือเครื่องมืออื่น)

## สิ่งที่ผมทำได้เลย
<ผลลัพธ์จริงที่จะได้ เครื่องมือที่ใช้ ไฟล์ที่จะส่งมอบ>

## สิ่งที่ทำได้แต่มีข้อจำกัด
<ทำได้แค่ไหน ต่างจากในคลิปตรงไหน>

## สิ่งที่อยากให้คุณช่วย
### ขอ #1 — <ชื่อ> (จำเป็น/เสริม)
- เหตุผล / เครื่องมือ / Prompt / สเปก / บันทึกที่ / ถ้าไม่มี / ได้แล้วผมทำต่อ

## แผนงาน
<ลำดับงาน ใครทำอะไร งานไหนเริ่มได้ก่อนโดยไม่ต้องรอคุณ>

## สิ่งที่ผมไม่แน่ใจ
<สิ่งที่ดูจากเฟรมไม่ได้ และสมมติฐานที่ใช้>

## เลือกต่อ
<คำถามเดียว: อยากให้เริ่มจากส่วนไหน>
```

Keep tables tight and skip sections with nothing to say, except **สิ่งที่อยากให้คุณช่วย**: if you need nothing, say so, since that is good news. Do not start building until the user picks a direction; a video is often a reference for one part of a bigger idea.

## When assets come back

Inspect the file before building on it, using the checks in `references/handoffs.md`. Tell the user what passed and what failed, and fix what you can before asking them to regenerate.
