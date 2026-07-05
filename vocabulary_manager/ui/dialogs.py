import tkinter as tk
from tkinter import simpledialog, messagebox

def ask_rename(parent, title, prompt, initial):
    """简单重命名对话框"""
    dlg = simpledialog.askstring(title, prompt, initialvalue=initial, parent=parent)
    return dlg

class EditEntryDialog(tk.Toplevel):
    """新建/编辑单词对话框"""
    def __init__(self, parent, title, word="", definition="", callback=None):
        super().__init__(parent)
        self.title(title)
        self.callback = callback
        self.transient(parent)
        self.grab_set()

        tk.Label(self, text="单词:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.word_var = tk.StringVar(value=word)
        tk.Entry(self, textvariable=self.word_var, width=30).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(self, text="释义:").grid(row=1, column=0, padx=5, pady=5, sticky='e')
        self.def_var = tk.StringVar(value=definition)
        tk.Entry(self, textvariable=self.def_var, width=30).grid(row=1, column=1, padx=5, pady=5)

        btn_frame = tk.Frame(self)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
        tk.Button(btn_frame, text="确定", command=self._on_ok).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.LEFT, padx=5)

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.wait_window()

    def _on_ok(self):
        word = self.word_var.get().strip()
        if not word:
            messagebox.showwarning("提示", "单词不能为空")
            return
        if self.callback:
            self.callback(word, self.def_var.get().strip())
        self.destroy()

class MoveTargetDialog(tk.Toplevel):
    """移动目标选择对话框，仅列出合规文件夹"""
    def __init__(self, parent, db, obj_id, is_entry, callback):
        super().__init__(parent)
        self.db = db
        self.obj_id = obj_id
        self.is_entry = is_entry
        self.callback = callback
        self.title("移动")
        self.transient(parent)
        self.grab_set()

        self.tree = ttk.Treeview(self, show='tree', selectmode='browse')
        self.tree.pack(fill=tk.BOTH, expand=True)

        # 获取当前所在文件夹
        if is_entry:
            c = db.conn.cursor()
            c.execute("SELECT folder_id FROM entries WHERE id=?", (obj_id,))
            row = c.fetchone()
            current_folder = row[0] if row else None
        else:
            current_folder = db.get_folder_parent(obj_id)

        if current_folder is None:
            messagebox.showwarning("错误", "无法获取当前位置")
            self.destroy()
            return

        # 合规目标：父文件夹 itself, 以及当前文件夹的所有子文件夹（排除自己如果 is_entry=False）
        # 父文件夹
        parent_of_current = db.get_folder_parent(current_folder)  # 父文件夹
        valid_ids = []
        if parent_of_current:
            valid_ids.append(parent_of_current)
        # 子文件夹
        children = db.get_children(current_folder)
        for cid, name in children:
            if not is_entry and cid == obj_id:
                continue  # 不能移动到自己
            valid_ids.append(cid)

        # 构建树，只显示这些合规文件夹，但需展示层级？这里简化列表显示
        self.folder_dict = {}
        self._populate_tree(valid_ids)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="确定", command=self._on_ok).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.LEFT, padx=5)

    def _populate_tree(self, valid_ids):
        # 简单展示：只列出文件夹名，但可能丢失层级。改为按路径显示
        for fid in valid_ids:
            path = self.db.get_folder_path(fid)
            display = '/'.join(path)
            # 避免重复iid
            self.tree.insert('', 'end', iid=str(fid), text=display)

    def _on_ok(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请选择目标文件夹")
            return
        target_id = int(sel[0])
        self.callback(self.obj_id, target_id)
        self.destroy()