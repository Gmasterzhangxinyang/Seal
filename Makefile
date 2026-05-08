.PHONY: dev dev-frontend dev-backend build install install-frontend install-backend clean

# 一键启动前端 + 后端（开发模式）
dev:
	@echo "=========================================="
	@echo "  文档盖章机器人 - 开发模式启动"
	@echo "=========================================="
	@echo "  后端: http://127.0.0.1:5001"
	@echo "  前端: http://localhost:5173"
	@echo "  按 Ctrl+C 停止所有服务"
	@echo "=========================================="
	npm run dev

# 仅启动后端
dev-backend:
	@echo "启动 FastAPI 后端: http://127.0.0.1:5001"
	python -m api.main

# 仅启动前端
dev-frontend:
	@echo "启动 Vite 前端: http://localhost:5173"
	cd frontend && npm run dev

# 构建前端
build:
	cd frontend && npm run build
	@echo "前端构建完成: frontend/dist/"

# 安装所有依赖
install: install-backend install-frontend

install-backend:
	pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

# 清理
clean:
	rm -rf frontend/dist
	rm -rf __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
