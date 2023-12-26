
from contextlib import contextmanager

class Exporter(object):

  INDENT_STR = "  "

  def __init__(self, fout):
    self._fout = fout
    self._indent_level = 0

  def lprint(self, outstr, *args, **kwargs):
    kwargs["file"] = self._fout
    indents = self.INDENT_STR * self._indent_level
    outstr = indents + outstr
    print(outstr, *args, **kwargs)

  def indent(self, cnt=1):
    self._indent_level += cnt

  def dedent(self, cnt=1):
    self._indent_level -= cnt
    if self._indent_level < 0:
      raise RuntimeError("Indent Stack Violation - Can't be negative")

  @contextmanager
  def indented(self, cnt=1):
    self.indent(cnt)
    yield
    self.dedent(cnt)