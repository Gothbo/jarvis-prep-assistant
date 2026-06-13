"""读取 .streamlit/secrets.toml，生成 _env.bat（纯 set 命令）"""
import sys
import tomllib
from pathlib import Path

project_dir = Path(sys.argv[1])
secrets_file = project_dir / ".streamlit" / "secrets.toml"
env_file = project_dir / "_env.bat"

try:
    with open(secrets_file, "rb") as f:
        config = tomllib.load(f)

    lines = []
    for key, value in config.items():
        if key.startswith("LLM_") or key.startswith("THREAT_"):
            lines.append(f'set {key}={value}')

    env_file.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    print(f"  已生成 _env.bat ({len(lines)} 个变量)")
except Exception as e:
    print(f"  [!] 解析 secrets.toml 失败: {e}")
    # 写一个空的 env.bat 以免 start.bat 报错
    env_file.write_text(":: empty\r\n", encoding="utf-8")
