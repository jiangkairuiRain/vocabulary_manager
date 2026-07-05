import sqlite3
import os

class Database:
    def __init__(self, db_path=None):
        self.conn = None
        self.db_path = db_path

    def connect(self, db_path):
        if self.conn:
            self.conn.close()
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._init_tables()

    def _init_tables(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER,
            name TEXT NOT NULL,
            FOREIGN KEY (parent_id) REFERENCES folders(id) ON DELETE CASCADE
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_id INTEGER NOT NULL,
            word TEXT NOT NULL,
            definition TEXT DEFAULT '',
            FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE CASCADE
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        # 确保根节点存在
        c.execute("SELECT id FROM folders WHERE id=1")
        if not c.fetchone():
            c.execute("INSERT INTO folders (id, parent_id, name) VALUES (1, NULL, '词汇库')")
        self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    # ---------- 文件夹操作 ----------
    def get_children(self, parent_id):
        c = self.conn.cursor()
        c.execute("SELECT id, name FROM folders WHERE parent_id=? ORDER BY name", (parent_id,))
        return c.fetchall()

    def get_folder_path(self, folder_id):
        """返回从根到 folder_id 的名称列表"""
        path = []
        current = folder_id
        while current:
            c = self.conn.cursor()
            c.execute("SELECT id, name, parent_id FROM folders WHERE id=?", (current,))
            row = c.fetchone()
            if not row:
                break
            path.append(row[1])
            current = row[2]
        path.reverse()
        return path

    def get_folder_parent(self, folder_id):
        c = self.conn.cursor()
        c.execute("SELECT parent_id FROM folders WHERE id=?", (folder_id,))
        row = c.fetchone()
        return row[0] if row else None

    def add_folder(self, parent_id, name="新文件夹"):
        c = self.conn.cursor()
        c.execute("INSERT INTO folders (parent_id, name) VALUES (?, ?)", (parent_id, name))
        self.conn.commit()
        return c.lastrowid

    def rename_folder(self, folder_id, new_name):
        c = self.conn.cursor()
        c.execute("UPDATE folders SET name=? WHERE id=?", (new_name, folder_id))
        self.conn.commit()

    def delete_folder(self, folder_id):
        c = self.conn.cursor()
        c.execute("DELETE FROM folders WHERE id=?", (folder_id,))
        self.conn.commit()

    # ---------- 词条操作 ----------
    def get_entries(self, folder_id):
        c = self.conn.cursor()
        c.execute("SELECT id, word, definition FROM entries WHERE folder_id=? ORDER BY word", (folder_id,))
        return c.fetchall()

    def add_entry(self, folder_id, word="新单词", definition=""):
        c = self.conn.cursor()
        c.execute("INSERT INTO entries (folder_id, word, definition) VALUES (?, ?, ?)",
                  (folder_id, word, definition))
        self.conn.commit()
        return c.lastrowid

    def update_entry(self, entry_id, word, definition):
        c = self.conn.cursor()
        c.execute("UPDATE entries SET word=?, definition=? WHERE id=?", (word, definition, entry_id))
        self.conn.commit()

    def delete_entry(self, entry_id):
        c = self.conn.cursor()
        c.execute("DELETE FROM entries WHERE id=?", (entry_id,))
        self.conn.commit()

    def move_entry(self, entry_id, new_folder_id):
        c = self.conn.cursor()
        c.execute("UPDATE entries SET folder_id=? WHERE id=?", (new_folder_id, entry_id))
        self.conn.commit()

    def move_folder(self, folder_id, new_parent_id):
        c = self.conn.cursor()
        c.execute("UPDATE folders SET parent_id=? WHERE id=?", (new_parent_id, folder_id))
        self.conn.commit()

    # ---------- 搜索 ----------
    def get_descendant_folder_ids(self, folder_id):
        """递归获取当前文件夹及所有子文件夹的 id 列表"""
        ids = [folder_id]
        children = self.get_children(folder_id)
        for child_id, _ in children:
            ids.extend(self.get_descendant_folder_ids(child_id))
        return ids

    def search_entries(self, folder_id, keywords):
        """
        多关键词 OR 模糊搜索，范围：folder_id 及其子文件夹
        keywords: 字符串，空格分隔
        返回列表: (word, definition, folder_path)
        """
        if not keywords.strip():
            return []
        kw_list = keywords.split()
        folder_ids = self.get_descendant_folder_ids(folder_id)
        if not folder_ids:
            return []

        placeholders_folder = ','.join('?' for _ in folder_ids)
        like_clauses = []
        params = []
        for kw in kw_list:
            like_clauses.append("(e.word LIKE ? OR e.definition LIKE ?)")
            params.extend([f'%{kw}%', f'%{kw}%'])
        where = " OR ".join(like_clauses)

        sql = f'''
            SELECT e.word, e.definition, e.folder_id
            FROM entries e
            WHERE e.folder_id IN ({placeholders_folder})
            AND ({where})
            ORDER BY e.word
        '''
        params = folder_ids + params
        c = self.conn.cursor()
        c.execute(sql, params)
        results = []
        for word, defn, f_id in c.fetchall():
            path = '/'.join(self.get_folder_path(f_id))
            results.append((word, defn, path, f_id))
        return results

    # ---------- 元数据（最近库路径） ----------
    def set_meta(self, key, value):
        c = self.conn.cursor()
        c.execute("REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))
        self.conn.commit()

    def get_meta(self, key):
        c = self.conn.cursor()
        c.execute("SELECT value FROM meta WHERE key=?", (key,))
        row = c.fetchone()
        return row[0] if row else None
    
    def ensure_folder(self, parent_id, name):
        """
        在 parent_id 下查找名为 name 的文件夹，若存在返回其 id，否则创建并返回新 id。
        parent_id 为 1 表示根文件夹。
        """
        c = self.conn.cursor()
        c.execute("SELECT id FROM folders WHERE parent_id=? AND name=?", (parent_id, name))
        row = c.fetchone()
        if row:
            return row[0]
        else:
            c.execute("INSERT INTO folders (parent_id, name) VALUES (?, ?)", (parent_id, name))
            self.conn.commit()
            return c.lastrowid
    def deduplicate_entries(self):
        """删除每个文件夹内 (word, definition) 完全相同的重复词条，保留 id 最小的那条。返回删除总数。"""
        c = self.conn.cursor()
        # 查找每个 (folder_id, word, definition) 组合中需要保留的最小 id
        c.execute('''
            SELECT MIN(id) FROM entries
            GROUP BY folder_id, word, definition
        ''')
        keep_ids = [row[0] for row in c.fetchall()]

        if not keep_ids:
            return 0

        # 删除所有 id 不在保留列表中的词条
        placeholders = ','.join('?' for _ in keep_ids)
        c.execute(f'DELETE FROM entries WHERE id NOT IN ({placeholders})', keep_ids)
        deleted = c.rowcount
        self.conn.commit()
        return deleted