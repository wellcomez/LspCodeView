class lspconfig:
    cmd :list[str]= []
    file_extensions = ["cc", "cpp", "h", "hpp", "cxx", "hxx",
                       "inl", 'c', 'cpp', 'objc', 'objcpp', 'cuda', 'proto']
    root_files = []
    single_file_support: bool = True
    capabilities: dict = {}

    def __get_file_ext(self, file):
        return file.split('.')[-1]

    def is_me(self, file):
        return self.__get_file_ext(file) in self.file_extensions

    def root_dir(self, dir):
        import os
        for a in os.listdir(dir):
            if a in self.root_files:
                return dir
        return None


class lspconfig_clangd(lspconfig):
    def __init__(self) -> None:
        super().__init__()
        self.cmd = ["clangd"]
        default_capabilities = {
            "textDocument": {
                "completion": {
                    "editsNearCursor": True,
                },
            },
            "offsetEncoding": ["utf-8", "utf-16"],
        }
        self.capabilities = default_capabilities
        self.root_files = [
            '.clangd',
            '.clang-tidy',
            '.clang-format',
            'compile_commands.json',
            'compile_flags.txt',
            'configure.ac',  # AutoTools
        ]
    pass
