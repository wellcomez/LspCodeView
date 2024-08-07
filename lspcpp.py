"""


"""
from inspect import stack
from codetask import task_message, taskbase
from typing import Union
import logging
import os
import argparse
import subprocess
import json
from typing import Optional

from pydantic import BaseModel, FailFast
from config import config
from lspconfig import lspconfig, lspconfig_clangd
from lspconfig_go import lspconfgi_go
from lspconfig_python import lspconfig_pylsp, lspconfig_pyright
from planuml import planuml_to_image
import pylspclient
import threading
from pylspclient import LspClient, LspEndpoint
from pylspclient.lsp_pydantic_strcuts import SignatureHelp, TextDocumentIdentifier, TextDocumentItem, LanguageIdentifier, Position, Range, SymbolInformation, Location, SymbolKind
from cpp_impl import LspFuncParameter, LspFuncParameter_cpp
from common import Body, SubLine, from_file, location_to_filename, range_before, to_file, where_is_bin
import logging

from common import to_uri

logger = logging.getLogger('lsppython')
print(logger)
logger.critical("lspcpp begined")
pipelog = open("pipe.log", "w")
# DEFAULT_CAPABILITIES = {
#     'textDocument': {
#         'completion': {
#             'completionItem': {
#                 'commitCharactersSupport': True,
#                 'documentationFormat': ['markdown', 'plaintext'],
#                 'snippetSupport': True
#             }
#         }
#     }
# }
# DEFAULT_CAPABILITIES = {
#     'textDocument': {
#         'completion': {
#             'completionItem': {
#                 'commitCharactersSupport': True,
#                 'documentationFormat': ['markdown', 'plaintext'],
#                 'snippetSupport': True
#             }
#         }
#     }
# }

#
#
tokenTypes = set([
    "variable", "variable", "parameter", "function", "method", "function",
    "property", "variable", "class", "interface", "enum", "enumMember", "type",
    "type", "unknown", "namespace", "typeParameter", "concept", "type",
    "macro", "modifier", "operator", "bracket", "label", "comment"
])


def SymbolKindName(v):
    """Represents various symbol kinds like File, Module, Namespace, Package, Class, Method, etc."""

    if SymbolKind.File == v:
        return "File"
    if SymbolKind.Module == v:
        return "Module"
    if SymbolKind.Namespace == v:
        return "Namespace"
    if SymbolKind.Package == v:
        return "Package"
    if SymbolKind.Class == v:
        return "Class"
    if SymbolKind.Method == v:
        return "Method"
    if SymbolKind.Property == v:
        return "Property"
    if SymbolKind.Field == v:
        return "Field"
    if SymbolKind.Constructor == v:
        return "Constructor"
    if SymbolKind.Enum == v:
        return "Enum"
    if SymbolKind.Interface == v:
        return "Interface"
    if SymbolKind.Function == v:
        return "Function"
    if SymbolKind.Variable == v:
        return "Variable"
    if SymbolKind.Constant == v:
        return "Constant"
    if SymbolKind.String == v:
        return "String"
    if SymbolKind.Number == v:
        return "Number"
    if SymbolKind.Boolean == v:
        return "Boolean"
    if SymbolKind.Array == v:
        return "Array"
    if SymbolKind.Object == v:
        return "Object"
    if SymbolKind.Key == v:
        return "Key"
    if SymbolKind.Null == v:
        return "Null"
    if SymbolKind.EnumMember == v:
        return "EnumMember"
    if SymbolKind.Struct == v:
        return "Struct"
    if SymbolKind.Event == v:
        return "Event"
    if SymbolKind.Operator == v:
        return "Operator"
    if SymbolKind.TypeParameter == v:
        return "TypeParameter"
    return "Unknow"


class PrepareReturn(Location):
    data: str
    kind: SymbolKind
    selectionRange: Range
    name: str

    @staticmethod
    def create(data: dict, sym: SymbolInformation):
        ret = PrepareReturn(range=Range.parse_obj(data["range"]),
                            selectionRange=Range.parse_obj(
                                data["selectionRange"]),
                            kind=SymbolKind(data["kind"]),
                            data=data["data"],
                            uri=sym.location.uri,
                            name=sym.name)
        return ret

    def in_range(self, sym: SymbolInformation):
        if sym.location.uri != self.uri:
            return False
        if sym.kind != self.kind:
            return False
        if self.range.start.line != sym.location.range.start.line:
            return False
        if sym.name != self.name:
            return False
        return True


class Token:

    def __init__(self, location: Location) -> None:
        self.data = ""
        with open(from_file(location.uri), "r") as fp:
            lines = fp.readlines()
            if location.range.start.line == location.range.end.line:
                self.data = lines[location.range.start.
                                  line][location.range.start.
                                        character:location.range.end.character]
            else:
                self.data = lines[location.range.start.line][
                    location.range.start.character:] + lines[
                        location.range.end.line][:location.range.end.character]


class SymbolLocation:

    def __init__(self,
                 loc: Location,
                 symbol: Optional['Symbol'] = None,
                 name="") -> None:
        self.file = from_file(loc.uri)
        self.range = loc.range
        if len(name):
            self.name = name
        else:
            self.name = symbol.name if symbol != None else ""
        self.code = ""
        if len(self.name):
            xx = loc.copy()
            xx.range.start.character = 0
            xx.range.end.character = -1
            code = str(Body(xx))
            code = code.replace("\n", "")
            pos = code.find(self.name)
            if pos > 0:
                code = code[max(pos - 20, 0):min(pos + len(self.name) +
                                                 20, len(code))]
                self.code = "  " + \
                    code.replace(self.name, '''[u]%s[/u]''' % (self.name))

    def __str__(self) -> str:
        return " %s:%d" % (display_file_path(
            self.file), self.range.start.line) + self.code


class Symbol:
    sym: SymbolInformation
    members: list['Symbol'] = []
    cls: Optional['Symbol'] = None
    param: Optional[LspFuncParameter] = None

    def to_dict(self):  # type: ignore
        ret = {}
        ret['sym'] = self.sym.dict()
        ret['members'] = [a.to_dict() for a in self.members]
        if self.cls != None:
            ret['cls'] = {
                'sym': self.cls.sym.dict(),
            }
        return ret

    def all_call_symbol(self):
        ret: list[Symbol] = [self]
        ret.extend(self.members)
        return ret

    def __init__(self, sym: SymbolInformation) -> None:
        self.sym = sym
        self.__begin = sym.location.range.start
        self.__end = sym.location.range.end
        self.name = sym.name
        self.members = []
        self.cls = None
        if self.is_method() or self.is_function() or self.is_construct():
            self.param = LspFuncParameter_cpp(sym)

    def contain(self, node: 'Symbol'):
        if self.__end.line < node.__end.line:
            return False
        if self.__end.line == node.__end.line:
            return self.__end.character >= node.__end.character
        return True

        # self.othercls = []

    def find(self, node: 'CallNode') -> Optional['Symbol']:
        if node.sym.in_range(self.sym):
            return self
        for a in self.members:
            yes = node.sym.in_range(a.sym)
            if yes:
                return a
        for a in self.members:
            if a.sym.name == node.sym.name:
                return a
        return None

    def __str__(self) -> str:
        if self.is_class_define():
            return self.name
        cls = self.cls.sym.name + "::" if self.cls != None else ""
        return cls + self.sym.name + " %s::%d" % (from_file(
            self.sym.location.uri), self.sym.location.range.start.line)

    def symbol_display_name(self) -> str:
        if self.is_class_define():
            return self.name
        cls = self.cls.sym.name + "::" if self.cls != None else ""
        return cls + self.sym.name

    def symbol_sidebar_displayname(self, showspace=True) -> str:
        icon = "".join([" " if showspace else "", ICON.ICON(self), " "])
        if self.is_class_define():
            return icon + self.name
        if self.cls:
            return "".join([
                "    " if showspace else "", icon, self.name,
                str(self.param.displayname() if self.param != None else "")
            ])
        return icon + self.name

    def is_construct(self):
        return self.sym.kind == SymbolKind.Constructor

    def is_class_define(self):
        return self.sym.kind == SymbolKind.Class or self.sym.kind == SymbolKind.Struct

    def is_function(self):
        return self.sym.kind == SymbolKind.Function

    def is_member(self):
        a = self.sym.kind == SymbolKind.Field
        if a:
            pass
        return a

    def is_method(self):
        return self.sym.kind == SymbolKind.Method

    def find_members(self, syms: list[SymbolInformation], otherscls):
        yes = self.sym.kind == SymbolKind.Class or self.sym.kind == SymbolKind.Struct
        if yes == False:
            return syms
        while len(syms):
            s = syms[0]
            s1 = Symbol(s)
            if self.contain(s1) == False:
                return syms
            elif s.kind == SymbolKind.Method or s.kind == SymbolKind.Constructor:
                s1.cls = self
                self.members.append(s1)
            elif s.kind == SymbolKind.Field:
                self.members.append(s1)
                s1.cls = self
            elif s1.sym.kind == SymbolKind.Class or s1.sym.kind == SymbolKind.Struct:
                otherscls.append(s1)
                syms = s1.find_members(syms[1:], otherscls)
                continue
            syms = syms[1:]
        return syms


class ReadPipe(threading.Thread):

    def __init__(self, pipe):
        threading.Thread.__init__(self)
        self.pipe = pipe

    def run(self):
        line = self.pipe.readline().decode('utf-8')
        while line:
            # pipelog.write('pipe:'+ line)
            # pipelog.write("\n")
            logger.info(line)
            line = self.pipe.readline().decode('utf-8')


class CallHierarchyItem(BaseModel):
    name: str
    kind: SymbolKind
    range: Range
    uri: TextDocumentIdentifier
    selectionRange: Range

    def setvalue(self, sym: SymbolInformation):
        self.name = sym.name
        self.kind = sym.kind
        self.uri = TextDocumentIdentifier(uri=sym.location.uri)
        self.range = sym.location.range

        self.range.end = self.range.start
        self.range.end.character = self.range.start.character + len(self.name)
        self.range.end.character = self.range.start.character + len(self.name)
        self.selectionRange = self.range


class SymbolParser:
    symbol_col: int = -1
    location: Location

    def __init__(self, sym: SymbolInformation):
        self.name = sym.name
        self.location = sym.location
        self.kind = sym.kind
        self.symbol_line = self.location.range.start.line
        with open(from_file(self.location.uri), "r") as fp:
            lines = fp.readlines()
            line = lines[self.location.range.start.line]
            name = self.name
            index = name.rfind("::")
            if index > 0:
                name = name[index + 2:]
            self.symbol_col = line[self.location.range.start.character:].index(
                name) + self.location.range.start.character


class SemanticTokens(BaseModel):
    resultId: Optional[str]
    data: list[int]


class SemanticTokensEdit(BaseModel):
    start: int
    deleteCount: int
    data: Optional[list[int]]


class SemanticTokensDelta(BaseModel):
    resultId: Optional[str]
    edits: list[SemanticTokensEdit]


class LspClient2(LspClient):
    endpoint: LspEndpoint

    def __init__(self, lsp_endpoint: LspEndpoint):
        """

        Args:
            lsp_endpoint:
        """
        LspClient.__init__(self, lsp_endpoint)
        self.endpoint = lsp_endpoint

    def process(self):
        return self.endpoint.send_notification("$/progress")

    def index_status(self):
        ret = self.endpoint.call_method("textDocument/index")
        return ret

    def document_semantictokens_delta(
        self, file, token: SemanticTokens
    ) -> Union[SemanticTokens, SemanticTokensDelta, None]:
        method = "textDocument/semanticTokens/full/delta"
        ret = self.endpoint.call_method(
            method,
            textDocument=TextDocumentIdentifier(uri=to_file(file)),
            previousResultId=token.resultId)
        try:
            return SemanticTokens.parse_obj(ret)
        except:
            pass
        try:
            return SemanticTokensDelta.parse_obj(ret)
        except:
            pass
        return None

    def document_semantictokens_full(self, file) -> SemanticTokens:
        method = "textDocument/semanticTokens/full"
        ret = self.endpoint.call_method(
            method, textDocument=TextDocumentIdentifier(uri=to_file(file)))
        return SemanticTokens.parse_obj(ret)

    def code_action(self, file):
        return self.endpoint.call_method(
            "textDocument/codeAction",
            textDocument=TextDocumentIdentifier(
                uri=to_file(file),
                range=Range(  # type: ignore
                    start=Position(line=0, character=0),
                    end=Position(line=0, character=0))))

    def workspace_symbol(self, query: str):
        return self.endpoint.call_method("workspace/symbol", query=query)

    def callIncoming(self, param: PrepareReturn) -> list[PrepareReturn]:
        sss = dict(param)
        ret = self.endpoint.call_method("callHierarchy/incomingCalls",
                                        item=sss)

        def convert(s):
            try:
                from_ = s["from"]
                return PrepareReturn(data=from_["data"],
                                     kind=from_["kind"],
                                     range=Range.parse_obj(from_["range"]),
                                     selectionRange=Range.parse_obj(
                                         from_["selectionRange"]),
                                     uri=from_["uri"],
                                     name=from_["name"])
            except Exception as e:
                logger.exception(str(e))
                return None

        return [x for x in map(convert, ret) if x is not None]

    def callHierarchyPrepareLocation(self,
                                     sym: Location) -> list[PrepareReturn]:
        ret = self.endpoint.call_method(
            "textDocument/prepareCallHierarchy",
            textDocument=TextDocumentIdentifier(uri=sym.uri),
            position=sym.range.start)
        return ret

    def callHierarchyPrepare(self,
                             sym: SymbolInformation) -> list[PrepareReturn]:
        s = SymbolParser(sym)
        col = s.symbol_col
        line = s.symbol_line
        ret = self.endpoint.call_method(
            "textDocument/prepareCallHierarchy",
            textDocument=TextDocumentIdentifier(uri=sym.location.uri),
            position={
                "character": col,
                "line": line
            })
        ret = list(map(lambda x: PrepareReturn.create(x, sym), ret))
        return ret

    # def call_hierarchy_incoming_calls(self):
    #     self.endpoint.call_method("callHierarchy/incomingCalls")

    def references(self, file, col: int, line: int) -> list[Location]:

        def convert(s):
            try:
                return Location.parse_obj(s)
            except Exception as e:
                logger.exception(str(e))
                return None

        ret = self.endpoint.call_method(
            'textDocument/references',
            textDocument=TextDocumentIdentifier(uri=to_file(file)),
            context={"includeDeclaration": True},
            position={
                "character": col,
                "line": line
            })
        # return list(
        # filter(lambda x: x != None and x.range.start.line != line,
        #    map(convert, ret)))
        return [
            x for x in map(convert, ret)
            if x is not None and x.range.start.line != line
        ]


class project_config:
    compile_database: Union[None, str]
    workspace_root: str

    def __init__(self,
                 workspace_root: str,
                 compile_database: Union[None, str] = None) -> None:
        self.workspace_root = workspace_root
        self.compile_database = compile_database
        if compile_database is None:
            self.compile_database = os.path.join(self.workspace_root,
                                                 "compile_commands.json")

    # def open_all(self, client: 'lspcppclient'):
    #     if self.compile_database is None:
    #         raise Exception("compile_database is None")
    #     fp = open(self.compile_database, "r")
    #     if fp != None:
    #         dd = json.load(fp)
    #         for a in dd:
    #             client.open_file(a["file"])

    def create_workspace(
        self
    ) -> 'WorkSpaceSymbol':
        wk = WorkSpaceSymbol(self.workspace_root)
        # if add == False:
        #     return wk
        # if self.compile_database is None:
        #     logger.warning("compile_database is None")
        #     return wk
        # fp = open(self.compile_database, "r")
        # if fp != None:
        #     dd = json.load(fp)
        #     for a in dd:
        #         # print(a)
        #         code = client.open_file(a["file"])
        #         wk.add(code)
        return wk


class lspcppclient:
    languageId = LanguageIdentifier.CPP
    lsp_client: Optional[LspClient2] = None

    def get_refer_from_cursor(self, loc: Location,
                              text: str) -> list[SymbolLocation]:
        if self.lsp_client is None:
            return []
        file = from_file(loc.uri)
        col = loc.range.start.character
        line = loc.range.start.line
        ret = self.lsp_client.references(file, col, line)
        decl = self.get_decl(loc=loc)
        name = str(Body(decl)) if decl != None else ""
        return list(map(lambda x: SymbolLocation(loc=x, name=name), ret))

    def get_impl(self, loc: Location) -> Location | None:
        if self.lsp_client is None:
            return None
        ret = self.lsp_client.definition(
            textDocument=TextDocumentIdentifier(uri=loc.uri),
            position=loc.range.start)
        if isinstance(ret, Location):
            return ret
        if isinstance(ret, list) and len(ret) > 0:
            if isinstance(ret[0], Location):
                return ret[0]
        return None

    def get_decl(self, loc: Location) -> Location | None:
        if self.lsp_client is None:
            return None
        ret = self.lsp_client.declaration(
            textDocument=TextDocumentIdentifier(uri=loc.uri),
            position=loc.range.start)
        if isinstance(ret, Location):
            return ret
        if isinstance(ret, list) and len(ret) > 0:
            if isinstance(ret[0], Location):
                return ret[0]
        return None

    def close(self):
        if self.lsp_client != None:
            self.lsp_client.shutdown()
            self.lsp_client.exit()

    def get_class_symbol(self, file) -> list[Symbol]:
        ret = []
        symbols = self.get_document_symbol(file)
        while len(symbols):
            s = symbols[0]
            if s.kind == SymbolKind.Class or s.kind == SymbolKind.Struct:
                s1 = Symbol(s)
                symbols = s1.find_members(symbols[1:], ret)
                ret.append(s1)
                continue
            elif s.kind == SymbolKind.Function:
                s1 = Symbol(s)
                ret.append(s1)
            elif s.kind == SymbolKind.Method:
                s1 = Symbol(s)
                ret.append(s1)
            symbols = symbols[1:]
        return ret

    def get_document_symbol(self, file: str) -> list[SymbolInformation]:
        if self.lsp_client is None:
            return []
        x = TextDocumentIdentifier(uri=to_file(file))
        symbol = self.lsp_client.documentSymbol(x)
        return symbol  # type: ignore

    def get_symbol_reference(self,
                             symbol: SymbolInformation) -> list[Location]:
        if self.lsp_client is None:
            return []
        s = SymbolParser(symbol)
        is_cpp = False
        try:
            file = from_file(symbol.location.uri)
            is_cpp = file.split(".")[-1].lower() in ["cc", "cpp", "cxx"]
        except Exception as e:
            logger.exception(str(e))
            pass
        decal = None
        if is_cpp:
            try:
                decal = self.lsp_client.declaration(
                    textDocument=TextDocumentIdentifier(
                        uri=symbol.location.uri),
                    position=Position(
                        line=s.symbol_line,
                        character=s.symbol_col))[0]  # type: ignore
            except Exception as e:
                logger.exception(e)
                pass

        rets = self.get_reference(symbol.location.uri, s.symbol_col,
                                  s.symbol_line)

        def filter_head(x: Location):
            try:
                if decal != None:
                    if x.uri == decal.uri and x.range.start.line == decal.range.start.line:  # type: ignore
                        return False
            except Exception as e:
                logger.exception(e)
                pass
            return True

        return list(filter(filter_head, rets))

    def get_reference(self, file, col: int, line: int) -> list[Location]:
        if self.lsp_client is None:
            return []
        return self.lsp_client.references(file, col, line)

    def open_file(self, file):
        uri = to_file(file)
        relative_file_path = file
        import os
        if os.path.isabs(file) == False:
            raise Exception("path should be absolute path")
        uri = to_file(relative_file_path)
        text = open(relative_file_path, "r").read()
        version = 2
        if self.lsp_client != None:
            ret = self.lsp_client.didOpen(
                TextDocumentItem(uri=uri,
                                 languageId=self.languageId,
                                 version=version,
                                 text=text))
        return SourceCode(relative_file_path, self)


class lspcppclient_clangd(lspcppclient):
    def __init__(self, config: project_config,
                 json_rpc_endpoint: pylspclient.JsonRpcEndpoint,
                 _lspconfig: lspconfig) -> None:
        lsp_endpoint = LspEndpoint(json_rpc_endpoint)
        lsp_client = LspClient2(lsp_endpoint)
        process_id = None
        root_path = None
        assert (config.workspace_root != None)
        root_uri = to_file(config.workspace_root)
        data_path = config.compile_database
        # initialization_options = {
        #     "compilationDatabasePath": data_path
        # } if data_path != None else None
        initialization_options = {
            "clangdFileStatus": True,
        }
        capabilities = {
            "window": {
                'workDoneProgress': True
            },
            'textDocument': {
                'completion': {
                    'completionItem': {
                        'commitCharactersSupport': True,
                        'snippetSupport': True
                    }
                }
            }
        }

        trace = "off"
        workspace_folders = None
        initialize_response = lsp_client.initialize(process_id, root_path,
                                                    root_uri,
                                                    initialization_options,
                                                    capabilities, trace,
                                                    workspace_folders)
        print(json.dumps(initialize_response, indent=4))
        if initialize_response['serverInfo']['name'] != 'clangd':
            raise RuntimeError("failed to initialize lsp_client")
        lsp_client.initialized()
        self.lsp_client = lsp_client
        pass


class lspcppclient_pylsp(lspcppclient):
    languageId = LanguageIdentifier.PYTHON
    def __init__(self, config: project_config,
                 json_rpc_endpoint: pylspclient.JsonRpcEndpoint) -> None:
        lsp_endpoint = pylspclient.LspEndpoint(json_rpc_endpoint)
        lsp_client = LspClient2(lsp_endpoint)
        process_id = None
        root_path = None
        root_uri = to_uri(config.workspace_root)
        initialization_options = None
        DEFAULT_CAPABILITIES = {
            'textDocument': {
                'completion': {
                    'completionItem': {
                        'commitCharactersSupport': True,
                        'documentationFormat': ['markdown', 'plaintext'],
                        'snippetSupport': True
                    }
                }
            }
        }
        capabilities = DEFAULT_CAPABILITIES
        trace = "off"
        workspace_folders = None
        initialize_response = lsp_client.initialize(
            process_id, root_path, root_uri, initialization_options, capabilities, trace, workspace_folders)
        if initialize_response['serverInfo']['name'] != 'pylsp':
            raise RuntimeError("failed to initialize lsp_client")
        lsp_client.initialized()
        self.lsp_client = lsp_client
        pass


class lsp_server:
    _lspconfig: lspconfig
    p: subprocess.Popen
    cmd = []
    json_rpc_endpoint: pylspclient.JsonRpcEndpoint

    def __init__(self, lspconfig: lspconfig) -> None:
        self._lspconfig = lspconfig
        self.cmd = lspconfig.cmd
        pass

    def start(self):
        self.p = p = subprocess.Popen(self.cmd, stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        read_pipe = ReadPipe(self.p.stderr)
        read_pipe.start()
        self.json_rpc_endpoint = pylspclient.JsonRpcEndpoint(
            p.stdin, p.stdout)  # type: ignore

    def close(self):
        self.p.communicate()
        self.p.kill()


class lsp_server_cpp(lsp_server):
    def __init__(self, root, lspconfig: lspconfig):
        super().__init__(lspconfig=lspconfig)
        self.cmd = [
            where_is_bin("clangd"),
            "--compile-commands-dir=%s" % (root), "--background-index",
            "--background-index-priority=normal", "-j", "4"
            # "--log=verbose",
            # "--background-index"
        ]
        self.start()

    def newclient(self, confg: project_config) -> lspcppclient:
        # type: ignore
        return lspcppclient_clangd(confg, self.json_rpc_endpoint, self._lspconfig)


class lsp_server_python(lsp_server):
    def __init__(self, root, lspconfig: lspconfig):
        super().__init__(lspconfig=lspconfig)
        self.start()

    def newclient(self, confg: project_config) -> lspcppclient:
        return lspcppclient_pylsp(confg, self.json_rpc_endpoint)


# DEFAULT_ROOT = path.abspath("./tests/test-workspace/cpp")
work_space_root: Optional[str] = None


class ICON:
    Text = "󰉿"
    Method = "ƒ"
    Function = ""
    Constructor = ""
    Field = "󰜢"
    Variable = "󰀫"
    Class = "𝓒"
    Interface = ""
    Module = ""
    Property = "󰜢"
    Unit = "󰑭"
    Value = "󰎠"
    Enum = ""
    Keyword = "󰌋"
    Snippet = ""
    Color = "󰏘"
    File = "󰈙"
    Reference = "󰈇"
    Folder = "󰉋"
    EnumMember = ""
    Constant = "󰏿"
    Struct = "𝓢"
    Event = ""
    Operator = "󰆕"
    TypeParameter = ""

    @staticmethod
    def ICON(s):
        return ICON.Method if s.is_method() else ICON.Field if s.is_member(
        ) else ICON.Class if s.is_class_define(
        ) else ICON.Function if s.is_function(
        ) else ICON.Constructor if s.is_construct() else "?"


def display_file_path(uri: str) -> str:
    global work_space_root
    path = from_file(uri).replace(
        work_space_root if work_space_root != None else "", "")

    i = 0
    while i < len(path) and path[i] == '/':
        i += 1
    return path[i:]


callnode_id = 1


class CallNode:
    symboldefine: Union[Symbol, None] = None
    detail: str = ""
    line: str = ""
    callee: Optional['CallNode'] = None
    status: str = ""
    resolved = False
    id: int

    def to_dict(self):  # type: ignore
        ret = {}
        ret['resolved'] = self.resolved
        if self.symboldefine != None:
            ret['symboldefine'] = self.symboldefine.to_dict()
        ret['status'] = ""
        return ret

    def __init__(self, sym: PrepareReturn) -> None:
        self.sym = sym
        self.callee = None
        self.param = ""
        global callnode_id
        self.id = callnode_id + 1
        callnode_id = self.id

    def get_cls_name(self) -> str:
        cls = self.get_cls()
        if cls != None:
            return cls.name
        return ""

    def get_cls(self) -> Optional[Symbol]:
        if self.symboldefine == None:
            return None
        return self.symboldefine.cls

    def displayname(self):
        return self.stack_display_name(0)

    def printstack(self, level=0, fp=None):
        sss = self.stack_display_name(level)
        print(sss)
        if fp != None:
            fp.write(sss)
            fp.write("\n")
            fp.flush()
        if self.callee != None:
            self.callee.printstack(level=level + 1, fp=fp)

    def filename(self):
        f = location_to_filename(self.sym)
        cls = self.get_cls()
        classname = cls.name + \
            "::" if cls != None else ""
        sss = classname + self.sym.name + f
        return sss

    def stack_display_name(self, level):
        cls = self.get_cls()
        classname = cls.name + \
            "::" if cls != None else ""
        sss = " " * level + "->" + classname + self.sym.name + self.param + " " + "%s:%d" % (
            display_file_path(self.sym.uri), self.sym.range.start.line)

        return sss

    def resolve_all(self, wk: 'WorkSpaceSymbol', cb=None):
        stack = self.callstack()
        completed = 0
        if cb != None:
            cb(0, len(stack))
        for index in range(len(stack)):
            s = stack[index]
            s.resolve(wk)
            completed += 1
            if cb != None:
                cb(completed, len(stack))
        if cb != None:
            cb(completed, len(stack))
        self.resolved = True

    def resolve(self, wk: 'WorkSpaceSymbol'):
        if self.symboldefine != None:
            return
        self.symboldefine = wk.find(self)
        if self.symboldefine != None:
            if len(self.line) == 0:
                self.param = wk.get_parama(self)
            self.detail = str(self.symboldefine)

    def uml(self,
            wk: Optional['WorkSpaceSymbol'] = None,
            markdown=False) -> str:
        stack = self.callstack()

        def fix(node: CallNode):
            if node.symboldefine == None:
                return node
            try:
                xx = node.symboldefine.name.rindex("::")
                clasname = node.symboldefine.name[:xx]
                fn = node.symboldefine.name[xx + 2:]
                node.symboldefine.name = fn
                if node.symboldefine.cls == None and node.symboldefine != None:
                    node.symboldefine.cls = Symbol(
                        node.symboldefine.sym)  # type: ignore
                    node.symboldefine.cls.name = clasname  # type: ignore
                    pass
            except Exception as e:
                logger.warn(e)
                pass
            return node

        stack = list(map(fix, stack))

        ret = []
        caller: Union[CallNode, None] = None

        def is_function(caller: CallNode):
            r = caller.sym.kind == SymbolKind.Function
            cls = caller.get_cls()
            if r == False and cls == None:
                if wk != None:
                    caller.symboldefine = None
                    wk.find(caller)
                pass
            return r

        title = ""
        for s in stack:
            right_prefix = ""
            if is_function(s) == False:
                right_prefix = s.symboldefine.cls.name.replace(  # type: ignore
                    "::",  # type: ignore
                    ".") + "::"
            right = right_prefix + s.symboldefine.name  # type: ignore
            if len(ret) == 0:
                title = "==%s==" % (right)
            if is_function(s) == False:
                left = s.symboldefine.cls.name  # type: ignore
                if caller != None:
                    if is_function(caller):
                        left = caller.symboldefine.name  # type: ignore
                    else:
                        if caller.symboldefine.cls.name != s.symboldefine.cls.name:  # type: ignore
                            left = caller.symboldefine.cls.name  # type: ignore
                ret.append("%s -> %s" % (left.replace("::", "."), right))
            else:
                if caller != None:
                    left = caller.symboldefine.cls.name if is_function(  # type: ignore
                        caller
                    ) == False else caller.symboldefine.name  # type: ignore
                    ret.append("%s -> %s" % (left.replace("::", "."), right))
                else:
                    pass
            caller = s
            pass
        mark_begin = "```plantuml" if markdown else ""
        sss = [mark_begin, "@startuml", "autoactivate on", title]
        sss.extend(ret)
        mark_end = "```" if markdown else ""
        sss.extend(["@enduml", mark_end, "\n" * 3])
        return "\n".join(sss)

    def callstack(self) -> list['CallNode']:
        ret: list[CallNode] = [self]
        next = self.callee
        while next != None:
            ret.append(next)
            next = next.callee
        return ret


class CallerWalker:
    maxlevel = config.load().get("maxlevel", 15)

    def __init__(self, client: lspcppclient,
                 workspaceSymbol: 'WorkSpaceSymbol') -> None:
        self.caller_set = []
        self.client = client
        self.workspaceSymbol = workspaceSymbol
        pass

    def __get_caller_next(self,
                          node: CallNode,
                          once=False,
                          level=10) -> list[CallNode]:
        if level > CallerWalker.maxlevel:
            return [node]
        # print(node.sym.name, node.sym.uri, len(self.caller_set))
        param = node.sym

        has = list(filter(lambda x: x.range == param.range, self.caller_set))
        self.caller_set.append(param)
        if self.client.lsp_client == None:
            return []
        parent = self.client.lsp_client.callIncoming(param)
        caller = list(map(lambda x: CallNode(x), parent))
        if once:
            return caller
        if len(has) == True and len(caller):
            return []
        for a in caller:
            a.callee = node
        if len(caller) == 0:
            return [node]
        ret = []
        for a in caller:
            next = self.__get_caller_next(a, level=level + 1)
            ret.extend(next)
        return ret

    def get_caller(self, sym: Symbol, once=False) -> list[CallNode]:
        if sym.is_function() or sym.is_method() or sym.is_construct():
            if self.client.lsp_client == None:
                return []
            ctx = self.client.lsp_client.callHierarchyPrepare(sym.sym)
            callser: list[CallNode] = []
            for a in ctx:
                c = CallNode(a)
                callser.extend(self.__get_caller_next(c, once, level=0))
            return callser
        return []


class SourceCode:
    tokenFull: Optional[SemanticTokens] = None
    tokenDelta: Union[SemanticTokens, SemanticTokensDelta, None] = None
    file: str
    symbols: list[SymbolInformation]
    class_symbol: list[Symbol]

    def __init__(self, file, client: lspcppclient) -> None:
        self.file = file
        self.lines = open(file, 'r').readlines()
        self.symbols = client.get_document_symbol(file)
        self.class_symbol = client.get_class_symbol(file)
        self.client = client

        if self.client.lsp_client != None:
            try:
                self.tokenFull = self.client.lsp_client.document_semantictokens_full(
                    self.file)
                self.tokenDelta = self.client.lsp_client.document_semantictokens_delta(
                    self.file, self.tokenFull)
            except Exception as e:
                logger.exception(str(e))
                pass
        pass

    def find(self, node: CallNode) -> Union[Symbol, None]:
        ret = self.__find(node)
        if ret != None:
            if ret.name != node.sym.name:
                ret = self.__find(node)
                pass
        return ret

    def __find(self, node: CallNode) -> Union[Symbol, None]:
        for a in self.class_symbol:
            r = a.find(node)
            if r != None:
                return r
            pass
        for s in self.symbols:
            if s.name.find(node.sym.name) > -1 and s.kind == node.sym.kind:
                ret = Symbol(s)
                return ret
        return None


class lspcs:
    serv: lsp_server
    client: lspcppclient

    def close(self):
        self.client.close()
        self.serv.close()

    def __init__(self, cls, lspconfig: lspconfig, cfg: project_config) -> None:
        self.serv = cls(cfg, lspconfig)
        self.client = self.serv.newclient(cfg)  # type: ignore
        pass


class _lspfactory:
    cpp_cs: Optional[lspcs] = None
    py_cs: Optional[lspcs] = None

    def __init__(self, root: str) -> None:
        self.cfg = project_config(workspace_root=root)
        self.root = root
        self.cpp = lspconfig_clangd()
        pylsp = True
        self.py = lspconfig_pylsp() if pylsp else lspconfig_pyright()
        self.go = lspconfgi_go()

        def __clangclient():
            if self.cpp_cs is None:
                try:
                    self.cpp_cs = lspcs(cls=lsp_server_cpp,
                                        lspconfig=self.cpp, cfg=self.cfg)
                    return self.cpp_cs.client
                except Exception as e:
                    pass
            else:
                return self.cpp_cs.client

        def __pythonclient():
            if self.py_cs is None:
                try:
                    self.py_cs = lspcs(cls=lsp_server_python,
                                       lspconfig=self.cpp, cfg=self.cfg)
                    return self.py_cs.client
                except Exception as e:
                    return None
            else:
                return self.py_cs.client

        self.lspconfig = {
            # "go":(self.go,self.__clangclient),
            "py": (self.py, __pythonclient),
            "cpp": (self.cpp, __clangclient)
        }
        pass

    def get_client(self, file):
        for a in self.lspconfig:
            config = self.lspconfig[a]
            if config[0].is_me(file):
                return config[1]()

    def close(self):
        if self.py_cs != None:
            self.py_cs.close()
        if self.cpp_cs != None:
            self.cpp_cs.close()


class WorkSpaceSymbol:
    factory: _lspfactory

    def __init__(self, root: str) -> None:
        self.source_list = {}
        self.root = root
        global work_space_root
        work_space_root = root
        self.factory = _lspfactory(root)

        pass

    def close(self):
        self.factory.close()

    def client(self, lang) -> lspcppclient:
        return self.factory.get_client(lang)  # type: ignore

    def create_source(self, file) -> 'SourceCode':
        if file in self.source_list.keys():
            return self.source_list[file]
        return self.client(file).open_file(file)

    def get_source(self, file) -> Optional['SourceCode']:
        return self.source_list[file]

    def add(self, s: SourceCode):
        self.source_list[s.file] = s

    def get_parama(self, node: CallNode) -> str:
        key = from_file(node.sym.uri)
        try:
            code: SourceCode = self.source_list[key]

            s = code.lines[node.sym.range.end.line]
            begin = s.find("(")
            ret = ""
            if begin > -1:
                begin = begin + 1
                ret = s[begin:]
            end = s.find(")")
            if begin > -1 and end > -1:
                ret = s[begin:end]
            if end < 0:
                i = node.sym.range.end.line + 1
                while i < len(code.lines):
                    s = code.lines[i]
                    i = i + 1
                    if begin == -1:
                        begin = s.find("(")
                    if end == -1:
                        end = s.find(")")
                    if begin > -1:
                        if len(ret) == 0:
                            ret = ret[begin + 1:]
                        if end > -1:
                            ret = ret + s[:end]
                            break
                        else:
                            ret = ret + s
            ret = ret.replace("\n", "")
            ss = ret.split(",")

            def formatspace(s):
                return " ".join(
                    list(filter(lambda x: len(x) > 0, s.split(' ')))[:-1])

            return "(%s)" % (",".join(map(formatspace, ss)))
        except Exception as e:
            logger.exception(str(e))
        return ""

    def find(self, node: CallNode) -> Union[Symbol, None]:
        key = from_file(node.sym.uri)
        try:
            code = self.source_list[key]
            return code.find(node)
        except Exception as e:
            logger.exception(str(e))
        try:
            self.add(self.client(key).open_file(key))
            return self.find(node)
        except Exception as e:
            logger.exception(str(e))
            return None


class Output:

    def __init__(self, name) -> None:
        self.name = name
        pass

    def close(self):
        pass

    def write(self, s):
        pass

    def flush(self):
        pass


class OutputFile(Output):

    def __init__(self, name) -> None:
        super().__init__(name)
        self.fp = open(name, "w")

    def write(self, s):
        self.fp.write(s)

    def flush(self):
        self.fp.flush()

    def close(self):
        self.fp.close()


class task_callback:
    toFile: Optional[Output] = None
    toUml: Optional[Output] = None

    def __init__(self) -> None:
        pass

    def update(self, a):
        pass


class task_call_in(taskbase):
    method: SymbolInformation
    resolve_task_list: list['subtask'] = []

    class message(task_message):
        task: 'task_call_in'
        node: Optional[CallNode] = None

        def __init__(self,
                     task: 'task_call_in',
                     updated_node: Optional['CallNode'] = None) -> None:
            super().__init__()
            self.task = task
            self.node = updated_node

    def __init__(self, wk: WorkSpaceSymbol, client: lspcppclient,
                 method: SymbolInformation, cb: task_callback, once) -> None:
        self.client = client
        self.wk = wk
        self.method = method
        self.toFile = cb.toFile
        self.uml = cb.toUml != None
        self.toUml = cb.toUml
        self.cb = cb
        self.once = once
        self.callin_all = []
        import codetask
        codetask.task_seq = +1
        self.id = codetask.task_seq
        self.processed = 0
        # self.pendding = 0
        pass

    def all_stacknode_cout(self):
        n = 0
        for node in self.callin_all:
            n += len(node.callstack())
        return n

    def run(self):
        self.processed = 0
        self.callin_all = []
        walk = CallerWalker(self.client, self.wk)
        ret = walk.get_caller(Symbol(self.method), once=False)
        self.callin_all = ret
        self.cb.update(task_call_in.message(self))

    def deep_resolve_at(self, index):
        node = self.callin_all[index]
        # if node.resolved:
        #     return
        found = list(filter(lambda x: node == x.node, self.resolve_task_list))
        if len(found):
            return
        t = subtask(node, self)
        self.resolve_task_list.append(t)
        t.run()
        self.resolve_task_list.remove(t)
        self.cb.update(task_call_in.message(self))

    def ensureroot(self):
        dirname = location_to_filename(
            self.method.location) + "_" + self.method.name
        dirname = os.path.join(os.path.dirname(__file__), "export",
                               dirname.replace(".", "_"))
        dirname = dirname.replace(" ", "")
        if os.path.exists(dirname):
            return dirname
        try:
            os.makedirs(dirname)
            if os.path.exists(dirname):
                return dirname
        except:
            pass
        return None

    def deep_resolve(self):
        if self.toFile != None:
            self.toFile.write("callin_all %d" % (len(self.callin_all)))
        for i in range(len(self.callin_all)):
            self.deep_resolve_at(i)

    def node_file_name(self, a: CallNode, markdown=False):
        root = self.ensureroot()
        if root is None:
            return None
        name = a.callstack()[0].filename()
        ext = ".md" if markdown else ".puml"
        filepath = os.path.join(root, name + ext)
        return filepath

    def check_node_resoved(self, a: CallNode):
        try:
            p = self.node_file_name(a)
            if p is None:
                return False
            return os.path.exists(p)
        except Exception as e:
            logger.error(str(e))

    def save_uml_tofile(self, a: CallNode, s: str, markdown: bool):
        root = self.ensureroot()
        name = a.callstack()[0].filename()
        if root != None:
            try:
                ext = ".md" if markdown else ".puml"
                filepath = os.path.join(root, name + ext)
                with open(filepath, "w") as fp:
                    fp.write(s)

                if markdown == False:
                    planuml_to_image(filepath, root)
            except Exception as e:
                logger.error(str(e))
                if self.toFile != None:
                    self.toFile.write(str(e) + "\n")
                pass
            pass
            try:
                ext = ".stack.json"
                filepath = os.path.join(root, name + ext)
                with open(filepath, "w") as fp:

                    def default_serializer(obj):
                        if isinstance(obj, CallNode):
                            return obj.to_dict()

                    json.dump(a.callstack(),
                              fp,
                              indent=4,
                              default=default_serializer)
            except Exception as e:
                logger.error(str(e))
                if self.toFile != None:
                    self.toFile.write(str(e) + "\n")
                pass

    def displayname(self):
        total = 0
        done = 0
        for item in self.resolve_task_list:
            total += item.total
            done += item.done
        substate = "" if total == 0 else "sub->%d/%d " % (done, total)

        state1 = "[%d/%d/%d] " % (self.processed, len(
            self.callin_all), len(self.resolve_task_list))
        data = Body(self.method.location).data.replace("\n", "")
        return data + "%s%s %s:%d" % (
            state1, substate, display_file_path(self.method.location.uri),
            self.method.location.range.start.line)


class subtask:
    node: CallNode
    task: task_call_in
    total = 0
    done = 0

    def __init__(self, a: CallNode, task: task_call_in) -> None:
        self.node = a
        self.task = task
        pass

    def run(self):
        task = self.task
        a = self.node
        task.cb.update(task_call_in.message(task))

        def fn(done, total):
            self.total = total
            self.done = done
            task.cb.update(task_call_in.message(task, self.node))
            pass

        a.resolve_all(task.wk, fn)
        a.printstack(fp=task.toFile)
        try:
            uml = task.uml
            if uml:
                markdown_it = False
                s = a.uml(wk=task.wk, markdown=markdown_it)
                task.save_uml_tofile(a, s, markdown=markdown_it)
                print(s)
                toUml = task.toUml
                if toUml != None:
                    toUml.write(s)
                    toUml.write("\n")
                    toUml.flush()
        except Exception as e:
            logger.exception(str(e))
            pass
        task.cb.update(task_call_in.message(task, a))
        task.processed += 1  # a.printstack(fp=self.toFile)


class SymbolFile:
    save_uml_file: Union[Output, None]
    save_stack_file: Union[Output, None]
    symbols_list: list[Symbol] = []
    wk: WorkSpaceSymbol
    sourcecode: SourceCode
    file: str

    def __init__(self, file, wk: WorkSpaceSymbol) -> None:
        self.save_stack_file = None
        self.save_uml_file = None
        self.wk = wk
        # self.root = wk.root
        self.sourcecode = wk.create_source(file)
        self.file = self.sourcecode.file

    def reset(self):
        if self.save_stack_file != None:
            self.save_stack_file.close()
        if self.save_uml_file != None:
            self.save_uml_file.close()

        self.save_stack_file = self.save_uml_file = None

    def get_class_symbol_list(self) -> list[Symbol]:

        def update_cls(a: Symbol, name: str, cls: Symbol):
            a.name = name
            a.cls = cls
            cls.members.append(a)

        symbols_list = []
        cimpl = {}
        for a in self.sourcecode.class_symbol:
            if a.is_class_define():
                if len(a.members):
                    symbols_list.append(a)
                else:
                    cimpl[a.name] = a
            elif a.is_method():
                name = a.sym.name
                classname = None
                index = name.rfind("::")
                if index > 0:
                    a = Symbol(a.sym)
                    classname = name[:index]
                    name = name[index + 2:]
                    if (classname in cimpl.keys()) == False:
                        cls = Symbol(a.sym.copy())
                        cls.name = classname
                        cls.sym.kind = SymbolKind.Class
                        cimpl[classname] = cls
                        symbols_list.append(cls)
                    update_cls(a, name, cimpl[classname])
                    pass
            else:
                symbols_list.append(a)
        return symbols_list

    def get_symbol_list(self) -> list[Symbol]:
        if (len(self.symbols_list)):
            return self.symbols_list
        symbols_list = []
        cimpl = {}
        for a in self.sourcecode.class_symbol:
            if a.is_class_define():
                if len(a.members):
                    symbols_list.append(a)
                    x = sorted(a.members, key=lambda x: x.name.lower())
                    symbols_list.extend(x)
                else:
                    cimpl[a.name] = a
            elif a.is_method():
                name = a.sym.name
                classname = None
                index = name.rfind("::")
                if index > 0:
                    classname = name[:index]
                    name = name[index + 2:]
                    try:
                        cls = cimpl[classname]
                        a.name = name
                        cls.members.append(a)
                        a.cls = cls
                    except:
                        cls = Symbol(a.sym.copy())
                        cls.name = classname
                        cls.sym.kind = SymbolKind.Class
                        cimpl[classname] = cls
                        symbols_list.append(cls)
                    pass
            else:
                symbols_list.append(a)
        for k in cimpl.values():
            symbols_list.append(k)
            symbols_list.extend(k.members)
        self.symbols_list = symbols_list
        return symbols_list

    def get_symbol_list_string(self) -> list[str]:
        sss = self.get_symbol_list()

        return list(map(lambda x: x.symbol_sidebar_displayname(), sss))

    def print(self):
        for s in self.get_symbol_list():
            print("%s %-10s" %
                  (SymbolKindName(s.sym.kind), s.symbol_sidebar_displayname()))

    def refer_symbolinformation(self,
                                sym: SymbolInformation,
                                toFile: Union[Output, None] = None):
        s = Symbol(sym)
        refs = self.sourcecode.client.get_symbol_reference(sym)
        ret = []
        for r in refs:
            ret.append(SymbolLocation(r, s))
            v = "Reference " + s.name + " %s:%d" % (from_file(
                r.uri), r.range.start.line)
            print(v)
            if toFile != None:
                toFile.write(v)
        return ret

    def refer(self, method, toFile: Union[Output, None] = None):
        symbo = self.find(method, False)
        print("Symbol number:", len(symbo))
        if toFile != None:
            toFile.write("Symbol number:%d" % (len(symbo)))
        ret = []
        for s in symbo:
            refs = self.sourcecode.client.get_symbol_reference(s.sym)
            for r in refs:
                ret.append(SymbolLocation(r, s))
                v = "Reference " + s.name + " %s:%d" % (from_file(
                    r.uri), r.range.start.line)
                print(v)
                if toFile != None:
                    toFile.write(v)
        return ret

    def find(self, method, Print=False) -> list[Symbol]:

        def find_fn(x: Symbol):
            if x.name == method:
                return True
            return method.find("::" + x.name) > 0

        symbo = list(filter(find_fn, self.symbols_list))
        if Print:
            for i in symbo:
                print(i)
        return symbo

    def callin(self,
               method: SymbolInformation,
               cb: task_callback,
               once=True) -> task_call_in:
        return task_call_in(self.wk,
                            self.sourcecode.client,
                            method=method,
                            cb=cb,
                            once=once)

    def call(self,
             method,
             uml=False,
             once=True,
             toFile: Union[Output, None] = None,
             toUml: Union[Output, None] = None):
        symbo = self.find(method)
        walk = CallerWalker(self.sourcecode.client, self.wk)
        ret: list[CallNode] = walk.get_caller(Symbol(symbo[0].sym), once=once)
        for a in ret:
            a.resolve_all(self.wk, cb=None)
            stack = a.callstack()
            a.printstack(fp=toFile)
            for ss in stack:
                ss.resolve(self.wk)
            try:
                if uml:
                    s = a.uml(wk=self.wk)
                    print(s)
                    if toUml != None:
                        toUml.write(s)
                        toUml.write("\n")
                        toUml.flush()
            except Exception as e:
                logger.exception(str(e))
                pass


class LspMain:
    opened_files: list[SymbolFile] = []
    currentfile: SymbolFile

    def __init__(self, root, file) -> None:
        if file != None and os.path.isabs(file) == False:
            file = os.path.join(root, file)
        print(root, file)
        cfg = project_config(workspace_root=root)
        wk = cfg.create_workspace()
        self.wk = wk
        self.root = root
        self.changefile(file)

    def client(self, location: Location):
        return self.wk.client(from_file(location.uri))

    def find_symbol_file(self, file: str) -> Optional[SymbolFile]:
        for f in self.opened_files:
            if f.sourcecode.file == file:
                return f
        return None

    def changefile(self, file) -> SymbolFile:
        for f in self.opened_files:
            if f.sourcecode.file == file:
                self.currentfile = f
                return self.currentfile
        self.currentfile = SymbolFile(file=file, wk=self.wk)
        self.opened_files.append(self.currentfile)
        return self.currentfile

    def __del__(self):
        self.wk.close()

    def close(self):
        self.wk.close()


# python lspcpp.py  --root /home/z/dev/lsp/pylspclient/tests/cpp --file /home/z/dev/lsp/pylspclient/tests/cpp/test_main.cpp -m a::run
# python lspcpp.py  --root /home/z/dev/lsp/pylspclient/tests/cpp --file /home/z/dev/lsp/pylspclient/tests/cpp/test_main.cpp
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-w", "--root", help="root path")
    parser.add_argument("-f", "--file", help="root path")

    args = parser.parse_args()
    root = args.root
    if root != None and root[0] != "/":
        root = os.path.join(os.getcwd(), root)
    runMain = LspMain(args.root, args.file)
    import time
    time.sleep(2)
    runMain.currentfile.print()
    history = []
    from prompt_toolkit.completion import WordCompleter

    colors = WordCompleter([
        '--file', '--callin', '--refer', '--exit', "--print", "--uml-output",
        "--stack-output", "--fzf"
    ])
    while True:
        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.history import FileHistory
            history = FileHistory('history.txt')
            session = PromptSession(history=history)
            _run: SymbolFile = runMain.currentfile
            cmd = session.prompt("%s >\n" % (_run.sourcecode.file),
                                 completer=colors)
            # session.history.save()
            _run.reset()
            try:
                parser.add_argument("-m", "--method", help="root path")
                parser.add_argument("-i", "--index", help="root path")
                parser.add_argument("-u",
                                    "--uml",
                                    help="root path",
                                    action="store_true")
                parser.add_argument("-R", "--refer", help="root path")
                parser.add_argument("-C", "--callin", help="root path")
                parser.add_argument("-S", "--symbol", help="root path")
                parser.add_argument("-q",
                                    "--exit",
                                    help="root path",
                                    action="store_true")
                parser.add_argument("-uo",
                                    "--uml-output",
                                    help="root path",
                                    action="store_true")
                parser.add_argument("-fzf",
                                    "--fzf",
                                    help="root path",
                                    action="store_true")
                parser.add_argument("-so",
                                    "--stack-output",
                                    help="root path",
                                    action="store_true")
                args = parser.parse_args(cmd.split(" "))
            except:
                continue
            if args.file != None:
                _run = runMain.changefile(args.file)
                _run.print()
            if args.callin != None:
                if args.stack_output:
                    _run.save_stack_file = OutputFile(
                        args.callin.replace(":", "_") + "_callstack.txt")
                if args.uml_output:
                    _run.save_uml_file = OutputFile(
                        args.callin.replace(":", "_") + ".puml")
                _run.call(args.callin, uml=True, once=False)
            elif args.refer != None:
                _run.refer(args.refer)
            elif args.exit != None:
                break
        except Exception as e:
            import traceback
            traceback.print_exc()
            pass
        pass
    runMain.close()
    # main(root=root, file=args.file, method=None)
    # main(root=args.root, file=args.file,
    #  method=args.method, index=args.index != None)
