"""
结构化日志配置
"""
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """JSON格式日志处理器"""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加额外字段
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "path"):
            log_data["path"] = record.path
        if hasattr(record, "method"):
            log_data["method"] = record.method
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        # 异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 额外属性
        for key, value in record.__dict__.items():
            if key not in log_data and not key.startswith("_"):
                log_data[key] = value

        return json.dumps(log_data, ensure_ascii=False, default=str)


def setup_logging(
    level: str = "INFO",
    json_format: bool = True,
    log_file: str = None
) -> logging.Logger:
    """
    配置日志系统

    Args:
        level: 日志级别 DEBUG/INFO/WARNING/ERROR/CRITICAL
        json_format: 是否使用JSON格式（生产环境推荐）
        log_file: 日志文件路径，None则只输出到控制台
    """
    logger = logging.getLogger("nyx_ai")
    logger.setLevel(getattr(logging, level.upper()))
    logger.handlers = []  # 清除现有处理器

    # 选择格式
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器（可选）
    if log_file:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# 全局logger实例
logger = setup_logging()


def get_logger(name: str = None) -> logging.Logger:
    """获取命名logger"""
    if name:
        return logging.getLogger(f"nyx_ai.{name}")
    return logger
