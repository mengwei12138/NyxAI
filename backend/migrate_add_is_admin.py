"""
迁移脚本：添加 is_admin 字段到 users 表
"""
import sqlite3
import os

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'nyx_ai.db')


def migrate():
    """执行迁移"""
    if not os.path.exists(DB_PATH):
        print(f"数据库不存在: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 检查是否已存在 is_admin 字段
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'is_admin' in columns:
        print("is_admin 字段已存在，跳过迁移")
    else:
        # 添加 is_admin 字段
        cursor.execute(
            "ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")

        # 将 admin 用户设置为管理员
        cursor.execute(
            "UPDATE users SET is_admin = 1 WHERE username = 'admin'")

        conn.commit()
        print("✅ 迁移完成：添加 is_admin 字段")
        print("   - admin 用户已设置为管理员")

    # 验证
    cursor.execute("SELECT username, is_admin FROM users")
    users = cursor.fetchall()
    print("\n当前用户列表:")
    for user in users:
        print(f"   - {user[0]}: is_admin={user[1]}")

    conn.close()


if __name__ == "__main__":
    migrate()
