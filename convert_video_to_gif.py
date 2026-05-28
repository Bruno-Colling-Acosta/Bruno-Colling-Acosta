from __future__ import annotations

import sys
from pathlib import Path


def print_install_instructions() -> None:
    python_exe = Path(sys.executable).name or "python"
    print("moviepy is not installed.")
    print("Install it with:")
    print(f"{python_exe} -m pip install moviepy imageio-ffmpeg")


def main() -> int:
    try:
        # MoviePy v2
        from moviepy import VideoFileClip
    except ImportError:
        try:
            # MoviePy v1 fallback
            from moviepy.editor import VideoFileClip
        except ImportError:
            print_install_instructions()
            return 1

    repo_root = Path(__file__).resolve().parent
    input_path = repo_root / "img" / "176-plotnuvem.mp4"
    output_path = repo_root / "img" / "nazare.gif"

    if not input_path.exists():
        print(f"Input video not found: {input_path}")
        return 1

    target_width = 1000
    target_fps = 12

    print(f"Converting {input_path} -> {output_path}")

    with VideoFileClip(str(input_path)) as clip:
        resize_width = min(target_width, int(clip.w))
        if hasattr(clip, "resized"):
            resized_clip = clip.resized(width=resize_width)
        else:
            resized_clip = clip.resize(width=resize_width)
        resized_clip.write_gif(
            str(output_path),
            fps=target_fps,
        )

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
