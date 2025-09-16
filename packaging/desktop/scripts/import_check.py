import sys, os
sys.path.insert(0, r"C:\\Program Files\\Audio Tuner\\resources\\api")
print("PYVER", sys.version)
try:
    import app.main_desktop as md
    print("IMPORT_OK")
except Exception as e:
    import traceback
    print("IMPORT_ERR", repr(e))
    traceback.print_exc()
    raise

