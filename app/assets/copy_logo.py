import base64
import pathlib

src = pathlib.Path(r'C:\Users\Saini\.gemini\antigravity\brain\9ec8c602-7d70-43f6-88b5-a8a21d3f8281\media__1783838748262.png')
dst = pathlib.Path(r'e:\Projects\Internship\gpp-visual-inspection-final\gpp-visual-inspection\app\assets\gpp_logo.png')
dst.parent.mkdir(parents=True, exist_ok=True)
if src.exists():
    dst.write_bytes(src.read_bytes())

b64 = base64.b64encode(dst.read_bytes()).decode('ascii')
logo_py = pathlib.Path(r'e:\Projects\Internship\gpp-visual-inspection-final\gpp-visual-inspection\app\assets\logo_data.py')
logo_py.write_text(f'"""Generated base64 logo data."""\n\nLOGO_BASE64 = "{b64}"\n', encoding='utf-8')
print("SUCCESS: Logo copied and base64 generated.")
