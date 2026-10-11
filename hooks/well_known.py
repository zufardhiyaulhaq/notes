"""Copy the .well-known/ directory into the built site.

MkDocs ignores files and directories whose names start with a dot, so a
docs/.well-known/ would never be published. We keep the source at a non-dot
path (well-known/) and copy it into site_dir/.well-known/ after the build.
"""
import os
import shutil


def on_post_build(config, **kwargs):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = os.path.join(root, "well-known", "agent-card.json")
    dst_dir = os.path.join(config["site_dir"], ".well-known")
    os.makedirs(dst_dir, exist_ok=True)
    shutil.copy(src, os.path.join(dst_dir, "agent-card.json"))
