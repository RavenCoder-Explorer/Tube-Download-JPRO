#!/usr/bin/env python3
"""
Tube Download JPRO - High Impact 9:16 Promo Video Generator
Renders a 30-second (900 frame) 1080x1920 vertical video for YouTube Shorts, TikTok & Reels.
Pipes directly to FFmpeg with synthesized 124 BPM background beat and vector badges.
"""

import os
import sys
import math
import time
import subprocess
import wave
import struct
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
W, H = 1080, 1920
FPS = 30
DURATION_SEC = 30
TOTAL_FRAMES = FPS * DURATION_SEC  # 900 frames


def draw_vector_check(draw, cx, cy, radius=18, bg_color=(16, 185, 129)):
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=bg_color)
    pts = [(cx - 8, cy), (cx - 2, cy + 6), (cx + 8, cy - 5)]
    draw.line(pts[:2], fill=(255, 255, 255), width=3)
    draw.line(pts[1:], fill=(255, 255, 255), width=3)


def ensure_audio_track() -> Path:
    audio_path = PROJECT_ROOT / "scratch" / "promo_music.wav"
    if audio_path.exists() and audio_path.stat().st_size > 1000:
        return audio_path

    audio_path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 44100
    duration = 30.0
    total_samples = int(sample_rate * duration)
    bpm = 124
    beat_sec = 60.0 / bpm

    chords = [
        [220.0, 261.63, 329.63, 440.0],  # Am
        [174.61, 220.0, 261.63, 349.23], # F
        [261.63, 329.63, 392.0, 523.25], # C
        [196.0, 246.94, 293.66, 392.0]   # G
    ]

    out = bytearray()
    for i in range(total_samples):
        t = i / sample_rate
        beat_idx = int(t / beat_sec)
        bar_idx = (beat_idx // 4) % len(chords)
        current_chord = chords[bar_idx]
        t_in_beat = t % beat_sec

        # Kick
        kick = 0.0
        if t_in_beat < 0.24:
            freq = 45 + 110 * math.exp(-t_in_beat * 35)
            kick = math.sin(2 * math.pi * freq * t_in_beat) * math.exp(-t_in_beat * 14) * 0.46

        # Snare / Clap
        snare = 0.0
        if (beat_idx % 2 == 1) and t_in_beat < 0.2:
            noise = (math.sin(t * 12345.67) % 1.0) * 2.0 - 1.0
            snare = noise * math.exp(-t_in_beat * 24) * 0.22

        # Hi-hat
        t_in_eighth = t % (beat_sec / 2)
        hat = 0.0
        if t_in_eighth < 0.045:
            noise = (math.sin(t * 98765.43) % 1.0) * 2.0 - 1.0
            hat = noise * math.exp(-t_in_eighth * 85) * 0.12

        # Synth pluck
        sub_beat = int((t % beat_sec) / (beat_sec / 4))
        note_freq = current_chord[sub_beat % len(current_chord)]
        t_in_16th = t % (beat_sec / 4)
        pluck = 0.0
        for h in range(1, 5):
            pluck += (math.sin(2 * math.pi * note_freq * h * t) / h)
        pluck *= math.exp(-t_in_16th * 18) * 0.18

        # Bass
        bass_freq = current_chord[0] / 2.0
        bass = math.sin(2 * math.pi * bass_freq * t) * 0.22

        sample = kick + snare + hat + pluck + bass
        if t < 0.8:
            sample *= (t / 0.8)
        elif t > 28.5:
            sample *= max(0.0, (30.0 - t) / 1.5)

        sample = max(-0.95, min(0.95, sample))
        val = int(sample * 32767)
        out.extend(struct.pack('<hh', val, val))

    with wave.open(str(audio_path), 'wb') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(out)

    return audio_path


def render_promo_video(output_mp4: Path):
    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    audio_path = ensure_audio_track()
    ffmpeg_bin = PROJECT_ROOT / "bin" / "ffmpeg.exe"
    if not ffmpeg_bin.exists():
        ffmpeg_bin = Path("ffmpeg")

    # Fonts
    font_bold_path = r"C:\Windows\Fonts\segoeuib.ttf"
    font_reg_path = r"C:\Windows\Fonts\segoeui.ttf"

    f_tag = ImageFont.truetype(font_bold_path, 25)
    f_title = ImageFont.truetype(font_bold_path, 52)
    f_sub = ImageFont.truetype(font_reg_path, 28)
    f_bullet = ImageFont.truetype(font_bold_path, 29)
    f_badge = ImageFont.truetype(font_bold_path, 22)
    f_cta = ImageFont.truetype(font_bold_path, 36)
    f_link = ImageFont.truetype(font_bold_path, 26)
    f_small = ImageFont.truetype(font_reg_path, 22)

    # Assets
    icon = Image.open(PROJECT_ROOT / "assets" / "icon.png").convert("RGBA")
    icon_small = icon.resize((48, 48), Image.Resampling.LANCZOS)
    icon_hero = icon.resize((220, 220), Image.Resampling.LANCZOS)

    img_down = Image.open(PROJECT_ROOT / "docs" / "assets" / "images" / "screen_downloader.png").convert("RGB")
    img_batch = Image.open(PROJECT_ROOT / "docs" / "assets" / "images" / "screen_batch.png").convert("RGB")
    img_scraper = Image.open(PROJECT_ROOT / "docs" / "assets" / "images" / "screen_scraper_dialog.png").convert("RGB")

    # Start FFmpeg process
    cmd = [
        str(ffmpeg_bin),
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{W}x{H}",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "-",
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-preset", "faster",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_mp4)
    ]

    print("Launching FFmpeg...", flush=True)
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    t_start = time.time()
    sw, sh = W // 4, H // 4

    for frame_idx in range(TOTAL_FRAMES):
        t = frame_idx / float(FPS)
        scene_num = int(frame_idx // 150)
        scene_t = (frame_idx % 150) / 150.0

        canvas = Image.new("RGB", (W, H), (8, 13, 24))
        draw = ImageDraw.Draw(canvas)

        # Ambient Glow Overlay
        glow_layer = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        d_glow = ImageDraw.Draw(glow_layer)
        glow_x1 = int(sw * 0.3 + sw * 0.15 * math.sin(t * 1.2))
        glow_y1 = int(sh * 0.2 + sh * 0.1 * math.cos(t * 1.2))
        glow_x2 = int(sw * 0.7 + sw * 0.15 * math.cos(t * 1.0))
        glow_y2 = int(sh * 0.75 + sh * 0.1 * math.sin(t * 1.0))

        d_glow.ellipse([glow_x1 - 60, glow_y1 - 60, glow_x1 + 60, glow_y1 + 60], fill=(0, 242, 254, 35))
        d_glow.ellipse([glow_x2 - 70, glow_y2 - 70, glow_x2 + 70, glow_y2 + 70], fill=(245, 158, 11, 28))
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(25))
        glow_layer = glow_layer.resize((W, H), Image.Resampling.BILINEAR)
        canvas.paste(glow_layer, (0, 0), glow_layer)

        # Floating Top Glass Header
        header_y = 70
        draw.rounded_rectangle([180, header_y, W - 180, header_y + 68], radius=34, fill=(15, 23, 42), outline=(56, 189, 248, 100), width=2)
        canvas.paste(icon_small, (200, header_y + 10), icon_small)
        draw.text((260, header_y + 34), "TUBE DOWNLOAD JPRO", font=ImageFont.truetype(font_bold_path, 22), fill=(255, 255, 255), anchor="lm")
        draw.rounded_rectangle([W - 320, header_y + 16, W - 204, header_y + 52], radius=18, fill=(245, 158, 11))
        draw.text((W - 262, header_y + 34), "PRO v1.3", font=f_badge, fill=(10, 15, 30), anchor="mm")

        # Scene Content
        if scene_num == 0:
            # SCENE 1: Hook & Brand Hero
            draw.text((W // 2, 230), "TIRED OF SLOW, AD-FILLED DOWNLOADERS?", font=ImageFont.truetype(font_bold_path, 32), fill=(244, 63, 94), anchor="mm")
            draw.text((W // 2, 290), "Meet the Future of Media Archiving", font=f_sub, fill=(148, 163, 184), anchor="mm")

            pulse = 1.0 + 0.04 * math.sin(t * 6.0)
            cur_icon_w = int(220 * pulse)
            cur_icon = icon.resize((cur_icon_w, cur_icon_w), Image.Resampling.LANCZOS)
            icon_x = (W - cur_icon_w) // 2
            icon_y = 380 + (220 - cur_icon_w) // 2

            ring_r = int(140 * pulse)
            draw.ellipse([W // 2 - ring_r, 490 - ring_r, W // 2 + ring_r, 490 + ring_r], outline=(0, 242, 254), width=3)
            draw.ellipse([W // 2 - ring_r - 12, 490 - ring_r - 12, W // 2 + ring_r + 12, 490 + ring_r + 12], outline=(245, 158, 11), width=2)
            canvas.paste(cur_icon, (icon_x, icon_y), cur_icon)

            draw.text((W // 2, 690), "TUBE DOWNLOAD JPRO", font=f_title, fill=(255, 255, 255), anchor="mm")
            draw.text((W // 2, 755), "High-Performance Windows Media Suite", font=f_sub, fill=(56, 189, 248), anchor="mm")

            bullets = [
                ("4K / 8K UHD & 320kbps MP3 Audio", (0, 242, 254)),
                ("Watermark-Free TikTok & Reels", (16, 185, 129)),
                ("Visual Channel & Playlist Scraper", (245, 158, 11)),
                ("100% Ad-Free • Portable Windows .zip", (255, 255, 255))
            ]
            by = 840
            for text_b, color_b in bullets:
                draw.rounded_rectangle([80, by, W - 80, by + 86], radius=20, fill=(15, 23, 42), outline=(255, 255, 255, 30), width=1)
                draw_vector_check(draw, 130, by + 43, radius=18, bg_color=color_b)
                draw.text((170, by + 43), text_b, font=f_bullet, fill=(255, 255, 255), anchor="lm")
                by += 110

            draw.rounded_rectangle([140, 1400, W - 140, 1485], radius=24, fill=(16, 185, 129))
            draw.text((W // 2, 1442), "DOWNLOAD FREE (PORTABLE .ZIP)", font=f_cta, fill=(10, 15, 30), anchor="mm")

        elif scene_num in (1, 2, 3, 4):
            configs = {
                1: {
                    "tag": "ULTRA RESOLUTION ENGINE",
                    "tag_color": (0, 242, 254),
                    "headline": "Download in Full 4K & 8K",
                    "sub": "Preserves original 60fps bitrates & HDR colors",
                    "image": img_down,
                    "bullets": [
                        "4K 60FPS & 8K Ultra HD Master Streams",
                        "Studio 320kbps High-Fidelity MP3 Audio",
                        "Precision Timestamp Trimmer & Subtitles"
                    ]
                },
                2: {
                    "tag": "CREATOR CONTENT WORKFLOW",
                    "tag_color": (236, 72, 153),
                    "headline": "Zero Watermarks. Original CDN.",
                    "sub": "Direct stream extraction from TikTok & Instagram",
                    "image": img_down,
                    "bullets": [
                        "Clean TikTok & Instagram Reels (No Watermark)",
                        "Full YouTube Shorts Audio & Video Merging",
                        "Original Lossless Pinterest Art & Photo Pins"
                    ]
                },
                3: {
                    "tag": "HIGH SPEED BULK QUEUE",
                    "tag_color": (16, 185, 129),
                    "headline": "Batch Queue with Smart Naming",
                    "sub": "Import dozens of links with auto-incrementing IDs",
                    "image": img_batch,
                    "bullets": [
                        "Paste 50+ URLs at Once for Bulk Processing",
                        "12 Custom Naming Templates (001 - Title)",
                        "Auto-Sort Folders & Sleep PC When Finished"
                    ]
                },
                4: {
                    "tag": "1-CLICK CHANNEL EXPLORER",
                    "tag_color": (245, 158, 11),
                    "headline": "Visual Channel Scraper",
                    "sub": "Preview and import entire playlists in seconds",
                    "image": img_scraper,
                    "bullets": [
                        "Interactive Card Grid with Video Durations",
                        "1-Click 'Select All' to Send to Batch Queue",
                        "Built-in 1-Click Engine Auto-Updater"
                    ]
                }
            }

            cfg = configs[scene_num]

            tag_w = 480
            draw.rounded_rectangle([W // 2 - tag_w // 2, 180, W // 2 + tag_w // 2, 230], radius=25, fill=(15, 23, 42), outline=cfg["tag_color"], width=2)
            draw.text((W // 2, 205), cfg["tag"], font=f_tag, fill=cfg["tag_color"], anchor="mm")

            draw.text((W // 2, 280), cfg["headline"], font=f_title, fill=(255, 255, 255), anchor="mm")
            draw.text((W // 2, 335), cfg["sub"], font=f_sub, fill=(148, 163, 184), anchor="mm")

            frame_w = 940
            frame_h = 700
            fx = (W - frame_w) // 2
            fy = 400

            draw.rounded_rectangle([fx, fy, fx + frame_w, fy + frame_h], radius=24, fill=(15, 23, 42), outline=(56, 189, 248, 90), width=2)
            draw.rounded_rectangle([fx, fy, fx + frame_w, fy + 44], radius=24, fill=(17, 24, 39))
            draw.ellipse([fx + 20, fy + 15, fx + 34, fy + 29], fill=(239, 68, 68))
            draw.ellipse([fx + 44, fy + 15, fx + 58, fy + 29], fill=(245, 158, 11))
            draw.ellipse([fx + 68, fy + 15, fx + 82, fy + 29], fill=(16, 185, 129))
            draw.text((fx + frame_w // 2, fy + 22), "Tube Download JPRO — Windows 64-bit", font=ImageFont.truetype(font_reg_path, 16), fill=(148, 163, 184), anchor="mm")

            src_img = cfg["image"]
            sw_orig, sh_orig = src_img.size
            zoom = 1.0 + 0.08 * scene_t
            pan_y = int(40 * scene_t)
            crop_w = int(sw_orig / zoom)
            crop_h = int((frame_h - 44) * (sw_orig / frame_w) / zoom)
            crop_h = min(crop_h, sh_orig)

            crop_x1 = max(0, (sw_orig - crop_w) // 2)
            crop_y1 = min(max(0, pan_y), sh_orig - crop_h)
            crop_x2 = min(sw_orig, crop_x1 + crop_w)
            crop_y2 = min(sh_orig, crop_y1 + crop_h)

            cropped = src_img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            scaled_crop = cropped.resize((frame_w - 4, frame_h - 48), Image.Resampling.BILINEAR)
            canvas.paste(scaled_crop, (fx + 2, fy + 45))

            by = 1145
            for bullet_txt in cfg["bullets"]:
                draw.rounded_rectangle([80, by, W - 80, by + 86], radius=20, fill=(15, 23, 42), outline=(255, 255, 255, 25), width=1)
                draw_vector_check(draw, 130, by + 43, radius=18, bg_color=(16, 185, 129))
                draw.text((170, by + 43), bullet_txt, font=f_bullet, fill=(255, 255, 255), anchor="lm")
                by += 105

            draw.rounded_rectangle([180, 1500, W - 180, 1570], radius=20, fill=(56, 189, 248, 40), outline=(56, 189, 248), width=2)
            draw.text((W // 2, 1535), "FAST • CLEAN • ZERO ADWARE", font=f_tag, fill=(0, 242, 254), anchor="mm")

        elif scene_num == 5:
            # SCENE 6: Outro & Call to Action
            draw.text((W // 2, 220), "UPGRADE YOUR CREATOR WORKFLOW", font=ImageFont.truetype(font_bold_path, 34), fill=(245, 158, 11), anchor="mm")
            draw.text((W // 2, 280), "Download Tube Download JPRO Today", font=f_title, fill=(255, 255, 255), anchor="mm")

            cx1, cy1, cx2, cy2 = 80, 360, W - 80, 1180
            draw.rounded_rectangle([cx1, cy1, cx2, cy2], radius=30, fill=(15, 23, 42), outline=(245, 158, 11), width=2)

            canvas.paste(icon_hero, (W // 2 - 110, 410), icon_hero)
            draw.text((W // 2, 680), "TUBE DOWNLOAD JPRO", font=f_title, fill=(255, 255, 255), anchor="mm")
            draw.text((W // 2, 735), "Version 1.3.0 Standalone Portable", font=f_sub, fill=(56, 189, 248), anchor="mm")

            px1, py1 = 120, 800
            draw.rounded_rectangle([px1, py1, px1 + 390, py1 + 120], radius=16, fill=(17, 24, 39), outline=(16, 185, 129), width=2)
            draw.text((px1 + 195, py1 + 42), "FREE EDITION", font=f_tag, fill=(16, 185, 129), anchor="mm")
            draw.text((px1 + 195, py1 + 82), "720p HD • 5-Queue", font=f_small, fill=(148, 163, 184), anchor="mm")

            px2 = W - 120 - 390
            draw.rounded_rectangle([px2, py1, px2 + 390, py1 + 120], radius=16, fill=(17, 24, 39), outline=(245, 158, 11), width=2)
            draw.text((px2 + 195, py1 + 42), "PRO PLANS FROM $2", font=f_tag, fill=(245, 158, 11), anchor="mm")
            draw.text((px2 + 195, py1 + 82), "4K/8K • 320k • Scraper • $19 Life", font=f_small, fill=(148, 163, 184), anchor="mm")

            draw_vector_check(draw, 220, 980, radius=14, bg_color=(16, 185, 129))
            draw.text((250, 980), "Bundled FFmpeg & yt-dlp Core", font=f_bullet, fill=(255, 255, 255), anchor="lm")
            draw_vector_check(draw, 220, 1035, radius=14, bg_color=(16, 185, 129))
            draw.text((250, 1035), "No Admin Rights • Zero Spyware", font=f_bullet, fill=(255, 255, 255), anchor="lm")
            draw_vector_check(draw, 220, 1090, radius=14, bg_color=(56, 189, 248))
            draw.text((250, 1090), "Works on Windows 10 & 11 (64-bit)", font=f_bullet, fill=(56, 189, 248), anchor="lm")

            pulse_btn = 1.0 + 0.03 * math.sin(t * 8.0)
            btn_w = int(820 * pulse_btn)
            btn_h = int(110 * pulse_btn)
            bx1 = (W - btn_w) // 2
            by1 = 1240
            bx2 = bx1 + btn_w
            by2 = by1 + btn_h

            draw.rounded_rectangle([bx1, by1, bx2, by2], radius=28, fill=(16, 185, 129))
            draw.text((W // 2, by1 + btn_h // 2), "DOWNLOAD FREE (PORTABLE .ZIP)", font=f_cta, fill=(10, 15, 30), anchor="mm")

            draw.text((W // 2, 1410), "github.com/RavenCoder-Explorer/Tube-Download-JPRO", font=f_link, fill=(0, 242, 254), anchor="mm")
            draw.text((W // 2, 1460), "100% Free & Open Source Core • Instant Launch", font=f_small, fill=(148, 163, 184), anchor="mm")

        # Bottom Animated Progress Bar
        p_bar_h = 10
        p_bar_y = H - 30
        p_progress = (frame_idx + 1) / float(TOTAL_FRAMES)
        draw.rounded_rectangle([40, p_bar_y, W - 40, p_bar_y + p_bar_h], radius=5, fill=(30, 41, 59))
        draw.rounded_rectangle([40, p_bar_y, 40 + int((W - 80) * p_progress), p_bar_y + p_bar_h], radius=5, fill=(0, 242, 254))

        proc.stdin.write(canvas.tobytes())

        if (frame_idx + 1) % 150 == 0 or frame_idx == TOTAL_FRAMES - 1:
            elapsed = time.time() - t_start
            fps_actual = (frame_idx + 1) / max(0.1, elapsed)
            percent = int((frame_idx + 1) * 100 / TOTAL_FRAMES)
            print(f"Rendered {frame_idx + 1}/{TOTAL_FRAMES} frames ({percent}%) - {fps_actual:.1f} fps", flush=True)

    proc.stdin.close()
    proc.wait()

    if proc.returncode != 0:
        raise RuntimeError("FFmpeg video rendering failed.")

    total_time = time.time() - t_start
    print(f"[SUCCESS] Promotional video created successfully in {total_time:.1f}s: {output_mp4}", flush=True)


if __name__ == "__main__":
    out_file = PROJECT_ROOT / "dist" / "TubeDownloadJPRO_Promo.mp4"
    render_promo_video(out_file)
