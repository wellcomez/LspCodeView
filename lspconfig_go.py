from lspconfig import lspconfig
import subprocess
import os

# 存储 GOMODCACHE 的结果
mod_cache = None


def util_root_pattern(fname):
    # 这里需要实现基于文件模式查找根目录的逻辑
    # 暂时返回一个示例路径
    return os.path.dirname(fname)


class lspconfgi_go(lspconfig):

    def __init__(self) -> None:
        file_extensions = ["go"]
        filetypes = ['go', 'gomod', 'gowork', 'gotmpl']
        file_extensions.extend(filetypes)
        root_files = ['go.work', 'go.mod', '.git']
        super().__init__(file_extensions=file_extensions, root_files=root_files)
        self.cmd = ["gopls"]
        self.file_extensions = list(set(file_extensions))

    def get_lsp_clients(self, name):
        # 这里需要实现获取 LSP 客户端的逻辑
        # 由于这是一个示例，我们暂时返回一个空列表
        return []

    def get_root_dir(self, fname):
        global mod_cache

        # 查看 https://github.com/neovim/nvim-lspconfig/issues/804
        if mod_cache is None:
            # 运行 'go env GOMODCACHE' 命令并获取结果
            result = subprocess.run(
                ['go', 'env', 'GOMODCACHE'], stdout=subprocess.PIPE, text=True)
            if result.stdout:
                mod_cache = result.stdout.strip()

        # 如果文件名的开始部分与 mod_cache 匹配
        if fname.startswith(mod_cache):
            # 获取所有名为 'gopls' 的 LSP 客户端
            clients = self.get_lsp_clients('gopls')
            if clients:
                return clients[-1].config['root_dir']
        return self.root_dir(fname)
