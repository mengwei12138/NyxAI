"""
数据库连接和会话管理
支持 SQLite 和 PostgreSQL
"""
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool, QueuePool
from app.config import get_settings
from app.core.logger import get_logger

logger = get_logger("database")
settings = get_settings()

# 根据数据库类型创建引擎


def create_db_engine():
    """创建数据库引擎"""
    is_sqlite = "sqlite" in settings.DATABASE_URL.lower()

    if is_sqlite:
        # SQLite 配置（开发环境）
        engine = create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=settings.DEBUG
        )
        logger.info("使用 SQLite 数据库")
    else:
        # PostgreSQL 配置（生产环境）
        engine = create_engine(
            settings.DATABASE_URL,
            poolclass=QueuePool,
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,  # 自动检测断开的连接
            pool_recycle=3600,   # 1小时回收连接
            echo=settings.DEBUG
        )
        logger.info("使用 PostgreSQL 数据库")

    return engine


engine = create_db_engine()


def create_db_and_tables():
    """创建数据库和表"""
    try:
        SQLModel.metadata.create_all(engine)
        logger.info("数据库表创建/检查完成")
        _migrate_checkin_nullable()
        _migrate_roles_columns()
        _migrate_voice_presets()
        _migrate_payment_packages()
    except Exception as e:
        logger.error(f"数据库表创建失败: {e}")
        raise


def _migrate_roles_columns():
    """
    迁移：为 roles 表补充 title 和 plot_milestones 列（幂等安全）
    这两列是后期新增的，旧数据库实例需要补全
    """
    from sqlalchemy import inspect as sa_inspect, text as sa_text
    try:
        inspector = sa_inspect(engine)
        existing = {c['name'] for c in inspector.get_columns('roles')}
        missing_cols = []
        if 'title' not in existing:
            missing_cols.append(
                "ALTER TABLE roles ADD COLUMN title VARCHAR(200)")
        if 'plot_milestones' not in existing:
            missing_cols.append(
                "ALTER TABLE roles ADD COLUMN plot_milestones VARCHAR(5000)")
        if missing_cols:
            with engine.connect() as conn:
                for sql in missing_cols:
                    conn.execute(sa_text(sql))
                conn.commit()
            logger.info(f"迁移完成：roles 表已补全 {len(missing_cols)} 个列")
    except Exception as e:
        logger.warning(f"roles 列迁移跳过（可能已是最新结构）: {e}")


def _migrate_checkin_nullable():
    """
    迁移：将 user_checkins.last_checkin_date 改为允许 NULL
    新用户创建时不再伪造昨天日期，避免首次签到获得第2天积分的 bug
    """
    import re
    from sqlalchemy import text as sa_text

    try:
        is_sqlite = "sqlite" in settings.DATABASE_URL.lower()

        with engine.connect() as conn:
            if is_sqlite:
                # SQLite 不支持 ALTER COLUMN，检查是否需要迁移
                result = conn.execute(
                    sa_text(
                        "SELECT sql FROM sqlite_master WHERE type='table' AND name='user_checkins'")
                ).fetchone()
                if not result or not result[0]:
                    return
                col_def = result[0]
                if not re.search(r'last_checkin_date\s+\S+\s+NOT NULL', col_def, re.IGNORECASE):
                    return  # 已经是 nullable，无需迁移

                logger.info(
                    "迁移 user_checkins.last_checkin_date 为 nullable（SQLite）...")
                conn.execute(sa_text("""
                    CREATE TABLE IF NOT EXISTS user_checkins_new (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
                        last_checkin_date DATE,
                        streak_days INTEGER NOT NULL DEFAULT 0,
                        total_checkins INTEGER NOT NULL DEFAULT 0,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL
                    )
                """))
                conn.execute(sa_text("""
                    INSERT INTO user_checkins_new
                    SELECT id, user_id, last_checkin_date, streak_days,
                           total_checkins, created_at, updated_at
                    FROM user_checkins
                """))
                conn.execute(sa_text("DROP TABLE user_checkins"))
                conn.execute(
                    sa_text("ALTER TABLE user_checkins_new RENAME TO user_checkins"))
                conn.commit()
                logger.info("迁移完成（SQLite）：last_checkin_date 已允许 NULL")

            else:
                # PostgreSQL 支持直接 ALTER COLUMN DROP NOT NULL
                # 先检查列是否仍为 NOT NULL
                result = conn.execute(sa_text("""
                    SELECT is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'user_checkins'
                      AND column_name = 'last_checkin_date'
                """)).fetchone()
                if not result or result[0] == 'YES':
                    return  # 表不存在或已是 nullable

                logger.info(
                    "迁移 user_checkins.last_checkin_date 为 nullable（PostgreSQL）...")
                conn.execute(sa_text(
                    "ALTER TABLE user_checkins ALTER COLUMN last_checkin_date DROP NOT NULL"
                ))
                conn.commit()
                logger.info("迁移完成（PostgreSQL）：last_checkin_date 已允许 NULL")

    except Exception as e:
        logger.warning(f"checkin 迁移跳过（可能已是最新结构）: {e}")


def _migrate_voice_presets():
    """
    初始化音色预设表：若表为空，插入默认的 3 条预设数据。
    此函数幂等安全，重复执行无副作用。
    """
    try:
        from app.models.voice import VoicePreset
        from sqlmodel import select as sm_select
        from sqlalchemy import func as sa_func

        default_presets = [
            {
                "preset_id": "wenrou_yujie",
                "name": "温柔御姐",
                "description": "温婉柔和，知性大方",
                "reference_id": "5c09bfed66ce4a968c3022d6f85c8e07",
                "preview_text": "今天辛苦了吧，来，让我帮你放松一下。",
                "is_default": True,
                "sort_order": 0,
            },
            {
                "preset_id": "linjia_jiejie",
                "name": "邻家大姐姐",
                "description": "亲切自然，温暖可爱",
                "reference_id": "fbe02f8306fc4d3d915e9871722a39d5",
                "preview_text": "哎呀，你怎么又来找我啦，快进来坐坐吧。",
                "is_default": False,
                "sort_order": 1,
            },
            {
                "preset_id": "nv_daxuesheng",
                "name": "女大学生",
                "description": "青春活泼，元气满满",
                "reference_id": "a1417155aa234890aab4a18686d12849",
                "preview_text": "哇，好久不见呀！最近过得怎么样呀？",
                "is_default": False,
                "sort_order": 2,
            },
        ]

        with Session(engine) as session:
            count = session.exec(
                sm_select(sa_func.count(VoicePreset.id))
            ).first() or 0
            if count > 0:
                return  # 已有数据，跳过

            from datetime import datetime
            now = datetime.utcnow()
            for p in default_presets:
                preset = VoicePreset(
                    preset_id=p["preset_id"],
                    name=p["name"],
                    description=p["description"],
                    reference_id=p["reference_id"],
                    preview_text=p["preview_text"],
                    is_default=p["is_default"],
                    sort_order=p["sort_order"],
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
                session.add(preset)
            session.commit()
            logger.info(f"音色预设初始化完成，插入 {len(default_presets)} 条默认预设")
    except Exception as e:
        logger.warning(f"音色预设初始化跳过: {e}")


def _migrate_payment_packages():
    """
    初始化充值套餐表：若表为空，插入与原硬编码 PACKAGES 一致的默认数据。
    此函数幂等安全，重复执行无副作用。
    """
    try:
        from app.models.payment import PaymentPackage
        from sqlmodel import select as sm_select
        from sqlalchemy import func as sa_func

        default_packages = [
            {
                "package_id": "starter",
                "plan_id": "47c3cb1226c111f1977a52540025c377",
                "name": "入门包",
                "amount": 9.9,
                "credits": 100,
                "desc": "适合体验",
                "popular": False,
                "sort_order": 0,
            },
            {
                "package_id": "standard",
                "plan_id": "0335865226c611f18df352540025c377",
                "name": "标准包",
                "amount": 30.0,
                "credits": 350,
                "desc": "最受欢迎",
                "popular": True,
                "sort_order": 1,
            },
            {
                "package_id": "pro",
                "plan_id": "63422a7826c111f1b71352540025c377",
                "name": "进阶包",
                "amount": 88.0,
                "credits": 1150,
                "desc": "超高性价比",
                "popular": False,
                "sort_order": 2,
            },
        ]

        with Session(engine) as session:
            count = session.exec(
                sm_select(sa_func.count(PaymentPackage.id))
            ).first() or 0
            if count > 0:
                return  # 已有数据，跳过

            for p in default_packages:
                pkg = PaymentPackage(
                    package_id=p["package_id"],
                    plan_id=p["plan_id"],
                    name=p["name"],
                    amount=p["amount"],
                    credits=p["credits"],
                    desc=p["desc"],
                    popular=p["popular"],
                    is_active=True,
                    sort_order=p["sort_order"],
                )
                session.add(pkg)
            session.commit()
            logger.info(f"充值套餐初始化完成，插入 {len(default_packages)} 条默认套餐")
    except Exception as e:
        logger.warning(f"充值套餐初始化跳过: {e}")


def get_session():
    """获取数据库会话"""
    with Session(engine) as session:
        yield session
