from __future__ import annotations

import sys
from pathlib import Path


def print_install_instructions() -> None:
    print("Missing required dependencies.")
    print("Install with:")
    print(f"{Path(sys.executable).name} -m pip install pillow moviepy imageio imageio-ffmpeg")
    print("Or:")
    print("pip install pillow moviepy imageio imageio-ffmpeg")


def ensure_dependencies():
    try:
        from PIL import Image
    except Exception:
        print_install_instructions()
        return None, None

    try:
        from moviepy import VideoFileClip
    except Exception:
        try:
            from moviepy.editor import VideoFileClip
        except Exception:
            print_install_instructions()
            return None, None

    return Image, VideoFileClip


def optimize_stereo_images(img_dir: Path, web_dir: Path, Image) -> None:
    stereo_pairs = [
        ("000176_0000000035194_01.tif", "stereo_left.jpg"),
        ("000176_0000000035194_02.tif", "stereo_right.jpg"),
    ]
    for src_name, dst_name in stereo_pairs:
        src = img_dir / src_name
        dst = web_dir / dst_name
        with Image.open(src) as im:
            rgb = im.convert("RGB")
            rgb.thumbnail((900, 9000), Image.Resampling.LANCZOS)
            rgb.save(dst, format="JPEG", quality=85, optimize=True, progressive=True)
        print(f"Created {dst}")


def optimize_png_images(img_dir: Path, web_dir: Path, Image) -> None:
    mappings = [
        ("imagem_max.png", "imagem_max.jpg"),
        ("imagem_media.png", "imagem_media.jpg"),
        ("imagem_min.png", "imagem_min.jpg"),
    ]
    for src_name, dst_name in mappings:
        src = img_dir / src_name
        dst = web_dir / dst_name
        with Image.open(src) as im:
            rgb = im.convert("RGB")
            rgb.save(dst, format="JPEG", quality=85, optimize=True, progressive=True)
        print(f"Created {dst}")

    # Keep this as PNG per requested filename.
    src = img_dir / "linhadecosta-kmeans-plotfinal.png"
    dst = web_dir / "shoreline_kmeans.png"
    with Image.open(src) as im:
        rgb = im.convert("RGB")
        rgb.save(dst, format="PNG", optimize=True)
    print(f"Created {dst}")


def generate_gif(img_dir: Path, web_dir: Path, VideoFileClip) -> None:
    src = img_dir / "176-plotnuvem.mp4"
    dst = web_dir / "nazare.gif"

    target_width = 900
    target_fps = 10
    target_duration = 9  # seconds

    with VideoFileClip(str(src)) as clip:
        trimmed = clip.subclipped(0, min(target_duration, clip.duration)) if hasattr(clip, "subclipped") else clip.subclip(0, min(target_duration, clip.duration))
        resized = trimmed.resized(width=target_width) if hasattr(trimmed, "resized") else trimmed.resize(width=target_width)
        resized.write_gif(str(dst), fps=target_fps)

    size_mb = dst.stat().st_size / (1024 * 1024)
    if size_mb > 20:
        print(f"Warning: {dst.name} is {size_mb:.2f} MB (>20 MB). Consider width 800 or fps 8.")
    else:
        print(f"Created {dst} ({size_mb:.2f} MB)")


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    img_dir = repo_root / "img"
    web_dir = img_dir / "web"
    web_dir.mkdir(parents=True, exist_ok=True)

    Image, VideoFileClip = ensure_dependencies()
    if Image is None or VideoFileClip is None:
        return 1

    required = [
        img_dir / "000176_0000000035194_01.tif",
        img_dir / "000176_0000000035194_02.tif",
        img_dir / "imagem_max.png",
        img_dir / "imagem_media.png",
        img_dir / "imagem_min.png",
        img_dir / "linhadecosta-kmeans-plotfinal.png",
        img_dir / "176-plotnuvem.mp4",
    ]
    missing = [p for p in required if not p.exists()]
    if missing:
        print("Missing input files:")
        for p in missing:
            print(f"- {p}")
        return 1

    optimize_stereo_images(img_dir, web_dir, Image)
    optimize_png_images(img_dir, web_dir, Image)
    generate_gif(img_dir, web_dir, VideoFileClip)
    print("Optimization complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
