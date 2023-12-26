import os
import logging
import sys
from collections import OrderedDict
from pycparser import c_ast

from lbstanza_wrappers.Lbstanza import NativeEnumExporter, EnumExporter


class EnumVisitor(c_ast.NodeVisitor):
  """ Extract Enums into Stanza Syntax
  """

  def __init__(self, opts):
    self._opts = opts
    if not self._opts.dry_run:
      if os.path.exists(self._opts.out_dir):
        if not os.path.isdir(self._opts.out_dir):
          raise ValueError("Output Directory Exists but isn't a Directory")
      else:
        os.makedirs(self._opts.out_dir)

    self._enums = OrderedDict()

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
          # Sometimes this value can be set to a negative value
          #  and when that happens we get a `UnaryOp` node for the minus sign.
          #  Unfortunately, that opens up a bit of a bag of worms -
          #    do we use the AST to change this into python math and then
          #    compute the value ?
          obj = value.value
          if type(obj) is c_ast.Constant:
            currValue = int(obj.value, base=0)
            yield (name, currValue)
          elif type(obj) is c_ast.UnaryOp:
            if obj.op != '-':
              raise NotImplementedError("Unhandled Unary Op for Enum Value Def: {}".format(obj.op))
            currValue = int (obj.op + obj.expr.value, base=0)
            yield (name, currValue)
          else:
            raise NotImplementedError("Unhandled AST Node for Enum Value Extraction: {}".format(obj))
        except Exception as exc:
          logging.error("Enumerator[{}] : Failed Extract Value: {}".format(name, exc))
          logging.error("Node: {}", node)

      currValue += 1

  def is_well_formed(self, enumerators):
    """ This function attempts to determine whether the enumerators
    for this C enum are well formed. In this context, well-formed means:
      - Enumerators start at value 0
      - Enumerators are monotically increasing
      - Enumerators always increment by one for the next value (ie, there
         are no gaps.)
    """
    for i, e in enumerate(enumerators):
      eName, v = e
      if i != v:
        return False

    return True

  def visit_TypeDecl(self, node):
    #print("Node: {}".format(node))
    declName = node.declname

    if declName in self._opts.skip:
      return

    declType = node.type
    if not isinstance(declType, c_ast.Enum):
      return

    if declName in self._enums.keys():
      logging.info("Ignoring Duplicate Enum: {}".format(declName))
      return

    enumerators = list(self.gen_enumerators(declType))
    wellFormed = self.is_well_formed(enumerators)

    if wellFormed and self._opts.use_defenum:
      expCls = NativeEnumExporter
    else:
      expCls = EnumExporter

    if not self._opts.dry_run:
      fpath = os.path.join(self._opts.out_dir, "{}.stanza".format(declName))
      with open(fpath, "w") as f:
        exp = expCls(f, declName, enumerators)
        exp.dump_enums(self._opts)
    else:
        exp = expCls(sys.stdout, declName, enumerators)
        exp.dump_enums(self._opts)

    self._enums[declName] = enumerators