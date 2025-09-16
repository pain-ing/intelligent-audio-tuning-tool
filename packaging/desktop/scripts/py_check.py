import sys
print('PY', sys.version)
try:
    import numpy as np
    print('NP', np.__version__)
except Exception as e:
    print('NP_ERR', repr(e))
try:
    import pydantic_core as pc
    print('PC', getattr(pc, '__version__', '?'))
except Exception as e:
    print('PC_ERR', repr(e))
