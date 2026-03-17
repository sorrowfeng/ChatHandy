"""
build.py — ChatHandy 打包脚本
用法：python build.py
输出：dist/ChatHandy/ChatHandy.exe（单目录，无需安装）
"""
import subprocess
import sys
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
SPEC = ROOT / "ChatHandy.spec"


def main() -> None:
    print("=" * 50)
    print("ChatHandy 打包工具")
    print("=" * 50)

    # 清理旧产物
    if DIST.exists():
        print(f"清理旧 dist: {DIST}")
        shutil.rmtree(DIST)
    if BUILD.exists():
        print(f"清理旧 build: {BUILD}")
        shutil.rmtree(BUILD)

    print("\n开始打包...\n")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(SPEC),
         "--noconfirm",
         "--distpath", str(DIST),
         "--workpath", str(BUILD)],
        cwd=ROOT,
    )

    if result.returncode != 0:
        print("\n打包失败，请检查上方错误信息。")
        sys.exit(1)

    exe = DIST / "ChatHandy" / "ChatHandy.exe"
    if exe.exists():
        size_mb = sum(
            f.stat().st_size for f in (DIST / "ChatHandy").rglob("*") if f.is_file()
        ) / 1024 / 1024
        print("\n打包成功！")
        print(f"   位置：{exe}")
        print(f"   大小：{size_mb:.1f} MB")
    else:
        print("\n未找到输出 exe，打包可能失败。")
        sys.exit(1)


if __name__ == "__main__":
    main()
