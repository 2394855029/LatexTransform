import sqlite3
import base64
from datetime import datetime
import os
from ..common.user_manager import userManager

class DatabaseManager:
    def __init__(self, db_path='app/data/history.db'):
        self.db_path = db_path
        # 确保数据库目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def init_db(self):
        """初始化数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查历史记录表是否已存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='history'")
            table_exists = cursor.fetchone()
            
            if not table_exists:
                # 创建包含user_id的新历史记录表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME NOT NULL,
                        image_data TEXT NOT NULL,
                        latex_result TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        request_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        UNIQUE(request_id)
                    )
                ''')
            else:
                # 检查表中是否已有user_id列
                try:
                    cursor.execute("SELECT user_id FROM history LIMIT 1")
                except sqlite3.OperationalError:
                    # 如果没有user_id列，添加它
                    cursor.execute("ALTER TABLE history ADD COLUMN user_id TEXT")
                    # 将现有记录更新为默认用户ID
                    cursor.execute("UPDATE history SET user_id = 'default' WHERE user_id IS NULL")
                    print("已将user_id列添加到history表并更新现有记录")
            
            conn.commit()
        except sqlite3.Error as e:
            print(f"数据库初始化错误: {e}")
        finally:
            if conn:
                conn.close()

    def add_record(self, image_data, latex_result, confidence, request_id, user_id=None):
        """添加记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 将图片转换为base64
        if isinstance(image_data, bytes):
            image_base64 = base64.b64encode(image_data).decode('utf-8')
        else:
            image_base64 = image_data
            
        try:
            # 如果没有提供user_id，使用当前用户ID
            if user_id is None:
                current_user = userManager.get_current_user()
                user_id = current_user['id'] if current_user else 'default'
                
            cursor.execute('''
                INSERT INTO history (timestamp, image_data, latex_result, confidence, request_id, user_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (datetime.now(), image_base64, latex_result, confidence, request_id, user_id))
            conn.commit()
            # 获取新插入记录的ID
            record_id = cursor.lastrowid
            print(f"Added new record with ID: {record_id}")
            return record_id  # 返回新记录的ID
        except sqlite3.IntegrityError:
            # 如果request_id已存在，则更新记录
            # 如果没有提供user_id，使用当前用户ID
            if user_id is None:
                current_user = userManager.get_current_user()
                user_id = current_user['id'] if current_user else 'default'
                
            cursor.execute('''
                UPDATE history 
                SET timestamp=?, image_data=?, latex_result=?, confidence=?, user_id=?
                WHERE request_id=?
            ''', (datetime.now(), image_base64, latex_result, confidence, user_id, request_id))
            conn.commit()
            # 获取更新记录的ID
            cursor.execute('SELECT id FROM history WHERE request_id=?', (request_id,))
            record_id = cursor.fetchone()[0]
            print(f"Updated existing record with ID: {record_id}")
            return record_id  # 返回更新记录的ID
        finally:
            conn.close()

    def get_records(self, page=1, page_size=10, search_text=None, user_id=None):
        """获取记录（支持分页和搜索）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 构建查询条件
        where_clauses = []
        params = []
        
        # 如果未提供用户ID，使用当前用户ID
        if user_id is None:
            current_user = userManager.get_current_user()
            user_id = current_user['id'] if current_user else 'default'
        
        # 添加用户ID条件
        where_clauses.append("user_id = ?")
        params.append(user_id)
        
        # 添加搜索条件
        if search_text:
            where_clauses.append("latex_result LIKE ?")
            params.append(f"%{search_text}%")
        
        # 组合所有条件
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        # 获取总记录数
        count_sql = f"SELECT COUNT(*) FROM history {where_clause}"
        cursor.execute(count_sql, params)
        total_count = cursor.fetchone()[0]
        
        # 获取分页数据
        offset = (page - 1) * page_size
        sql = f"""
            SELECT id, timestamp, image_data, latex_result, confidence, request_id 
            FROM history {where_clause}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(sql, params + [page_size, offset])
        records = cursor.fetchall()
        
        conn.close()
        
        return records, total_count

    def delete_record(self, record_id):
        """删除记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM history WHERE id=?", (record_id,))
        conn.commit()
        conn.close()

    def clear_history(self, user_id=None):
        """清空历史记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 如果指定了用户ID，只清除该用户的历史记录
        if user_id is None:
            current_user = userManager.get_current_user()
            user_id = current_user['id'] if current_user else 'default'
            
        cursor.execute("DELETE FROM history WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)

    def update_latex(self, record_id, latex):
        """更新记录的 LaTeX 内容"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            sql = 'UPDATE history SET latex_result = ? WHERE id = ?'
            params = (latex, record_id)
            print(f"Executing SQL: {sql} with params: {params}")  # 打印SQL语句和参数
            cursor.execute(sql, params)
            conn.commit()
            print(f"Rows affected: {cursor.rowcount}")  # 打印受影响的行数
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating latex: {e}")
            return False 

    def get_history_records(self, page=1, page_size=10, search_text=None, user_id=None):
        """获取历史记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 构建查询条件
        where_clauses = []
        params = []
        
        # 如果未提供用户ID，使用当前用户ID
        if user_id is None:
            current_user = userManager.get_current_user()
            user_id = current_user['id'] if current_user else 'default'
        
        # 添加用户ID条件
        where_clauses.append("user_id = ?")
        params.append(user_id)
        
        # 添加搜索条件
        if search_text:
            where_clauses.append("latex_result LIKE ?")
            params.append(f"%{search_text}%")
        
        # 组合所有条件
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
        # 获取总记录数
        count_sql = f"SELECT COUNT(*) FROM history {where_clause}"
        cursor.execute(count_sql, params)
        total_count = cursor.fetchone()[0]
        
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 获取分页数据
        sql = f"""
            SELECT id, timestamp, image_data, latex_result, confidence, request_id 
            FROM history {where_clause}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(sql, params + [page_size, offset])
        records = cursor.fetchall()
        
        conn.close()
        
        return records, total_count 