"""Asset helpers for the GPP application."""

from app.assets.logo_data import LOGO_BASE64


def get_logo_img_tag(class_name: str = "", style: str = "") -> str:
    """Return an HTML <img> tag with the embedded GPP official logo."""
    cls_attr = f' class="{class_name}"' if class_name else ""
    style_attr = f' style="{style}"' if style else ""
    return f'<img src="data:image/png;base64,{LOGO_BASE64}" alt="GPP Logo"{cls_attr}{style_attr} />'
