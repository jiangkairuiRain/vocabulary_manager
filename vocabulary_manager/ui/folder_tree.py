import tkinter as tk
from tkinter import ttk, messagebox

class FolderTree(ttk.Frame):
    def __init__(self, parent, db, on_select_callback=None):
        super().__init__(parent)
        self.db = db
        self.on_select_callback = on_select_callback
        self.tree = ttk.Treeview(self, show='tree', selectmode='browse')
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind('<<TreeviewSelect>>', self._on_select)
        self._create_right_click_menu()

    def _populate_root(self):
        """初始化根节点"""
        self.tree.delete(*self.tree.get_children())
        # 根节点 id=1，从数据库读取名称
        c = self.db.conn.cursor()
        c.execute("SELECT name FROM folders WHERE id=1")
        row = c.fetchone()
        root_name = row[0] if row else "词汇库"
        self.root_id = 1
        self.root_iid = self.tree.insert('', 'end', iid=str(self.root_id), text=root_name, open=True)
        self._load_children(self.root_id)

    def _load_children(self, parent_id, parent_iid=None):
        """加载子文件夹到树中"""
        if parent_iid is None:
            parent_iid = str(parent_id)
        # 清除已存在的子项（避免重复）
        self.tree.delete(*self.tree.get_children(parent_iid))
        children = self.db.get_children(parent_id)
        for child_id, name in children:
            iid = str(child_id)
            self.tree.insert(parent_iid, 'end', iid=iid, text=name)
            # 检查是否有子文件夹，若有则添加虚节点以便展开
            if self.db.get_children(child_id):
                self.tree.insert(iid, 'end', iid=f"dummy_{child_id}", text='')

    def _on_select(self, event):
        sel = self.tree.selection()
        if sel:
            folder_id = int(sel[0])
            if self.on_select_callback:
                self.on_select_callback(folder_id)

    def refresh_children(self, folder_id):
        """展开且刷新该节点的子项"""
        iid = str(folder_id)
        kids = self.tree.get_children(iid)
        # 如果存在虚节点，先删除
        for kid in kids:
            if kid.startswith('dummy_'):
                self.tree.delete(kid)
        self._load_children(folder_id, iid)
        # 确保节点展开
        self.tree.item(iid, open=True)

    def get_selected_folder_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def select_folder(self, folder_id):
        """选中并展开路径到指定文件夹"""
        # 递归展开父节点路径
        path_ids = []
        c = self.db.conn.cursor()
        current = folder_id
        while current:
            path_ids.append(current)
            c.execute("SELECT parent_id FROM folders WHERE id=?", (current,))
            row = c.fetchone()
            current = row[0] if row else None
        path_ids.reverse()

        parent_iid = ''
        for fid in path_ids:
            iid = str(fid)
            if not self.tree.exists(iid):
                # 如果节点还没创建，需要逐级加载，这里简化：重新加载整棵树
                self._populate_root()
                self._open_path(folder_id)
                self.tree.selection_set(iid)
                return
            self.tree.item(iid, open=True)
            parent_iid = iid
        self.tree.selection_set(str(folder_id))

    def _open_path(self, folder_id):
        """强制按路径逐级加载并展开"""
        path = []
        current = folder_id
        while current:
            path.append(current)
            c = self.db.conn.cursor()
            c.execute("SELECT parent_id FROM folders WHERE id=?", (current,))
            row = c.fetchone()
            current = row[0] if row else None
        path.reverse()
        parent_iid = ''
        for fid in path:
            iid = str(fid)
            if not self.tree.exists(iid):
                # 需要先加载父节点，但这时我们已经按顺序，可以先加载父节点的孩子
                if parent_iid:
                    self._load_children(int(parent_iid), parent_iid)
            if self.tree.exists(iid):
                self.tree.item(iid, open=True)
                parent_iid = iid

    # ---------- 右键菜单 ----------
    def _create_right_click_menu(self):
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="新建子文件夹", command=self._new_subfolder)
        self.menu.add_command(label="新建单词", command=self._new_word_in_folder)
        self.menu.add_separator()
        self.menu.add_command(label="重命名", command=self._rename_folder)
        self.menu.add_command(label="移动", command=self._move_folder)
        self.menu.add_separator()
        self.menu.add_command(label="删除", command=self._delete_folder)
        self.tree.bind("<Button-3>", self._on_right_click)  # Windows
        self.tree.bind("<Button-2>", self._on_right_click)  # Mac

    def _on_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.menu.post(event.x_root, event.y_root)

    def _new_subfolder(self):
        fid = self.get_selected_folder_id()
        if fid is None:
            return
        new_id = self.db.add_folder(fid)
        self.refresh_children(fid)
        # 让用户重命名
        self.after(100, lambda: self._start_rename(new_id))

    def _new_word_in_folder(self):
        fid = self.get_selected_folder_id()
        if fid is None:
            return
        # 这里通知主窗口在右侧添加新单词
        if self.on_new_word_callback:
            self.on_new_word_callback(fid)

    def set_new_word_callback(self, callback):
        self.on_new_word_callback = callback

    def _rename_folder(self):
        fid = self.get_selected_folder_id()
        if fid is None or fid == 1:
            if fid == 1:
                messagebox.showwarning("提示", "不能重命名根节点")
            return
        self._start_rename(fid)

    def _start_rename(self, folder_id):
        iid = str(folder_id)
        if not self.tree.exists(iid):
            return
        old_name = self.tree.item(iid, 'text')
        # 弹出简单对话框
        from .dialogs import ask_rename
        new_name = ask_rename(self, "重命名文件夹", "新名称:", old_name)
        if new_name and new_name != old_name:
            self.db.rename_folder(folder_id, new_name)
            self.tree.item(iid, text=new_name)

    def _move_folder(self):
        fid = self.get_selected_folder_id()
        if fid is None or fid == 1:
            return
        # 获取允许的移动目标：父文件夹 和 当前文件夹的子文件夹（排除自身和后代）
        from .dialogs import MoveTargetDialog
        MoveTargetDialog(self, self.db, fid, is_entry=False, callback=self._do_move_folder)

    def _do_move_folder(self, folder_id, new_parent_id):
        self.db.move_folder(folder_id, new_parent_id)
        self._populate_root()
        # 重新选择该文件夹
        self.select_folder(folder_id)

    def _delete_folder(self):
        fid = self.get_selected_folder_id()
        if fid is None:
            return
        if fid == 1:
            messagebox.showwarning("提示", "不能删除根节点")
            return
        name = self.tree.item(str(fid), 'text')
        if messagebox.askyesno("确认删除", f"确定删除文件夹‘{name}’及其所有子文件夹和单词吗？"):
            self.db.delete_folder(fid)
            self._populate_root()
            # 通知主窗口刷新右侧列表（可能当前选中被删了）
            if self.on_select_callback:
                self.on_select_callback(self.root_id)

    def load_root(self):
        self._populate_root()