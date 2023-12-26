
import unittest
import os
import os.path

from contextlib import contextmanager

from argparse import Namespace
import subprocess as sp

from lbstanza_wrappers.Lbstanza import EnumExporter, NativeEnumExporter

@contextmanager
def open_test(fpath):
  uutDir = os.path.dirname(fpath)
  if not os.path.isdir(uutDir):
    os.makedirs(uutDir)

  with open(fpath, "w") as f:
    yield f


class EnumExporterTests(unittest.TestCase):
  def test_basic(self):
    """ This tests basic functionality for the EnumExporter class
    This will generate multiple stanza files, and then compile them with `stanza`
    and run a stanza unit test on them.
    """
    stanza_dir = "tests/uut/enum_exporter/"
    fout = os.path.join(stanza_dir, "Colors.stanza")
    with open_test(fout) as cap:
      exp = EnumExporter(cap, "Colors", [("Red", 0), ("Green", 1), ("Blue", 2) ])

      opts = Namespace(pkg_prefix="wrapper/enum_exporter")
      exp.dump_enums(opts)

    fout = os.path.join(stanza_dir, "Codes.stanza")
    with open_test(fout) as cap:
      exp = EnumExporter(cap, "Codes", [("ErrorCode", 10), ("WarnCode", 20), ("InfoCode", 30) ])

      opts = Namespace(pkg_prefix="wrapper/enum_exporter")
      exp.dump_enums(opts)

    fout = os.path.join(stanza_dir, "Wonky.stanza")
    with open_test(fout) as cap:
      exp = EnumExporter(cap, "Wonky", [("Jabber", -2), ("Wocky", -20), ("Walrus", 3000) ])

      opts = Namespace(pkg_prefix="wrapper/enum_exporter")
      exp.dump_enums(opts)

    sp.check_call("stanza build test_enum_exporter", cwd="./tests", shell=True)
    sp.check_call(["tests/bin/test_enum_exporter"], shell=True)

class NativeEnumExporterTests(unittest.TestCase):
  def test_native_exporter(self):
    """ Unit tests for the Native `defenum` exporter
    """

    stanza_dir = "tests/uut/enum_exporter/"
    fout = os.path.join(stanza_dir, "Faces.stanza")
    with open_test(fout) as cap:
      exp = NativeEnumExporter(cap, "Faces", [("Happy", 0), ("Sad", 1), ("Angry", 2) ])

      opts = Namespace(pkg_prefix="wrapper/enum_exporter")
      exp.dump_enums(opts)

    sp.check_call("stanza build test_native_enum_exporter", cwd="./tests", shell=True)
    sp.check_call(["tests/bin/test_native_enum_exporter"], shell=True)
