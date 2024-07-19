from lspconfig import lspconfig


class lspconfig_py(lspconfig):
    def __init__(self) -> None:
        super().__init__()
        self.root_files = ['pyproject.toml',
                           'setup.py',
                           'setup.cfg',
                           'requirements.txt',
                           'Pipfile',]
        self.cmd = ["python", "-m", "pylsp"]
        self.file_extensions = ["py", "pyi", "mpy"]
