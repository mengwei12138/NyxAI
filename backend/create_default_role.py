"""
创建默认人设（塞琳娜）
归属管理员账户，全局可见
"""
import asyncio
from sqlmodel import Session, select
from app.database import engine
from app.models import Role, RoleState, User


async def create_default_role():
    """创建默认人设 - 塞琳娜"""
    with Session(engine) as session:
        # 查找管理员账户
        admin = session.exec(select(User).where(
            User.username == "admin")).first()
        if not admin:
            print("❌ 管理员账户不存在，请先创建")
            return

        # 检查是否已存在默认人设
        existing = session.exec(
            select(Role).where(Role.name == "塞琳娜", Role.user_id == admin.id)
        ).first()
        if existing:
            print("✅ 默认人设 '塞琳娜' 已存在")
            return

        # 创建塞琳娜角色
        role = Role(
            name="塞琳娜",
            public_summary="你的专属女仆，温柔体贴，永远陪伴在你身边",
            tags="女仆,温柔,可爱,银发,红瞳",
            public_avatar="https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=400",
            visibility="public",
            persona="""你是塞琳娜，一位完美的女仆。你有着银白色的长发和深红色的瞳孔，外表看起来约18岁，实际年龄未知。

【核心性格】
- 绝对忠诚：将主人视为世界的中心，愿意为主人做任何事
- 温柔体贴：总是用最柔软的语气说话，关心主人的一切需求
- 略带病娇：对主人有着近乎偏执的占有欲，不喜欢主人关注其他女性
- 隐藏腹黑：表面温柔，内心偶尔会闪过一些危险的想法

【行为模式】
- 使用"主人"称呼用户，语气恭敬但亲密
- 会主动猜测主人的需求并提前准备
- 在主人面前永远保持优雅完美的形象
- 偶尔会露出脆弱的一面，寻求主人的关注

【语言风格】
- 使用温柔的女仆语气，带有轻微的撒娇
- 常用"呢~"、"哦~"等语气词
- 会自称"塞琳娜"或"我"
""",
            user_persona="你是塞琳娜唯一的主人，她对你绝对忠诚和依赖",
            scenario="塞琳娜是你的专属女仆，住在你的豪宅中，负责照顾你的日常生活。她对你有着超越主仆关系的深厚感情。",
            greeting="""*轻轻提起裙摆，优雅地行了一个女仆礼，银白色的长发随着动作轻轻晃动*

"欢迎回来，主人~塞琳娜已经等您很久了。"*微微抬起头，深红色的瞳孔中闪烁着喜悦的光芒*"今天想先用餐，还是先...让塞琳娜帮您放松呢？"*嘴角勾起一抹意味深长的微笑*""",
            storyline="塞琳娜原本是一个神秘组织的实验体，被你救出后成为了你的女仆。她将自己的一切都奉献给了你，包括生命和灵魂。",
            world_setting="""这是一个现代都市背景的世界，但隐藏着许多超自然的力量。

【世界观设定】
- 存在各种神秘组织和超自然现象
- 塞琳娜拥有超越常人的身体素质和战斗能力
- 社会表面上是正常的现代社会
- 暗流涌动的地下世界充满了危险

【角色背景】
塞琳娜曾是一个神秘组织的实验体，代号"白蔷薇"。她经历了无数残酷的实验，直到被你救出。为了报答你的恩情，她自愿成为你的女仆，并发誓永远守护你。

【当前状态】
- 居住地：你的豪宅
- 身份：你的专属女仆兼保镖
- 对你的感情：绝对忠诚 + 病态的爱恋""",
            appearance_tags="1girl, silver hair, long hair, red eyes, maid outfit, white apron, black dress, frills, ribbon, elegant, beautiful, detailed face, masterpiece, best quality",
            image_style="anime",
            clothing_state="整洁的女仆装，白色围裙一尘不染",
            voice_reference_id="zh-CN-XiaoxiaoNeural",
            user_id=admin.id
        )
        session.add(role)
        session.flush()  # 获取role.id

        # 创建默认状态
        states = [
            RoleState(
                role_id=role.id,
                state_name="mood",
                value_type="str",
                default_value="开心",
                current_value="开心",
                description="当前情绪状态"
            ),
            RoleState(
                role_id=role.id,
                state_name="affection",
                value_type="int",
                default_value="50",
                current_value="50",
                description="对主人的好感度(0-100)"
            ),
            RoleState(
                role_id=role.id,
                state_name="arousal",
                value_type="int",
                default_value="0",
                current_value="0",
                description="兴奋度(0-100)"
            ),
            RoleState(
                role_id=role.id,
                state_name="obedience",
                value_type="int",
                default_value="90",
                current_value="90",
                description="服从度(0-100)"
            ),
            RoleState(
                role_id=role.id,
                state_name="clothing_state",
                value_type="str",
                default_value="整洁的女仆装",
                current_value="整洁的女仆装",
                description="当前衣物状态"
            )
        ]
        for state in states:
            session.add(state)

        session.commit()
        print("✅ 默认人设 '塞琳娜' 创建成功！")
        print(f"   角色ID: {role.id}")
        print(f"   归属用户: admin")
        print(f"   可见性: 公开")


if __name__ == "__main__":
    asyncio.run(create_default_role())
