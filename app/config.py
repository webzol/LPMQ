"""全局配置常量。"""
from pathlib import Path

# 项目根目录（app 包的上一级）
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据目录与配置文件
DATA_DIR = BASE_DIR / "data"
STATIONS_FILE = DATA_DIR / "stations.json"

# 静态资源目录
STATIC_DIR = BASE_DIR / "static"

# 模型测试相关
TEST_CONCURRENCY = 5          # 并发测试的模型数量
TEST_MESSAGE = "hi"           # 测试消息内容
TEST_TIMEOUT = 30.0           # 单次请求超时（秒）
TEST_MAX_TOKENS = 5           # 测试请求的最大 token 数
