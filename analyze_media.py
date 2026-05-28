from __future__ import annotations

import mimetypes
import sys
from pathlib import Path
from typing import Any


def _try_imports() -> dict[str, Any]:
    deps: dict[str, Any] = {
        "PIL": None,
        "imageio": None,
        "moviepy": None,
        "cv2": None,
    }

    try:
        from PIL import Image  # type: ignore

        deps["PIL"] = Image
    except Exception:
        pass

    try:
        import imageio.v3 as iio  # type: ignore

        deps["imageio"] = iio
    except Exception:
        pass

    try:
        from moviepy import VideoFileClip  # type: ignore

        deps["moviepy"] = VideoFileClip
    except Exception:
        try:
            from moviepy.editor import VideoFileClip  # type: ignore

            deps["moviepy"] = VideoFileClip
        except Exception:
            pass

    try:
        import cv2  # type: ignore

        deps["cv2"] = cv2
    except Exception:
        pass

    return deps


def _fmt_mb(num_bytes: int) -> float:
    return num_bytes / (1024 * 1024)


def _detect_kind(path: Path, mime: str | None) -> str:
    suffix = path.suffix.lower()
    if suffix == ".gif":
        return "gif"
    if mime:
        if mime.startswith("image/"):
            return "image"
        if mime.startswith("video/"):
            return "video"
    if suffix in {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}:
        return "image"
    if suffix in {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}:
        return "video"
    return "other"


def _get_image_dims(path: Path, deps: dict[str, Any]) -> tuple[int | None, int | None]:
    pil_image = deps.get("PIL")
    if pil_image:
        try:
            with pil_image.open(path) as im:
                return int(im.width), int(im.height)
        except Exception:
            pass
    return None, None


def _get_video_meta(path: Path, deps: dict[str, Any]) -> tuple[float | None, float | None, int | None, int | None]:
    # Prefer moviepy for duration/fps metadata when available.
    video_file_clip = deps.get("moviepy")
    if video_file_clip:
        try:
            with video_file_clip(str(path)) as clip:
                duration = float(clip.duration) if clip.duration is not None else None
                fps = float(clip.fps) if getattr(clip, "fps", None) is not None else None
                width = int(clip.w) if getattr(clip, "w", None) is not None else None
                height = int(clip.h) if getattr(clip, "h", None) is not None else None
                return duration, fps, width, height
        except Exception:
            pass

    cv2_mod = deps.get("cv2")
    if cv2_mod:
        try:
            cap = cv2_mod.VideoCapture(str(path))
            if cap.isOpened():
                fps = cap.get(cv2_mod.CAP_PROP_FPS) or None
                frame_count = cap.get(cv2_mod.CAP_PROP_FRAME_COUNT) or None
                width = int(cap.get(cv2_mod.CAP_PROP_FRAME_WIDTH) or 0) or None
                height = int(cap.get(cv2_mod.CAP_PROP_FRAME_HEIGHT) or 0) or None
                duration = None
                if fps and frame_count and fps > 0:
                    duration = float(frame_count / fps)
                cap.release()
                return duration, float(fps) if fps else None, width, height
            cap.release()
        except Exception:
            pass

    iio = deps.get("imageio")
    if iio:
        try:
            meta = iio.immeta(path)
            fps = None
            if isinstance(meta, dict):
                fps_val = meta.get("fps")
                if isinstance(fps_val, (int, float)):
                    fps = float(fps_val)
            return None, fps, None, None
        except Exception:
            pass

    return None, None, None, None


def _estimate_friendliness(kind: str, size_mb: float, width: int | None, fps: float | None) -> str:
    if size_mb > 30:
        return "Poor"
    if size_mb > 10:
        return "Needs optimization"
    if kind == "gif" and fps is not None and fps > 15:
        return "Okay (high fps)"
    if width is not None and width > 1400:
        return "Okay (large dimensions)"
    return "Good"


def _suggestions(row: dict[str, Any]) -> list[str]:
    s: list[str] = []
    kind = row["kind"]
    size_mb = row["size_mb"]
    width = row["width"]
    fps = row["fps"]
    ext = row["ext"]

    if size_mb > 10:
        s.append("Reduce size (target <= 10 MB)")
    if kind == "gif":
        if width and width > 1000:
            s.append("Resize GIF to ~1000px width")
        if fps and fps > 15:
            s.append("Lower GIF fps to ~12-15")
        if size_mb > 15:
            s.append("Consider MP4/WebM + thumbnail in README")
    if kind == "video" and ext in {".mp4", ".webm"} and size_mb > 20:
        s.append("Trim/encode lower bitrate for sharing")
    if kind == "image" and width and width > 2000:
        s.append("Downscale static image for README")

    return s


def _print_table(rows: list[dict[str, Any]]) -> None:
    headers = [
        "Filename",
        "Type",
        "Size (MB)",
        "Image Res",
        "GIF Res",
        "Video Duration (s)",
        "Video FPS",
        "Dimensions",
        "GitHub Friendly",
    ]

    table_rows: list[list[str]] = []
    for r in rows:
        image_res = f"{r['width']}x{r['height']}" if r["kind"] == "image" and r["width"] and r["height"] else "-"
        gif_res = f"{r['width']}x{r['height']}" if r["kind"] == "gif" and r["width"] and r["height"] else "-"
        duration = f"{r['duration']:.2f}" if isinstance(r["duration"], float) else "-"
        fps = f"{r['fps']:.2f}" if isinstance(r["fps"], float) else "-"
        dims = f"{r['width']}x{r['height']}" if r["width"] and r["height"] else "-"
        table_rows.append(
            [
                r["name"],
                r["kind"],
                f"{r['size_mb']:.2f}",
                image_res,
                gif_res,
                duration,
                fps,
                dims,
                r["friendly"],
            ]
        )

    widths = [len(h) for h in headers]
    for row in table_rows:
        for i, cell in enumerate(row):
            if len(cell) > widths[i]:
                widths[i] = len(cell)

    def fmt_line(cols: list[str]) -> str:
        return " | ".join(col.ljust(widths[i]) for i, col in enumerate(cols))

    print(fmt_line(headers))
    print("-+-".join("-" * w for w in widths))
    for row in table_rows:
        print(fmt_line(row))


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    img_dir = repo_root / "img"
    if not img_dir.exists():
        print(f"img directory not found: {img_dir}")
        return 1

    deps = _try_imports()
    missing = [name for name, module in deps.items() if module is None]
    if missing:
        python_exe = Path(sys.executable).name or "python"
        print("Some optional dependencies are missing:", ", ".join(missing))
        print("Install with:")
        print(f"{python_exe} -m pip install pillow imageio moviepy opencv-python")
        print()

    files = [p for p in img_dir.iterdir() if p.is_file()]
    if not files:
        print("No files found in img directory.")
        return 0

    rows: list[dict[str, Any]] = []
    for path in files:
        mime, _ = mimetypes.guess_type(path.name)
        kind = _detect_kind(path, mime)
        size_bytes = path.stat().st_size
        size_mb = _fmt_mb(size_bytes)

        width = height = None
        duration = fps = None

        if kind in {"image", "gif"}:
            width, height = _get_image_dims(path, deps)
            if kind == "gif":
                iio = deps.get("imageio")
                if iio:
                    try:
                        meta = iio.immeta(path)
                        if isinstance(meta, dict):
                            fps_val = meta.get("fps")
                            if isinstance(fps_val, (int, float)):
                                fps = float(fps_val)
                    except Exception:
                        pass
        elif kind == "video":
            duration, fps, width, height = _get_video_meta(path, deps)

        friendly = _estimate_friendliness(kind, size_mb, width, fps)

        rows.append(
            {
                "name": path.name,
                "ext": path.suffix.lower(),
                "kind": kind,
                "size_mb": size_mb,
                "width": width,
                "height": height,
                "duration": duration,
                "fps": fps,
                "friendly": friendly,
            }
        )

    rows.sort(key=lambda r: r["size_mb"], reverse=True)

    print(f"Media report for: {img_dir}")
    print(f"Total files scanned: {len(rows)}")
    print()
    _print_table(rows)
    print()

    large = [r for r in rows if r["size_mb"] > 10]
    if large:
        print("Warnings (>10 MB):")
        for r in large:
            print(f"- {r['name']}: {r['size_mb']:.2f} MB")
        print()

    print("Optimization opportunities for GitHub README usage:")
    any_suggestion = False
    for r in rows:
        suggestions = _suggestions(r)
        if suggestions:
            any_suggestion = True
            print(f"- {r['name']}: " + "; ".join(suggestions))
    if not any_suggestion:
        print("- No obvious optimization opportunities found.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
