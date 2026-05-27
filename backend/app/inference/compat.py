import sys

import numpy as np


def safe_log1p(values):
    if hasattr(values, "clip"):
        try:
            return np.log1p(values.clip(lower=0))
        except TypeError:
            return np.log1p(values.clip(min=0))
    return np.log1p(np.clip(values, a_min=0, a_max=None))


def install_joblib_compat_shims() -> None:
    main_module = sys.modules.get("__main__")
    if main_module is not None and not hasattr(main_module, "safe_log1p"):
        setattr(main_module, "safe_log1p", safe_log1p)
