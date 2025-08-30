.PHONY: install run deploy clean killpy

# Install dependencies
install:
	uv sync

# 개발용 FastAPI 서버 실행
run:
	uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Deploy FastAPI server in background
deploy:
	nohup uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 > fastapi.log 2>&1 &

# Clean temporary files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/

# Kill all python processes using lsof and kill
killpy:
	@echo "모든 python, python3 프로세스를 ps aux로 찾아서 kill -9로 종료합니다..."
	- ps aux | grep '[p]ython' | awk '{print $$2}' | xargs -r kill -9
	@echo "8000번 포트를 사용 중인 프로세스를 ps aux로 찾아서 종료합니다..."
	- ps aux | grep '8000' | grep -v grep | awk '{print $$2}' | xargs -r kill -9
	@echo "uvicorn 프로세스도 ps aux로 찾아서 종료합니다..."
	- ps aux | grep '[u]vicorn' | awk '{print $$2}' | xargs -r kill -9
