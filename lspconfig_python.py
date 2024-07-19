from lspconfig import lspconfig

file_extensions = ["py", "pyi", "mpy"]


class lspconfig_pyright(lspconfig):
    setting = {
        "python": {
            "analysis": {
                "autoSearchPaths": True,
                "useLibraryCodeForTypes": True,
                "diagnosticMode": "openFilesOnly"
            }
        }
    }

    def __init__(self) -> None:
        root_files = [
            'pyproject.toml',
            'setup.py',
            'setup.cfg',
            'requirements.txt',
            'Pipfile',
            'pyrightconfig.json',
            '.git',
        ]
        super().__init__(root_files, file_extensions)
        self.cmd = ['pyright-langserver', '--stdio']


class lspconfig_pylsp(lspconfig):
    def __init__(self) -> None:
        root_files = ['pyproject.toml',
                      'setup.py',
                      'setup.cfg',
                      'requirements.txt',
                      'Pipfile',]
        super().__init__(root_files, file_extensions)
        self.cmd = ["python", "-m", "pylsp"]
