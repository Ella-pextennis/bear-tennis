#!/usr/bin/env bash
# Start MySQL for the coffee dashboard.
# Path 1 (preferred, no sudo): tarball at ~/.local/mysql — already installed.
# Path 2 (fallback): Homebrew `brew install mysql`.
# Path 3 (first run, no sudo): download MySQL tarball and install to ~/.local/mysql.
# Idempotent: safe to re-run after a machine restart to bring MySQL back up.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

MYSQL_HOME_DIR="$HOME/.local/mysql"
MYSQL_DATA="$HOME/.local/mysql-data"
MY_CNF="$HOME/.local/my.cnf"
MYSQL_LOG="$HOME/.local/mysql.log"
MYSQL_TARBALL="$HOME/.local/mysql.tar.gz"
MYSQL_VERSION="8.0.46"
MYSQL_TARBALL_URL="https://cdn.mysql.com/Downloads/MySQL-8.0/mysql-${MYSQL_VERSION}-macos15-arm64.tar.gz"

# Make brew available on Apple Silicon even if not in PATH yet
if [ -x /opt/homebrew/bin/brew ]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
fi

echo "========================================"
echo " BearmeCoffee — MySQL 启动"
echo "========================================"

# --- Already installed via tarball? Just start it ------------------------
if [ -x "$MYSQL_HOME_DIR/bin/mysqld" ]; then
  echo ">> 检测到 tarball 安装的 MySQL ($MYSQL_HOME_DIR)"
  # Is it already running?
  if "$MYSQL_HOME_DIR/bin/mysqladmin" ping --socket=/tmp/mysql.sock 2>/dev/null | grep -q alive; then
    echo ">> MySQL 已在运行。"
  else
    echo ">> 启动 mysqld..."
    mkdir -p "$MYSQL_DATA"
    nohup "$MYSQL_HOME_DIR/bin/mysqld" --defaults-file="$MY_CNF" --user="$USER" >> "$MYSQL_LOG" 2>&1 &
    echo "   PID=$!  日志=$MYSQL_LOG"
    for i in $(seq 1 30); do
      if "$MYSQL_HOME_DIR/bin/mysqladmin" ping --socket=/tmp/mysql.sock 2>/dev/null | grep -q alive; then
        echo ">> MySQL 就绪（${i}s）"; break
      fi
      sleep 1
    done
  fi

# --- Homebrew MySQL available? --------------------------------------------
elif command -v brew >/dev/null 2>&1 && brew list mysql >/dev/null 2>&1; then
  echo ">> 检测到 brew 安装的 MySQL"
  brew services start mysql >/dev/null 2>&1 || true
  for i in $(seq 1 30); do
    if mysqladmin ping --silent 2>/dev/null; then echo ">> MySQL 就绪（${i}s）"; break; fi
    sleep 1
  done
  MYSQL_HOME_DIR=""  # use system mysql client below

# --- Neither: download tarball (no sudo needed) ---------------------------
else
  echo ">> 未检测到 MySQL。下载 tarball 免 sudo 安装（${MYSQL_VERSION}, macos15, arm64）..."
  echo "   URL: $MYSQL_TARBALL_URL"
  mkdir -p "$HOME/.local"
  curl -C - -L --retry 5 --retry-delay 3 -o "$MYSQL_TARBALL" "$MYSQL_TARBALL_URL"
  echo ">> 解压..."
  cd "$HOME/.local"
  tar xzf mysql.tar.gz
  EXTRACTED=$(ls -d mysql-${MYSQL_VERSION}-macos*-arm64 2>/dev/null | head -1)
  if [ -z "$EXTRACTED" ]; then
    echo "!! 解压后未找到 mysql 目录"; exit 1
  fi
  xattr -r -d com.apple.quarantine "$EXTRACTED" 2>/dev/null || true
  rm -rf mysql 2>/dev/null
  ln -sf "$EXTRACTED" mysql
  echo ">> 初始化数据目录..."
  mkdir -p "$MYSQL_DATA"
  "$MYSQL_HOME_DIR/bin/mysqld" --initialize-insecure \
    --basedir="$MYSQL_HOME_DIR" --datadir="$MYSQL_DATA" 2>&1 | tail -3
  echo ">> 启动 mysqld..."
  nohup "$MYSQL_HOME_DIR/bin/mysqld" --defaults-file="$MY_CNF" --user="$USER" >> "$MYSQL_LOG" 2>&1 &
  echo "   PID=$!  日志=$MYSQL_LOG"
  for i in $(seq 1 30); do
    if "$MYSQL_HOME_DIR/bin/mysqladmin" ping --socket=/tmp/mysql.sock 2>/dev/null | grep -q alive; then
      echo ">> MySQL 就绪（${i}s）"; break
    fi
    sleep 1
  done
fi

# --- Verify it's up -------------------------------------------------------
if ! "$MYSQL_HOME_DIR/bin/mysqladmin" ping --socket=/tmp/mysql.sock 2>/dev/null | grep -q alive 2>/dev/null; then
  if ! mysqladmin ping --silent 2>/dev/null; then
    echo "!! MySQL 未就绪。日志末尾："
    tail -20 "$MYSQL_LOG" 2>/dev/null || echo "(无日志)"
    exit 1
  fi
fi

MYSQL_BIN="$MYSQL_HOME_DIR/bin/mysql"
[ -x "$MYSQL_BIN" ] || MYSQL_BIN="mysql"

echo ">> 创建数据库和用户..."
"$MYSQL_BIN" --socket=/tmp/mysql.sock -uroot <<'SQL' 2>/dev/null
CREATE DATABASE IF NOT EXISTS coffee CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'coffee'@'localhost' IDENTIFIED WITH mysql_native_password BY 'coffee123';
CREATE USER IF NOT EXISTS 'coffee'@'127.0.0.1' IDENTIFIED WITH mysql_native_password BY 'coffee123';
GRANT ALL PRIVILEGES ON coffee.* TO 'coffee'@'localhost';
GRANT ALL PRIVILEGES ON coffee.* TO 'coffee'@'127.0.0.1';
FLUSH PRIVILEGES;
SQL

echo ">> 校验表结构..."
"$MYSQL_BIN" --socket=/tmp/mysql.sock -uroot coffee < "$PROJECT_ROOT/docker/init.sql" 2>/dev/null
TABLE_COUNT=$("$MYSQL_BIN" --socket=/tmp/mysql.sock -uroot coffee -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='coffee' AND table_name='coffee_orders'" 2>/dev/null | tr -d '[:space:]')
if [ "$TABLE_COUNT" != "1" ]; then
  echo "!! COFFEE_ORDERS 表创建失败"; exit 1
fi

echo ""
echo "========================================"
echo " ✅ MySQL 就绪"
echo "========================================"
echo " 连接信息：localhost:3306 / coffee / coffee123"
echo "   socket : /tmp/mysql.sock"
echo "   root   : 无密码"
echo "   数据目录: $MYSQL_DATA"
echo "   日志    : $MYSQL_LOG"
echo ""
echo " 下一步：bash scripts/dev.sh  启动前后端"
