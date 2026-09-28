"""Build every ExplorerPro icon from the approved Store tile artwork."""

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "store_assets"
SOURCE = STORE / "Square310x310Logo.png"
SIZES = (16, 20, 24, 30, 32, 36, 40, 48, 60, 64, 72, 80, 96, 256)
FORMS = ("", "_altform-unplated", "_altform-lightunplated")


def main() -> None:
    master = Image.open(SOURCE).convert("RGBA")
    # The Store tile is the user-approved design. Keep all runtime fallbacks
    # and the embedded EXE icon on the same artwork.
    desktop = master.resize((1024, 1024), Image.Resampling.LANCZOS)
    for relative in ("icon.png", "DesktopIcon.png", "assets/icon.png", "assets/DesktopIcon.png", "assets/ExplorerPro.png", "mobile_icons/icon.png"):
        desktop.save(ROOT / relative, optimize=True)
    for relative in (
        "icon.ico", "DesktopIcon.ico", "ExplorerPro.ico", "assets/icon.ico",
        "assets/DesktopIcon.ico", "assets/ExplorerPro.ico", "mobile_icons/favicon.ico",
    ):
        desktop.save(ROOT / relative, format="ICO", sizes=[(size, size) for size in (16, 24, 32, 48, 64, 128, 256)])
    desktop.save(ROOT / "assets/favicon.ico", format="ICO", sizes=[(size, size) for size in (16, 24, 32, 48)])
    for relative, size in (
        ("assets/favicon.png", 32), ("assets/favicon-64.png", 64),
        ("assets/apple-touch-icon.png", 180),
        ("mobile_icons/favicon.png", 32), ("mobile_icons/apple-touch-icon.png", 180),
        ("mobile_icons/apple-touch-icon-180.png", 180),
        ("mobile_icons/icon-192.png", 192),
        ("mobile_icons/icon-512.png", 512), ("mobile_icons/icon-maskable-192.png", 192),
        ("mobile_icons/icon-maskable-512.png", 512),
        ("mobile_icons/icons/favicon.png", 32),
        ("mobile_icons/icons/Icon-192.png", 192),
        ("mobile_icons/icons/Icon-512.png", 512),
        ("mobile_icons/icons/Icon-maskable-192.png", 192),
        ("mobile_icons/icons/Icon-maskable-512.png", 512),
    ):
        master.resize((size, size), Image.Resampling.LANCZOS).save(ROOT / relative, optimize=True)
    for relative, size in (
        ("icon_44x44.png", 44), ("icon_50x50.png", 50),
        ("icon_150x150.png", 150), ("icon_310x310.png", 310),
    ):
        master.resize((size, size), Image.Resampling.LANCZOS).save(STORE / relative, optimize=True)
    # The wide legacy mirror should use the same layout as the manifest logo.
    (STORE / "icon_310x150.png").write_bytes((STORE / "Wide310x150Logo.png").read_bytes())
    for size in SIZES:
        base = master.resize((size, size), Image.Resampling.LANCZOS)
        for form in FORMS:
            frame = base.copy()
            if form:
                alpha = frame.getchannel("A")
                corner = max(1, size // 8)
                alpha.paste(0, (0, 0, corner, corner))
                frame.putalpha(alpha)
            frame.save(STORE / f"Square44x44Logo.targetsize-{size}{form}.png", optimize=True)


if __name__ == "__main__":
    main()
