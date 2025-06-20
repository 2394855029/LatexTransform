import os
import json
import hashlib
import uuid
from PyQt5.QtCore import QObject, pyqtSignal
from ..common.signal_bus import signalBus

class UserManager(QObject):
    """用户管理类，负责用户数据的加载、保存和切换"""
    
    # 当前用户信息变更信号
    userChanged = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.users = []
        self.current_user = None
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        self.users_file = os.path.join(self.data_dir, 'users.json')
        
        # 确保数据目录存在
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        # 加载用户数据
        self.load_users()
        
        # 如果没有用户，创建默认用户
        if not self.users:
            self.create_default_user()
            
        # 设置当前用户为第一个用户
        if self.users and not self.current_user:
            self.set_current_user(self.users[0]['id'])
    
    def load_users(self):
        """从文件加载用户数据"""
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.users = data.get('users', [])
                    
                    # 修复缺少密码字段的旧用户数据
                    users_updated = False
                    for user in self.users:
                        if 'password_hash' not in user or 'salt' not in user:
                            # 为旧用户添加默认密码 "123456"
                            salt = uuid.uuid4().hex
                            default_password = "123456"
                            hashed_password = self._hash_password(default_password, salt)
                            user['password_hash'] = hashed_password
                            user['salt'] = salt
                            users_updated = True
                    
                    # 如果更新了用户数据，保存到文件
                    if users_updated:
                        self.save_users()
                    
                    current_user_id = data.get('current_user_id')
                    if current_user_id:
                        self.set_current_user(current_user_id)
            except Exception as e:
                self.create_default_user()
        else:
            self.create_default_user()
    
    def save_users(self):
        """保存用户数据到文件"""
        try:
            data = {
                'users': self.users,
                'current_user_id': self.current_user['id'] if self.current_user else None
            }
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass
    
    def create_default_user(self):
        """创建默认用户"""
        # 生成默认密码的盐值和哈希
        salt = uuid.uuid4().hex
        default_password = "123456"  # 默认密码
        hashed_password = self._hash_password(default_password, salt)
        
        default_user = {
            'id': 'default',
            'name': 'andy',
            'avatar': 'images/andy.png',
            'password_hash': hashed_password,
            'salt': salt
        }
        self.users = [default_user]
        self.current_user = default_user
        self.save_users()
    
    def get_current_user(self):
        """获取当前用户信息"""
        return self.current_user
    
    def set_current_user(self, user_id):
        """设置当前用户"""
        for user in self.users:
            if user['id'] == user_id:
                self.current_user = user
                self.userChanged.emit(self.current_user)
                signalBus.userChanged.emit(self.current_user)
                self.save_users()
                return True
        return False
    
    def update_current_user(self, name=None, avatar=None):
        """更新当前用户信息"""
        if not self.current_user:
            return False
            
        if name is not None:
            self.current_user['name'] = name
            
        if avatar is not None:
            self.current_user['avatar'] = avatar
            
        # 更新用户列表中的用户信息
        for i, user in enumerate(self.users):
            if user['id'] == self.current_user['id']:
                self.users[i] = self.current_user
                break
                
        self.save_users()
        self.userChanged.emit(self.current_user)
        signalBus.userChanged.emit(self.current_user)
        return True
    
    def _hash_password(self, password, salt):
        """对密码进行哈希"""
        # 将密码和盐值进行哈希
        hashed = hashlib.sha256((password + salt).encode()).hexdigest()
        return hashed
        
    def verify_password(self, user_id, password):
        """验证用户密码"""
        for user in self.users:
            if user['id'] == user_id:
                salt = user.get('salt', '')
                stored_hash = user.get('password_hash', '')
                # 如果是旧用户没有密码，则默认验证通过
                if not salt or not stored_hash:
                    return True
                    
                # 计算输入密码的哈希
                input_hash = self._hash_password(password, salt)
                return input_hash == stored_hash
                
        return False
    
    def add_user(self, name, avatar, password):
        """添加新用户"""
        # 生成唯一ID和盐值
        user_id = str(uuid.uuid4())
        salt = uuid.uuid4().hex
        
        # 对密码进行哈希
        hashed_password = self._hash_password(password, salt)
        
        new_user = {
            'id': user_id,
            'name': name,
            'avatar': avatar,
            'password_hash': hashed_password,
            'salt': salt
        }
        
        self.users.append(new_user)
        self.save_users()
        return new_user
    
    def delete_user(self, user_id):
        """删除用户"""
        # 不允许删除当前用户
        if self.current_user and self.current_user['id'] == user_id:
            return False
            
        # 不允许删除所有用户
        if len(self.users) <= 1:
            return False
            
        for i, user in enumerate(self.users):
            if user['id'] == user_id:
                del self.users[i]
                self.save_users()
                return True
                
        return False
    
    def get_all_users(self):
        """获取所有用户"""
        return self.users
    
    def get_user_history_dir(self, user_id=None):
        """获取用户历史记录目录"""
        if user_id is None and self.current_user:
            user_id = self.current_user['id']
            
        if not user_id:
            return None
            
        user_dir = os.path.join(self.data_dir, 'history', user_id)
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
        return user_dir

# 全局单例
userManager = UserManager()
