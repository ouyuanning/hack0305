#!/bin/bash
# dev.sh - 启动/停止/重启开发服务
# 用法: ./dev.sh [start|stop|restart|status]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_DIR="$SCRIPT_DIR/.pids"
LOG_DIR="$SCRIPT_DIR/.logs"
CONFIG="$SCRIPT_DIR/config.yaml"

mkdir -p "$PID_DIR" "$LOG_DIR"

# 加载 .env 文件
if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$SCRIPT_DIR/.env"
  set +a
elif [ -f "$SCRIPT_DIR/src/.env" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$SCRIPT_DIR/src/.env"
  set +a
fi

BACKEND_PID="$PID_DIR/backend.pid"
FRONTEND_PID="$PID_DIR/frontend.pid"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

# ---- helpers ----

is_running() {
  local pid_file="$1"
  [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null
}

stop_service() {
  local name="$1"
  local pid_file="$2"
  if is_running "$pid_file"; then
    kill "$(cat "$pid_file")" 2>/dev/null
    rm -f "$pid_file"
    echo "  ✓ $name 已停止"
  else
    echo "  - $name 未在运行"
  fi
}

start_backend() {
  if is_running "$BACKEND_PID"; then
    echo "  - 后端已在运行 (pid $(cat $BACKEND_PID))"
    return
  fi
  echo "  → 编译后端..."
  (cd "$SCRIPT_DIR/go" && go build -o api-server ./cmd/api-server/main.go) 2>&1
  echo "  → 启动后端 (日志: $BACKEND_LOG)"
  "$SCRIPT_DIR/go/api-server" -config "$CONFIG" >> "$BACKEND_LOG" 2>&1 &
  echo $! > "$BACKEND_PID"
  sleep 1
  if is_running "$BACKEND_PID"; then
    echo "  ✓ 后端已启动 (pid $(cat $BACKEND_PID)) → http://localhost:8080"
  else
    echo "  ✗ 后端启动失败，查看日志: $BACKEND_LOG"
    tail -20 "$BACKEND_LOG"
    exit 1
  fi
}

start_frontend() {
  if is_running "$FRONTEND_PID"; then
    echo "  - 前端已在运行 (pid $(cat $FRONTEND_PID))"
    return
  fi
  echo "  → 启动前端 (日志: $FRONTEND_LOG)"
  (cd "$SCRIPT_DIR/frontend" && npm run dev >> "$FRONTEND_LOG" 2>&1) &
  echo $! > "$FRONTEND_PID"
  sleep 2
  if is_running "$FRONTEND_PID"; then
    echo "  ✓ 前端已启动 (pid $(cat $FRONTEND_PID)) → http://localhost:3000"
  else
    echo "  ✗ 前端启动失败，查看日志: $FRONTEND_LOG"
    tail -20 "$FRONTEND_LOG"
    exit 1
  fi
}

cmd_start() {
  echo "▶ 启动服务..."
  start_backend
  start_frontend
  echo ""
  echo "服务已就绪:"
  echo "  前端: http://localhost:3000"
  echo "  后端: http://localhost:8080"
  echo ""
  echo "查看日志:"
  echo "  tail -f $BACKEND_LOG"
  echo "  tail -f $FRONTEND_LOG"
}

cmd_stop() {
  echo "■ 停止服务..."
  stop_service "后端" "$BACKEND_PID"
  stop_service "前端" "$FRONTEND_PID"
  # 清理可能残留的 vite 进程
  pkill -f "vite" 2>/dev/null || true
  pkill -f "api-server" 2>/dev/null || true
  echo "  完成"
}

cmd_restart() {
  cmd_stop
  sleep 1
  cmd_start
}

cmd_status() {
  echo "● 服务状态:"
  if is_running "$BACKEND_PID"; then
    echo "  后端: ✓ 运行中 (pid $(cat $BACKEND_PID))"
  else
    echo "  后端: ✗ 未运行"
  fi
  if is_running "$FRONTEND_PID"; then
    echo "  前端: ✓ 运行中 (pid $(cat $FRONTEND_PID))"
  else
    echo "  前端: ✗ 未运行"
  fi
}

cmd_log() {
  echo "=== 后端日志 (最近 30 行) ==="
  tail -30 "$BACKEND_LOG" 2>/dev/null || echo "(无日志)"
  echo ""
  echo "=== 前端日志 (最近 20 行) ==="
  tail -20 "$FRONTEND_LOG" 2>/dev/null || echo "(无日志)"
}

# ---- main ----

case "${1:-start}" in
  start)   cmd_start ;;
  stop)    cmd_stop ;;
  restart) cmd_restart ;;
  status)  cmd_status ;;
  log|logs) cmd_log ;;
  *)
    echo "用法: $0 [start|stop|restart|status|logs]"
    exit 1
    ;;
esac
