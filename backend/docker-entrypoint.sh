#!/bin/bash
set -e

# 确保挂载目录有正确权限
for dir in logs cache cache/tts cache/images instance; do
    if [ -d "/app/$dir" ]; then
        chmod -R 777 "/app/$dir" 2>/dev/null || true
    else
        mkdir -p "/app/$dir"
        chmod 777 "/app/$dir"
    fi
done

# 执行传入的命令
exec "$@"
