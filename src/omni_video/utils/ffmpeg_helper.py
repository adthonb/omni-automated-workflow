import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def is_ffmpeg_available() -> bool:
    """Check if ffmpeg is installed and accessible in PATH."""
    return shutil.which("ffmpeg") is not None


def convert_mp4_to_mp3(video_path: str, audio_path: str, bitrate: str = "192k") -> str:
    """
    Convert MP4 video to MP3 audio with 192 kb/s quality.
    Command from Implementation.md:
      ffmpeg -i video.mp4 -vn -c:a libmp3lame -b:a 192k audio.mp3
    """
    v_path = Path(video_path)
    a_path = Path(audio_path)

    if not v_path.exists():
        raise FileNotFoundError(f"Input video file not found: {video_path}")

    a_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(v_path),
        "-vn",
        "-c:a",
        "libmp3lame",
        "-b:a",
        bitrate,
        str(a_path),
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed (code {res.returncode}): {res.stderr}")

    return str(a_path)


def convert_pcm_to_mp3(
    pcm_input: bytes | str,
    output_audio_path: str,
    sample_rate: int = 24000,
    channels: int = 1,
) -> str:
    """Convert raw PCM bytes or file to 192k MP3."""
    out_path = Path(output_audio_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    temp_pcm_file: tempfile.NamedTemporaryFile | None = None
    if isinstance(pcm_input, bytes):
        temp_pcm_file = tempfile.NamedTemporaryFile(suffix=".pcm", delete=False)
        temp_pcm_file.write(pcm_input)
        temp_pcm_file.flush()
        temp_pcm_file.close()
        pcm_path = temp_pcm_file.name
    else:
        pcm_path = str(pcm_input)

    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "s16le",
            "-ar",
            str(sample_rate),
            "-ac",
            str(channels),
            "-i",
            pcm_path,
            "-vn",
            "-ar",
            "44100",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            str(out_path),
        ]

        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"PCM to MP3 conversion failed (code {res.returncode}): {res.stderr}")
    finally:
        if temp_pcm_file and os.path.exists(temp_pcm_file.name):
            try:
                os.remove(temp_pcm_file.name)
            except OSError:
                pass

    return str(out_path)


def get_audio_duration(audio_path: str) -> float:
    """Get audio duration in seconds using ffprobe/ffmpeg."""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        return 30.0


def assemble_reels_video(
    image_paths: list[str] | None = None,
    video_paths: list[str] | None = None,
    audio_path: str | None = None,
    output_path: str = "",
    title_text: str = "",
    hook_text: str = "",
) -> str:
    """
    Assemble 9:16 vertical video (1080x1920) for Facebook Reels combining
    multi reference images or videos and voiceover audio.
    Supports:
    - Multiple videos: scales and concatenates into vertical video sequence
    - Multiple images: creates vertical slideshow cycling through images
    - Mixed videos & images: concatenates video clips and image slides
    - Single video / image fallback
    - Gradient canvas fallback if no media found
    """
    image_paths = image_paths or []
    video_paths = video_paths or []

    valid_videos = [v for v in video_paths if os.path.exists(v)]
    valid_images = [img for img in image_paths if os.path.exists(img)]

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    duration = 30.0
    if audio_path and os.path.exists(audio_path):
        duration = get_audio_duration(audio_path)

    # 1. Multiple videos (or mixed videos + images)
    if len(valid_videos) > 1 or (valid_videos and valid_images):
        cmd = ["ffmpeg", "-y"]
        filter_parts = []
        input_count = 0

        # Add videos
        for v in valid_videos:
            cmd.extend(["-i", v])
            filter_parts.append(
                f"[{input_count}:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{input_count}];"
            )
            input_count += 1

        # Add images as timed slides if any
        if valid_images:
            slide_duration = max(3.0, duration / (len(valid_videos) + len(valid_images)))
            for img in valid_images:
                cmd.extend(["-loop", "1", "-t", str(slide_duration), "-i", img])
                filter_parts.append(
                    f"[{input_count}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30[v{input_count}];"
                )
                input_count += 1

        tags = "".join(f"[v{i}]" for i in range(input_count))
        filter_parts.append(f"{tags}concat=n={input_count}:v=1:a=0[vcat]")
        filter_str = "".join(filter_parts)

        if audio_path and os.path.exists(audio_path):
            cmd.extend(
                [
                    "-i",
                    audio_path,
                    "-filter_complex",
                    filter_str,
                    "-map",
                    "[vcat]",
                    "-map",
                    f"{input_count}:a:0",
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-pix_fmt",
                    "yuv420p",
                    "-shortest",
                    str(out_path),
                ]
            )
        else:
            cmd.extend(
                [
                    "-filter_complex",
                    filter_str,
                    "-map",
                    "[vcat]",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-t",
                    str(duration),
                    str(out_path),
                ]
            )

        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            return str(out_path)
        print(f"[FFmpegHelper] Multi-video assembly notice: {res.stderr[:200]}", file=sys.stderr)

    # 2. Single video
    if len(valid_videos) == 1:
        input_video = valid_videos[0]
        cmd = ["ffmpeg", "-y", "-i", input_video]

        if audio_path and os.path.exists(audio_path):
            cmd.extend(
                [
                    "-i",
                    audio_path,
                    "-vf",
                    "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1",
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-pix_fmt",
                    "yuv420p",
                    "-shortest",
                    str(out_path),
                ]
            )
        else:
            cmd.extend(
                [
                    "-vf",
                    "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(out_path),
                ]
            )

        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            return str(out_path)

    # 3. Multiple images (Vertical Slideshow)
    if len(valid_images) > 1:
        per_slide = max(2.5, duration / len(valid_images))
        cmd = ["ffmpeg", "-y"]
        filter_parts = []
        for i, img in enumerate(valid_images):
            cmd.extend(["-loop", "1", "-t", str(per_slide), "-i", img])
            filter_parts.append(
                f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30[v{i}];"
            )
        tags = "".join(f"[v{i}]" for i in range(len(valid_images)))
        filter_parts.append(f"{tags}concat=n={len(valid_images)}:v=1:a=0[vcat]")
        filter_str = "".join(filter_parts)

        if audio_path and os.path.exists(audio_path):
            cmd.extend(
                [
                    "-i",
                    audio_path,
                    "-filter_complex",
                    filter_str,
                    "-map",
                    "[vcat]",
                    "-map",
                    f"{len(valid_images)}:a:0",
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-pix_fmt",
                    "yuv420p",
                    "-t",
                    str(duration),
                    "-shortest",
                    str(out_path),
                ]
            )
        else:
            cmd.extend(
                [
                    "-filter_complex",
                    filter_str,
                    "-map",
                    "[vcat]",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-t",
                    str(duration),
                    str(out_path),
                ]
            )

        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            return str(out_path)

    # 4. Single image
    if len(valid_images) == 1:
        img = valid_images[0]
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img]
        if audio_path and os.path.exists(audio_path):
            cmd.extend(
                [
                    "-i",
                    audio_path,
                    "-vf",
                    "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1",
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-pix_fmt",
                    "yuv420p",
                    "-t",
                    str(duration),
                    "-shortest",
                    str(out_path),
                ]
            )
        else:
            cmd.extend(
                [
                    "-vf",
                    "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-t",
                    str(duration),
                    str(out_path),
                ]
            )

        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            return str(out_path)

    # 3. Fallback: Generate vertical gradient Reel canvas
    clean_title = (title_text or "Shopee Affiliate").replace("'", "").replace('"', "").replace(":", "")
    clean_hook = (hook_text or "Viral Shopee Product").replace("'", "").replace('"', "").replace(":", "")

    filter_complex = (
        f"color=c=0x111827:s=1080x1920:d={duration}[bg];"
        f"[bg]drawtext=text='{clean_title}':fontsize=64:fontcolor=white:x=(w-text_w)/2:y=300,"
        f"drawtext=text='{clean_hook}':fontsize=42:fontcolor=yellow:x=(w-text_w)/2:y=420,"
        f"drawtext=text='Shopee Affiliate Special':fontsize=36:fontcolor=orange:x=(w-text_w)/2:y=h-250[outv]"
    )

    cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=0x0f172a:s=1080x1920:d={duration}"]

    if audio_path and os.path.exists(audio_path):
        cmd.extend(
            [
                "-i",
                audio_path,
                "-vf",
                filter_complex,
                "-map",
                "0:v",
                "-map",
                "1:a",
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-pix_fmt",
                "yuv420p",
                "-shortest",
                str(out_path),
            ]
        )
    else:
        cmd.extend(
            [
                "-vf",
                filter_complex,
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(out_path),
            ]
        )

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode == 0:
        return str(out_path)

    # Fallback to simple solid color if drawtext filter lacks fonts
    simple_cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=0x1e293b:s=1080x1920:d={duration}"]
    if audio_path and os.path.exists(audio_path):
        simple_cmd.extend(
            [
                "-i",
                audio_path,
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-pix_fmt",
                "yuv420p",
                "-shortest",
                str(out_path),
            ]
        )
    else:
        simple_cmd.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p", str(out_path)])

    res2 = subprocess.run(simple_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res2.returncode == 0:
        return str(out_path)

    raise RuntimeError(f"Fallback video creation failed (code {res2.returncode}): {res.stderr}")
