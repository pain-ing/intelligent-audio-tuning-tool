import os, shutil, zipfile
WHEEL = r"d:\\Mituanapp2\\packaging\\desktop\\vendor\\wheels\\pydantic_core-2.33.2-cp311-cp311-win_amd64.whl"
DEST = r"d:\\Mituanapp2\\packaging\\desktop\\vendor\\wheels\\pyd_core_311_unz"
if os.path.exists(DEST):
    shutil.rmtree(DEST)
os.makedirs(DEST, exist_ok=True)
with zipfile.ZipFile(WHEEL, 'r') as zf:
    zf.extractall(DEST)
print("EXTRACTED", DEST)

