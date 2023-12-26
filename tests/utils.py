import os
import os.path
from contextlib import contextmanager

@contextmanager
def open_test(fpath):
  uutDir = os.path.dirname(fpath)
  if not os.path.isdir(uutDir):
    os.makedirs(uutDir)

  with open(fpath, "w") as f:
    yield f
