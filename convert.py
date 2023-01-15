import argparse
import os
import os.path
import sys
import logging
from collections import OrderedDict
from contextlib import contextmanager

from pycparser import c_parser, c_ast, parse_file
import pycparser_fake_libc

__version__ = "0.1.0"

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

class LBStanzaExporter(Exporter):
  """ Exporter with utility functions
  for creating LBStanza code.
  """
  RESERVED_WORDS = [
    "val", "var", "when", "if", "is", "is-not", "else", "defn", "defmethod",
    "defmulti", "lostanza", "public", "new", "to", "through", "by",
    "ptr", "int", "long", "double", "float", "char", "byte",
    "return", "label", "generate", "from", "defstruct", "with",
    "try", "catch", "finally", "attempt", "multifn", "deftype", "not",
    "match", "switch", "let", "let-var" "where", "in", "within", "while",
    "String", "Int", "Double", 
  ]

  def dump_autogen_header(self):
    self.lprint("; This file was auto-generated by lbstanza-wrapper")
    self.lprint("; Version {}".format(__version__))
    self.lprint("; Manual editing would be unwise")

  def dump_package_decl(self, prefix, pkgName, imports):
    self.lprint("defpackage {}/{} :".format(prefix, pkgName))
    with self.indented():
      for imp in imports:
        self.lprint("import {}".format(imp))
    self.lprint("")

class FuncDeclExporter(LBStanzaExporter):
  """ Function Declarations Exporter
  """

  def gen_func_type(self, argsList, retType):
    """ Generate the function type declaration
    in the form " (int, int) -> int "
    """
    args = ",".join([x[2] for x in argsList.values()])
    return "({}) -> {}".format(args, retType)

  def dump_static_decl(self, funcs):
    """ Dump static function declarations.
    @NOTE - the lack of prefix - this is because these function
      names are searched for in the compiled objects and must match
      as symbol names.
    """
    for name, data in funcs.items():
      argsList, retData, *others = data
      retType, isVoid, *_ = retData
      voidComment = ""
      if isVoid:
        voidComment = "  ;  void"
      funcType = self.gen_func_type(argsList, retType)
      self.lprint("extern {} : {}{}".format(name, funcType, voidComment))
  
  def dump_wrapper(self, funcs, deref=False):
    """ Generate the wrapper lostanza function that is used to make
    consistent calling interface from high stanza code.
    @note: These functions have the `w_` prefix.
    @param deref - selects between direct call and dereferenced call.
    """
    # public lostanza defn w_func_name (v:int) -> int :
    #   DEREF = True
    #   val ret = call-c [p_func_name](v)
    #   DEFER = FALSE
    #   val ret = call-c func_name(v)
    #   return ret

    def to_argdecl(k,v):
      return "{}:{}".format(k, v[2])

    for name, data in funcs.items():
      argsList, retData, *others = data
      retType, isVoid, *_ = retData
      argDecls = ", ".join([to_argdecl(k,v) for k,v in argsList.items()])
      fArgs = ", ".join(argsList.keys())

      if isVoid:
        retDecl = "ref<False>"
      else:
        retDecl = retType

      self.lprint("public lostanza defn w_{} ({}) -> {} :".format(name, argDecls, retDecl))
      with self.indented():
        retPrefix = "val ret = "
        if isVoid:
          retPrefix = ""
        if deref:
          self.lprint("{}call-c [p_{}]({})".format(retPrefix, name, fArgs))
        else:
          self.lprint("{}call-c {}({})".format(retPrefix, name, fArgs))
        # @NOTE - here it would be nice to be able to know if 
        #   this is a void or a true int return.
        #   We could then do `return false` here and 
        if isVoid:
          self.lprint("return false")
        else:
          self.lprint("return ret")

  def dump_static_wrapper(self, funcs):
    self.dump_wrapper(funcs, deref=False)

  def dump_dynamic_wrapper(self, funcs):
    self.dump_wrapper(funcs, deref=True)

  def dump_dynamic_ptr(self, funcs):
    """ Generate the pointer address import 
    Note that these values have the `p_` prefix.
    """
    #   lostanza val p_func_name: ptr<( (int) -> int )> =
    #     dynamic-library-symbol(lib, String("func_name")).address
    for name, data in funcs.items():
      argsList, retData, *others = data
      retType, isVoid, *_ = retData    
      funcType = self.gen_func_type(argsList, retType)
      self.lprint("lostanza val p_{}: ptr<({})> = ".format(name, funcType))
      with self.indented():
        self.lprint("dynamic-library-symbol(shlib, String(\"{}\")).address".format(name))
      self.lprint("")

  def dump_dynamic_lib(self, opts): 
    defName = opts.pkg_prefix
    defName = defName.replace("/", "-")
    varName = opts.pkg_prefix
    varName = varName.replace("/", "_").upper()
    lines = [
      "val DEF_LIB_PATH = \"./lib{}.dll\"".format(defName),
      "val ENV_LIB_PATH_NAME = \"{}_SHARED_LIB\"".format(varName),
      ""
      "defn get-shared-lib () -> String :",
      "  label<String> return:",
      "    var sharedLib = get-env(ENV_LIB_PATH_NAME)",
      "    match(sharedLib) :",
      "      (fpath:String) :",
      "        return(fpath)",
      "      (x:False):",
      "        return(DEF_LIB_PATH)",
      "",
      "val shlibPath = get-shared-lib()",
      "val shlib = dynamic-library-open(shlibPath)",
      "",
    ]
    for line in lines:
      self.lprint(line)

  def dump_dynamics(self, funcs, opts): 
    self.dump_dynamic_lib(opts)
    self.dump_dynamic_ptr(funcs)
    self.dump_dynamic_wrapper(funcs)


  def dump_both(self, funcs, opts):
    """ Generate both static and dynamic imports and
    use a compile time flag to 
    """
    self.lprint("#if-defined(COMPILE-STATIC):")
    with self.indented():
      self.dump_static_decl(funcs)
      self.dump_static_wrapper(funcs)
    self.lprint("#else:")
    with self.indented():
      self.dump_dynamics(funcs, opts)

  def dump_func_decls(self, funcs, opts):
    self.dump_autogen_header()
    imports = ["core", "core/dynamic-library"]
    self.dump_package_decl(opts.pkg_prefix, opts.pkg_name, imports)

    if opts.func_form == "static" : 
      self.dump_static_decl(funcs)
    elif opts.func_form == "dynamic" :
      self.dump_dynamics(funcs, opts) 
    elif opts.func_form == "both": 
      self.dump_both(funcs, opts)

class NativeEnumExporter(LBStanzaExporter):
  """ I implemented the original enum exportation code
  before I knew about `defenum` - unfortunately, `defenum`
  wasn't documented anywhere except in a file in the `examples`
  folder at the time I wrote this :(
  In any case - this is a better implementation for standard enum types
  that don't attempt to specify specific integer values. 
  If the enum that you are attempting to wrap contains a gap or 
  a starting number that is not 0 - then this will likely not work
  because there is no way to control the numbering like there is 
  in C. 
  """

  def __init__(self, fout, name, enumerators): 
    super().__init__(fout)
    self._name = name
    self._enumerators = enumerators

  def dump_enums(self, opts):
    self.dump_autogen_header()

    imports = ["core",]
    self.dump_package_decl(opts.pkg_prefix, self._name, imports)

    self.lprint("public defenum {}:".format(self._name))
    with self.indented():
      for eName, v in self._enumerators :
        self.lprint("{}".format(eName))
    self.lprint("")

    # I add a lostanza constructor for ease of use with 
    #  wrappers
    self.lprint("public lostanza defn {} (v:int) -> ref<{}> :".format(self._name, self._name))
    with self.indented():
      self.lprint("return {}(new Int{{v}})".format(self._name))
    self.lprint("")


class EnumExporter(LBStanzaExporter): 

  def __init__(self, fout, name, enumerators): 
    super().__init__(fout)
    self._name = name
    self._enumerators = enumerators

  def dump_enum_deftypes(self):
    self.lprint("public deftype {}".format(self._name))
    for eName, v in self._enumerators :
      self.lprint("public deftype {} <: {}".format(eName, self._name))
    self.lprint("")

  def dump_to_int(self):
    self.lprint("public defn to-int (v:{}) -> Int:".format(self._name))
    with self.indented():
      self.lprint("match(v) :")
      with self.indented():
        for eName, v in self._enumerators:
          self.lprint("(x:{}) : {}".format(eName,v))
    self.lprint("")

  def dump_constructor(self):
    self.lprint("public defn {} (v:Int) -> {} :".format(self._name, self._name))
    with self.indented():
      self.lprint("switch {v == _}:")
      with self.indented():
        for eName, v in self._enumerators :
          self.lprint("{} : new {}".format(v, eName))
        self.lprint("else: throw(Exception(\"{}: Invalid Enum Value: %_\" % [v]))".format(self._name))
    self.lprint("")

    self.lprint("public lostanza defn {} (v:int) -> ref<{}> :".format(self._name, self._name))
    with self.indented():
      self.lprint("return {}(new Int{{v}})".format(self._name))
    self.lprint("")

  def dump_print(self):
    self.lprint("public defmethod print (o:OutputStream, v:{}) :".format(self._name))
    with self.indented():
      self.lprint("match(v) :")
      with self.indented():
        for eName, v in self._enumerators :
          self.lprint("(x:{}) : print(o, \"{}\")".format(eName, eName))
    self.lprint("")


  def dump_enums(self, opts): 
    self.dump_autogen_header()

    imports = ["core",]
    self.dump_package_decl(opts.pkg_prefix, self._name, imports)
    self.dump_enum_deftypes()
    self.dump_to_int()
    self.dump_constructor()
    self.dump_print()


class FuncDeclVisitor(c_ast.NodeVisitor): 
  """ Extract Function Declarations into Stanza Syntax 
  
  This code will extract the function declarations and then
  output them in either `static`, `dynamic`, or `both`

  Static Form:  
    extern func_to_use : (int) -> int

  Dynamic Form:
    lostanza val p_func_to_use: ptr<( (int) -> int )> =
      dynamic-library-symbol(QRLIB, String("func_to_use")).address

    public lostanza defn w_func_to_use (v:int) -> int :
      val ret = call-c [p_func_to_use](v)
      return ret

  Both Form: 
    This form uses a compile time flag to differentiate between
    the two.
  
  #if-defined COMPILE-STATIC:
    extern func_to_use : (int) -> int

    public lostanza defn w_func_to_use (v:int) -> int :
      val ret = call-c func_to_use(v)
      return ret

  #else:
    lostanza val p_func_to_use: ptr<( (int) -> int )> =
      dynamic-library-symbol(QRLIB, String("func_to_use")).address

    public lostanza defn w_func_to_use (v:int) -> int :
      val ret = call-c [p_func_to_use](v)
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

def prep_args(opts):
  def to_header(fpath):
    return "-I" + fpath
  fake_libc_arg = to_header(pycparser_fake_libc.directory)
  others = [to_header(x) for x in opts.include]
  cpp_arg_list = others + [fake_libc_arg]
  cpp_args = " ".join(cpp_arg_list)
  return cpp_args

def process_func_decl(opts):
  cpp_args = prep_args(opts)
  node = parse_file(opts.input, use_cpp=True, cpp_args=cpp_args)
  v = FuncDeclVisitor(opts)
  v.visit(node)
  v.export()

def process_enums(opts):
  cpp_args = prep_args(opts)
  node = parse_file(opts.input, use_cpp=True, cpp_args=cpp_args)
  v = EnumVisitor(opts)
  v.visit(node)

def setup_opts():
  desc = """
  LBStanza C Wrapper Generator 

  This tool is used to generate wrappers around a C library (static or dynamic).

  This tool uses 'pycparser'. As such, you should follow instructions defined in
  that project for using the C preprocessor to message headers before feeding them
  to this tool (eg, 'gcc -E -std=c99 headers.h' ). 

  Function Declaration Generator 
  ------------------------------

  This sub-command will generate all the exported C function declarations
  as stanza external declarartions. 

  Static: 
    Generates the static extern definitions
    extern some_func : (int, int) -> int
  
  Dynamic
    Generates the dynamic shared library import format. 

    EXAMPLE:

      val DEF_LIB_PATH = "./libPREFIX.dll"
      val ENV_LIB_PATH_NAME = "PREFIX_SHARED_LIB"
      defn get-shared-lib () -> String :
        label<String> return:
          var sharedLib = get-env(ENV_LIB_PATH_NAME)
          match(sharedLib) :
            (fpath:String) :
              return(fpath)
            (x:False):
              return(DEF_LIB_PATH)
      
      val shlibPath = get-shared-lib()
      val shlib = dynamic-library-open(shlibPath)
      
      lostanza val p_SomeFunc: ptr<(int -> ptr<?>)> = 
        dynamic-library-symbol(shlib, String("SomeFunc")).address

      public lostanza defn w_SomeFunc (v:int) -> ptr<?> :
        val ret = call-c [p_SomeFunc](v)
        return ret

  Both 
    Generates both formats but with a compile time flag.

  Enum Generator
  --------------
  This sub-command will generate a stanza Enum definition for each 
  C-enum declaration. 

  For well-formed C-enums - this code will use the `defenum` construct
  in stanza. "Well-Formed" in this context means values start at zero and
  increase monotonically without gaps. 
  For non-"Well-Formed" C-enums, this will generate a backup implementation
  that is not as pretty or performant. 
  """
  parser = argparse.ArgumentParser(description=desc, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument("-i", "--input", type=str, help="Path to the header file that will be parsed for function declarations")
  parser.add_argument("-I", "--include", action="append", default=[], help="Add an additional search path for headers. This arg can be used multiple times.")  

  sub = parser.add_subparsers(help="Extraction Operations")

  ep = sub.add_parser("enums", help="Extract Enumerated Types into a Stanza Style")
  ep.add_argument("--pkg-prefix", help="Prefix string when declaring the 'defpackage'")
  ep.add_argument("--out-dir", help="Directory where stanza files will be created.")
  ep.add_argument("--dry-run", action="store_true", help="Generate all output to stdout instead of files in the `--out-dir`.")
  ep.add_argument("--use-defenum", action="store_true", help="Generate defenum structures for all well-formed C enums.")
  ep.add_argument("--skip", action="append", default=[], help="Don't generate any enumeration files for objects whose name matches the passed string. This argument can be used multiple times.")
  ep.set_defaults(func=process_enums)

  fp = sub.add_parser("func-decl", help="Extract Function Declarations into a Stanza Style")
  fp.add_argument("--pkg-prefix", help="Prefix string when declaring the 'defpackage'")
  fp.add_argument("--pkg-name", default="Wrapper", help="Name of the package containing the func decl. Default is '%(default)s'")
  fp.add_argument("--output", help="Output file that will contain the wrapper declarations")
  fp.add_argument("--func-form", required=True, choices=['static', 'dynamic', 'both'], help="Select which form of function declaration output to generate.")
  fp.add_argument("--dry-run", action="store_true", help="Generate all output to stdout instead of to file.")
  fp.add_argument("--dump-types", action="store_true", help="Dump the captured types, enums, structs, and functions to stdout.")
  fp.set_defaults(func=process_func_decl)

  opts = parser.parse_args()
  return opts

def main():
  opts = setup_opts()
  opts.func(opts)

if __name__ == "__main__":
    main()