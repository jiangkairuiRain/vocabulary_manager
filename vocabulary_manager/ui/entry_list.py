import tkinter as tk
from tkinter import ttk, messagebox

class EntryList(ttk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.current_folder_id = None

        columns = ('word', 'definition')
        self.tree = ttk.Treeview(self, columns=columns, show='headings', selectmode='extended')
        self.tree.heading('word', text='单词')
        self.tree.heading('definition', text='释义')
        self.tree.column('word', width=150)
        self.tree.column('definition', width=250)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # 右键菜单
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="新建单词", command=self._new_entry)
        self.menu.add_command(label="重命名", command=self._rename_entry)
        self.menu.add_command(label="移动", command=self._move_entry)
        self.menu.add_separator()
        self.menu.add_command(label="删除", command=self._delete_entry)
        self.tree.bind("<Button-3>", self._on_right_click)
        self.tree.bind("<Button-2>", self._on_right_click)

        self.tree.bind("<Double-1>", lambda e: self._rename_entry())

    def load_entries(self, folder_id):
        self.current_folder_id = folder_id
        self.tree.delete(*self.tree.get_children())
        entries = self.db.get_entries(folder_id)
        for eid, word, definition in entries:
            self.tree.insert('', 'end', iid=str(eid), values=(word, definition))

    def get_selected_entry_ids(self):
        return [int(iid) for iid in self.tree.selection()]

    # ---------- 右键/按钮操作 ----------
    def _on_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.menu.post(event.x_root, event.y_root)

    def _new_entry(self):
        if self.current_folder_id is None:
            return
        from .dialogs import EditEntryDialog
        EditEntryDialog(self, "新建单词", callback=lambda word, defn: self._add_entry(word, defn))

    def _add_entry(self, word, definition):
        if self.current_folder_id is None:
            return
        self.db.add_entry(self.current_folder_id, word, definition)
        self.load_entries(self.current_folder_id)

    def _rename_entry(self):
        selected = self.get_selected_entry_ids()
        if not selected:
            return
        eid = selected[0]  # 只处理第一个
        values = self.tree.item(str(eid), 'values')
        old_word, old_def = values[0], values[1]
        from .dialogs import EditEntryDialog
        EditEntryDialog(self, "修改单词", word=old_word, definition=old_def,
                        callback=lambda w, d: self._do_rename(eid, w, d))

    def _do_rename(self, eid, word, definition):
        self.db.update_entry(eid, word, definition)
        self.load_entries(self.current_folder_id)

    def _move_entry(self):
        selected = self.get_selected_entry_ids()
        if not selected:
            return
        eid = selected[0]
        from .dialogs import MoveTargetDialog
        MoveTargetDialog(self, self.db, eid, is_entry=True, callback=self._do_move_entry)

    def _do_move_entry(self, entry_id, new_folder_id):
        self.db.move_entry(entry_id, new_folder_id)
        self.load_entries(self.current_folder_id)

    def _delete_entry(self):
        selected = self.get_selected_entry_ids()
        if not selected:
            return
        if messagebox.askyesno("确认删除", f"确定删除选中的 {len(selected)} 个词条吗？"):
            for eid in selected:
                self.db.delete_entry(eid)
            self.load_entries(self.current_folder_id)

    def add_entry_from_outside(self, word, definition):
        """供外部（如工具栏）调用"""
        self._add_entry(word, definition)