import tkinter as tk
from tkinter import ttk

class SearchWindow(tk.Toplevel):
    def __init__(self, parent, db, results):
        super().__init__(parent)
        self.db = db
        self.results = results  # list of (word, defn, path, folder_id)
        self.title(f"搜索结果 ({len(results)} 条)")
        self.geometry("600x400")

        columns = ('word', 'definition', 'path')
        self.tree = ttk.Treeview(self, columns=columns, show='headings')
        self.tree.heading('word', text='单词')
        self.tree.heading('definition', text='释义')
        self.tree.heading('path', text='所在路径')
        self.tree.column('word', width=120)
        self.tree.column('definition', width=200)
        self.tree.column('path', width=250)
        self.tree.pack(fill=tk.BOTH, expand=True)

        for word, defn, path, folder_id in results:
            self.tree.insert('', 'end', values=(word, defn, path), tags=(str(folder_id),))

        self.tree.bind('<Double-1>', self._on_double_click)

    def _on_double_click(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        item = sel[0]
        folder_id = int(self.tree.item(item, 'tags')[0])
        self.master.jump_to_folder(folder_id)
        self.destroy()