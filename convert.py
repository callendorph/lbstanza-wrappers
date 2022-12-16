import argparse
import os
import os.path
import sys

from pycparser import c_parser, c_ast, parse_file
import pycparser_fake_libc

def eprint(*args, **kwargs):
  print(*args, file=sys.stderr, **kwargs)


class EnumVisitor(c_ast.NodeVisitor):
  """ Extract Enums into Stanza Syntax
  """

  def __init__(self, opts):
    self._opts = opts
    if os.path.exists(self._opts.out_dir):
      if not os.path.isdir(self._opts.out_dir):
        raise ValueError("Output Directory Exists but isn't a Directory")
    else:
      os.makedirs(self._opts.out_dir)

    super().__init__()

  def gen_enumerators(self, node):
    values = node.values
    currValue = 0
    for value in values:
      name = value.name
      if value.value is None:
        yield (name, currValue)
      else:
        try:
          currValue = int(value.value.value)
          yield (name, currValue)
        except Exception as exc:
          eprint("Enumerator[{}] : Failed Extract Value: {}".format(name, exc))
          eprint("Node: {}", value.value)

      currValue += 1

  def gen_stanza(self, name, enumerators, f=None):
    def lprint(*args, **kwargs):
      kwargs["file"] = f
      print(*args, **kwargs)

    lprint("defpackage {}/{} :".format(self._opts.pkg_prefix, name))
    lprint("  import core")
    lprint()
    lprint("public deftype {}".format(name))
    for eName, v in enumerators :
      lprint("public deftype {} <: {}".format(eName, name))

    lprint()
    lprint("public defn to-int (v:{}) -> Int:".format(name))
    lprint("  match(v) :")
    for eName, v in enumerators:
      lprint("    (x:{}) : {}".format(eName,v))
    lprint()
    lprint("public defn {} (v:Int) -> {} :".format(name, name))
    lprint("  switch {v == _}:")
    for eName, v in enumerators :
      lprint("    {} : new {}".format(v, eName))
    lprint("    else: throw(Exception(\"Invalid Exception Value\"))")
    lprint()
    lprint("public lostanza defn {} (v:int) -> ref<{}> :".format(name, name))
    lprint("  return {}(new Int{{v}})".format(name))
    lprint()
    lprint("defmethod print (o:OutputStream, v:{}) :".format(name))
    lprint("  match(v) :")
    for eName, v in enumerators :
      lprint("    (x:{}) : print(o, \"{}\")".format(eName, eName))
    lprint()

  def visit_TypeDecl(self, node):
    #print("Node: {}".format(node))
    declName = node.declname
    declType = node.type
    if not isinstance(declType, c_ast.Enum):
      return

    enumerators = list(self.gen_enumerators(declType))

    fpath = os.path.join(self._opts.out_dir, "{}.stanza".format(declName))
    with open(fpath, "w") as f:
      self.gen_stanza(declName, enumerators, f=f)

def process_enums(opts):
  fake_libc_arg = "-I" + pycparser_fake_libc.directory
  node = parse_file(opts.input, use_cpp=True, cpp_args=fake_libc_arg)
  v = EnumVisitor(opts)
  v.visit(node)

def setup_opts():
  parser = argparse.ArgumentParser()
  parser.add_argument("-i", "--input", type=str, help="Path to a file that will be parsed for function declarations")
  #parser.add_argument("-e", "--enums", action="store_true", help="Create Enum definitions")
  sub = parser.add_subparsers(help="Extraction Operations")
  ep = sub.add_parser("enums", help="Extract Enumerated Types into a Stanza Style")
  ep.add_argument("--pkg-prefix", help="Prefix string when declaring the 'defpackage'")
  ep.add_argument("--out-dir", help="Directory where stanza files will be created.")
  ep.set_defaults(func=process_enums)

  opts = parser.parse_args()
  return opts

def main():
  opts = setup_opts()
  opts.func(opts)

if __name__ == "__main__":
    main()