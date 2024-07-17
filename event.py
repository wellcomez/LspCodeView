from typing import Optional
from textual.message import Message
from callinview import task_call_in
from codesearch import SymbolLocation
from pylspclient.lsp_pydantic_strcuts import Location
class mymessage(Message):

    def __init__(self, s: list[str]) -> None:
        super().__init__()
        self.s = s


class changelspmessage(Message):
    loc: Optional[Location] = None

    def __init__(self,
                 file,
                 loc: Optional[Location] = None,
                 refresh=True) -> None:
        super().__init__()
        self.loc = loc
        self.file = file
        self.refresh_symbol_view = refresh

    pass


class symbolsmessage(Message):
    data = []
    file: str

    def __init__(self, data, file: str) -> None:
        super().__init__()
        self.file = file
        self.data = data


class callin_message(Message):
    taskmsg: task_call_in.message

    def __init__(self, message: task_call_in.message) -> None:
        super().__init__()
        self.taskmsg = message


class refermessage(Message):
    s: list[SymbolLocation]
    query: str

    def __init__(self, s: list[SymbolLocation], key: str) -> None:
        super().__init__()
        self.query = key
        self.s = s
