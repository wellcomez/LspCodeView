from functools import update_wrapper
from logging import root
from typing import Optional
from textual.message import Message
from textual.widgets import Tree
from baseview import MyListView
from callinview import log_message
from codesearch import Symbol
from common import from_file
from lspcpp import LspMain, SymbolFile, SymbolKind


class symbolload:
    file: str

    def __init__(self, filepath: str, lsp: LspMain) -> None:
        self.filepath = filepath
        self.lsp = lsp

    def symbols_list(self, file: str):
        if file != self.filepath:
            raise Exception("%s!=%s" % (file, self.filepath))
        a = self.lsp.find_symbol_file(self.filepath)
        return [] if a is None else a.symbols_list

    def need_refresh(self, file: str):
        return True if self.filepath != file else False


class symbol_tree_update(Message):
    symfile: Optional[SymbolFile]

    def __init__(self, symfile: Optional[SymbolFile]) -> None:
        super().__init__()
        self.symfile = symfile


class message_line_change(Message):

    def __init__(self, line, file) -> None:
        super().__init__()
        self.line = line
        self.file = file


class message_get_symbol_refer(Message):
    sym: Symbol

    def __init__(self, sym: Symbol) -> None:
        super().__init__()
        self.sym = sym


class _symbol_tree_view(Tree):
    BINDINGS = [
        ("r", "refer", "Reference"),
    ]

    def get_refer_for_symbol_list(self):
        root = self.cursor_node
        if root is None:
            return
        sym: Optional[Symbol] = root.data
        if sym is None:
            return
        self.post_message(message_get_symbol_refer(sym))

    def action_refer(self) -> None:
        try:
            self.get_refer_for_symbol_list()
        except Exception as e:
            self.post_message(log_message("exception %s" % (str(e))))
            pass

    def __init__(self):
        Tree.__init__(self, "", id="symbol-tree")

    def on_symbol_tree_update(self, message: symbol_tree_update):
        if message.symfile is None:
            self.root.remove_children()
            self.loading = True
            return
        else:
            self.loading = False
            self.set_data(message.symfile)
        pass

    def set_data(self, data: SymbolFile):
        self.symbols = data.sourcecode.class_symbol
        root = self.root
        root.remove_children()
        for a in data.sourcecode.class_symbol:
            if len(a.members):
                n = root.add(a.symbol_sidebar_displayname(False),
                             data=a,
                             expand=False)
                self.add_child(n, a)

            else:
                root.add_leaf(a.symbol_sidebar_displayname(False), data=a)
            pass
        root.toggle()

    def add_child(self, root, sym: Symbol):
        if len(sym.members):
            for a in sym.members:
                root.add_leaf(a.symbol_sidebar_displayname(False), data=a)

    def action_select_cursor(self):
        root = self.cursor_node
        if root is None:
            return
        sym: Optional[Symbol] = root.data
        if sym is None:
            return
        loc = sym.sym.location
        self.post_message(
            message_line_change(loc.range.start.line, file=from_file(loc.uri)))
        pass
