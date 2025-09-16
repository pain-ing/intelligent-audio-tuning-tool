import sys
sys.path.insert(0, r"C:\\Program Files\\Audio Tuner\\resources\\api")
try:
    import app.main_desktop as md
    print('IMPORT_OK')
except Exception as e:
    print('IMPORT_ERR', repr(e))
