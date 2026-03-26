"""
创建管理员账户脚本
"""
import asyncio
from sqlmodel import Session, select
from app.database import engine
from app.models import User
from app.services.auth_service import AuthService


async def create_admin():
    """创建默认管理员账户"""
    with Session(engine) as session:
        # 检查是否已存在管理员
        admin = session.exec(select(User).where(
            User.username == "admin")).first()
        if admin:
            print("✅ 管理员账户已存在")
            return

        # 创建管理员
        admin_user = User(
            username="admin",
            email="admin@nyxai.com",
            password_hash=AuthService.get_password_hash("admin123"),
            is_admin=True
        )
        session.add(admin_user)
        session.commit()
        print("✅ 管理员账户创建成功")
        print("   用户名: admin")
        print("   密码: admin123")
        print("   ⚠️  请登录后立即修改密码！")


if __name__ == "__main__":
    asyncio.run(create_admin())
