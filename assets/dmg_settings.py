# dmgbuild settings. Run via build-dmg.sh, which passes app= and background= with -D.
import os.path

app = defines["app"]  # noqa: F821 (provided by dmgbuild)
app_name = os.path.basename(app)

format = "UDZO"
filesystem = "HFS+"
files = [app]
symlinks = {"Applications": "/Applications"}

background = defines["background"]  # noqa: F821
# 448 = 420px of artwork + Finder's 28px title bar.
window_rect = ((200, 120), (660, 448))
icon_size = 112
text_size = 13
icon_locations = {app_name: (180, 220), "Applications": (480, 220)}

show_status_bar = False
show_tab_view = False
show_toolbar = False
show_pathbar = False
show_sidebar = False
default_view = "icon-view"
show_icon_preview = False
