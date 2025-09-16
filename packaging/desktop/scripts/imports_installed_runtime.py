import importlib
mods=['fastapi','uvicorn','numpy','librosa','soundfile','scipy','numba','llvmlite','pydantic','pydantic_core']
for m in mods:
    try:
        mod=importlib.import_module(m)
        v=getattr(mod,'__version__','?')
        print(m,'OK',v)
    except Exception as e:
        print(m,'ERR',repr(e))
