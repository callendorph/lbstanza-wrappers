import os
import logging
import sys
from collections import OrderedDict
from pycparser import c_ast

from lbstanza_wrappers.Lbstanza import FuncDeclExporter, LBStanzaExporter

class FuncDeclVisitor(c_ast.NodeVisitor):
  """ Extract Function Declarations into Stanza Syntax

  This code will extract the function declarations and then
  output them in the following stanza form:

    extern func_to_use : (int) -> int

    public lostanza defn w_func_to_use (v:int) -> int :
      val ret = call-c func_to_use(v)
      return ret

  """
  STANZA_PRIMS = [
    "double", "float", "int", "long", "byte"
  ]

  # NOTE - the pycparser fake headers don't handle
  #   conversion of stdint.h types well, so I'm
  #   implementing a better mapping here.
  #
  #   The keys in this mapping are standard C type definitions.
  #   The values in this mapping should all be lbstanza primitives.
  #     The exceptions to this is for struct definitions (not struct ptrs, they are ptr<?>)
  #        and function pointer typedefs (not declarations).
  #     The struct definitions will use 'struct' as keyword. This is necessary because
  #        currently lbstanza doesn't handle passing struct by value.
  #     The function pointers will use 'funcdef'. This will make reference to the
  #        `self._funcdef` dict that will contain more info about that particular
  #        function pointer.
  FIXED_TYPE_MAPPING = {
    "double" : "double",
    "float" : "float",
    "int" : "int",
    "unsigned" : "int",
    "signed" : "int",
    "long" : "long",
    "char" : "byte",
    "void" : "void",
    "bool" : "byte", #  <-- GCC uses byte for this
    "Bool" : "int",
    "_Bool" : "int",
    "uint" : "int",
    "ulong" : "long",
    "uint32_t" : "int",
    "int32_t" : "int",
    "uint64_t" : "long",
    "int64_t" : "long",
    # What to do with `short` and `ushort` ?
    "short" : "int",
    "ushort" : "int",
  }

  FIXED_PTR_MAPPING = {
    "char" : "byte",
    "void" : "?",
    # This only affects pointers to structures
    #   if it is a struct by value - then we
    #   have to handle it a different way.
    "struct" : "?",
  }

  def __init__(self, opts):
    self._opts = opts
    super().__init__()
    self.parent = None

    self._types = dict(self.FIXED_TYPE_MAPPING)
    self._enums = {}
    self._fdefs = OrderedDict()
    self._funcs = OrderedDict()


  def generic_visit(self, node):
    """ Called if no explicit visitor function exists for a
        node. Implements preorder visiting of the node.
    """
    oldparent = self.parent
    self.parent = node
    for c in node:
        self.visit(c)
    self.parent = oldparent

  def convert_ptr_type(self, lbType, numPtrs):
    ptrType = self.FIXED_PTR_MAPPING.get(lbType, lbType)
    prefix = "ptr<" * numPtrs
    suffix = ">" * numPtrs
    return prefix + ptrType + suffix

  def capture_funcdef(self, node, numPtrs, fdef):
    """ Capture a Function Pointer Definition
    @param node
    """
    #import pdb; pdb.set_trace()
    lbType = "funcdef"
    if numPtrs > 0 :
      lbType = self.convert_ptr_type(lbType, numPtrs)
    store = self._types
    name = node.name
    existing = store.get(name)
    if existing is not None:
      logging.info("{}: Ignoring Existing FuncDef: {}".format(node.coord, name))
      return
    store[name] = lbType
    logging.debug("{}: Captured FuncDef: {}".format(node.coord, name))

    # Now we need to extract the function declaration - parameters and
    #   return arguments.
    args = self.get_args(fdef)
    retType = self.get_retType(fdef)

    self._fdefs[name] = (args, retType, fdef)

  def funcdef_to_stanza(self, data):
    args, retData, *others = data
    retType, *_ = retData
    argStr = ",".join([v[2] for k,v in args.items()])
    ret = "( ({}) -> {} )".format(argStr, retType)
    return ret

  def capture_typedef(self, node):
    """ Traverse the node tree to determine the type of
    declaration is expressed by this node.
    This compresses pointer types into a number of levels
      of redirection.
    """
    param = node
    numPtrs = 0
    while True:
      if type(param.type) is c_ast.TypeDecl:
        baseNode = param.type.type
        if type(baseNode) is c_ast.Struct:
          # This needs to be handled specially because
          #   stanza can't handle passing structs by value yet.
          lbType = "struct"
          if numPtrs > 0 :
            lbType = self.convert_ptr_type(lbType, numPtrs)
          store = self._types
          existing = store.get(param.type.declname)
          if existing is not None:
            logging.info("{}: Ignoring Existing Struct: {}".format(node.coord, param.type.declname))
            return
          store[param.type.declname] = lbType
          logging.debug("{}: Captured Struct: {} = {}".format(node.coord, param.type.declname, lbType))
        elif type(baseNode) is c_ast.IdentifierType:
          baseType = baseNode.names[-1]
          # Attempt to convert to lbtype - and if that
          #  doesn't work return the baseType - we will
          #  attempt a lookup later.
          lbType = self._types.get(baseType)
          if lbType is None:
            # This type is referencing a type we don't know about yet - that
            # is a little strange.
            raise RuntimeError("{}: Unhandled declaration base: {}".format(node.coord, baseNode))
          if numPtrs > 0:
            lbType = self.convert_ptr_type(lbType, numPtrs)

          existing = self._types.get(param.type.declname)
          if existing is not None:
            logging.info("{}: Ignoring Existing Type: {}".format(node.coord, param.type.declname))
            return

          self._types[param.type.declname] = lbType
          logging.debug("{}: Captured Identifier: {} = {}".format(node.coord, param.type.declname, lbType))
        elif type(baseNode) is c_ast.Enum:
          existing = self._enums.get(baseNode.name)
          if existing is not None:
            logging.info("{}: Ignoring Existing Enum: {}".format(node.coord, baseNode.name))
            return
          # Need to capture as an int
          self._types[param.type.declname] = "int"
          # But the function definition we will likely want
          #  to use a type definition.
          self._enums[param.type.declname] = [] # @TODO implement Enum List Capture
          logging.debug("{}: Captured Enum: {}".format(node.coord, param.type.declname))
        elif type(baseNode) is c_ast.Union:
          logging.warn("Ignoring Typedef of Base Union: {}".format(baseNode))
        else:
          raise RuntimeError("{}: Unhandled declaration base: {}".format(node.coord, baseNode))
        return
      elif type(param.type) is c_ast.PtrDecl:
        numPtrs += 1
        param = param.type
      elif type(param.type) is c_ast.IdentifierType:
        # No op - I don't think this make sense for a typedef
        pass
      elif type(param.type) is c_ast.FuncDecl:
        self.capture_funcdef(node, numPtrs, param.type)
        return
      elif type(param.type) is c_ast.ArrayDecl:
        numPtrs += 1
        param = param.type
      else:
        raise RuntimeError("{}: Unhandled Node in Declaration: {}".format(node.coord, node))

  def visit_Typedef(self, node):
    # We use this to capture the type declarations and
    #  Store a mapping of how translate these from C to Stanza
    #  Stanza has only a hand ful of types and so there is a need to
    #  handle conversion properly.
    self.capture_typedef(node)

  def visit_Decl(self, node):
    if type(node.type) is c_ast.FuncDecl:
      if node.name in self._funcs:
        logging.info("{}: Ignoring Existing Function Decl: {}".format(node.coord, node.name))
        return

      fdef = node.type
      argsList = self.get_args(fdef)
      retType = self.get_retType(fdef)

      self._funcs[node.name] = (argsList, retType, fdef)
      logging.debug("{}: Captured Function Decl: {}".format(node.coord, node.name))
    elif type(node.type) is c_ast.Struct:
      if node.name in self._types:
        logging.info("{}: Ignoring Existing Struct Decl: {}".format(node.coord, node.name))
        return
      self._types[node.name] = "struct"
      logging.debug("{}: Captured Struct Decl '{}' as Dummy Definition".format(node.coord, node.name))
    else:
      logging.warn("Unhandled Decl: {} type={}".format(node.name, node.type))


  def get_decl(self, param):
    p = param
    numPtrs = 0
    while True:
      if type(p.type) is c_ast.TypeDecl:
        baseType = p.type.type.names[-1]
        lbType = self._types.get(baseType)
        if lbType is None:
          raise ValueError("Failed to Find Type Mapping for TypeDecl '{}'".format(baseType))
        if "funcdef" in lbType:
          fdef = self._fdefs[baseType]
          fptrDecl = self.funcdef_to_stanza(fdef)
          lbType = lbType.replace("funcdef", fptrDecl)
          if numPtrs == 0:
            # Z3 uses function points and functions directly as
            #   values. This is a hack to work around.
            numPtrs = 1
        return p.type.declname, lbType, numPtrs
      elif type(p.type) in [c_ast.PtrDecl, c_ast.ArrayDecl]:
        numPtrs += 1
        p = p.type
      elif type(p.type) is c_ast.IdentifierType:
        baseType = p.type.names[-1]
        lbType = self._types.get(baseType)
        if lbType is None:
          raise ValueError("Failed to Find Type Mapping for Identifier '{}'".format(baseType))
        # @NOTE - this is primarily for parsing functions
        #   that return void.
        return "", lbType, numPtrs
        #return "void", "int", 0
      elif type(p.type) is c_ast.FuncDecl:
        raise NotImplementedError("Anonymous Function pointer types not handled yet")
      else:
        raise RuntimeError("{}: Unhandled Decl Type: {}".format(param.coord, p))

  def fix_arg_name(self, name, argMap):
    """ Stanza has some keywords that can't be used as variable names
      like `val`, `when`, etc. This function inspects the
    """

    if name is not None and name not in LBStanzaExporter.RESERVED_WORDS:
      return name

    if name is None:
      name = "missing_name"

    newName = name + "_v"
    i = 1
    while newName in argMap.keys():
      newName = name + "_v{}".format(i)
      i += 1
    return newName

  def get_args(self, n):
    ret = OrderedDict()
    if n.args is None:
      return ret
    for p in n.args.params:
      name, lbType, numPtrs = self.get_decl(p)

      if lbType == "void" and numPtrs == 0:
        # C functions with signature `int somefunc(void)` don't have any
        #  arguments so we just skip this.
        continue

      if numPtrs > 0 :
        completeType = self.convert_ptr_type(lbType, numPtrs)
      else:
        completeType = lbType

      name = self.fix_arg_name(name, ret)

      ret[name] = (lbType, numPtrs, completeType)

    return ret

  def get_retType(self, n):
    name, lbType, numPtrs = self.get_decl(n)
    isVoid = False
    if lbType == "void" and numPtrs == 0:
      # Stanza can't handle void return - it has to be
      #  int
      retType = "int"
      isVoid = True
    else:
      if numPtrs > 0:
        retType = self.convert_ptr_type(lbType, numPtrs)
      else:
        retType = lbType
    return retType, isVoid

  def dump_types(self):
    from pprint import pprint
    print("Enums:")
    pprint(self._enums)
    print("Types:")
    pprint(self._types)
    print("FuncDefs:")

    pprint([ (k,v[:2]) for k,v in self._fdefs.items()])
    print("Funcs:")
    fNames = list(self._funcs.keys())
    pprint(fNames)

  def export(self):
    """ Generate the exported stanza wrapper file for the
    captured header.
    """
    if self._opts.dump_types:
      self.dump_types()

    if self._opts.dry_run:
      fout = sys.stdout
    else:
      fout = open(self._opts.output, "w")

    exp = FuncDeclExporter(fout)
    exp.dump_func_decls(self._funcs, self._opts)
