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
	@echo "Killing all python and python3 processes using lsof and kill..."
	- for pid in $(lsof -t -c python -c python3); do kill -9 $$pid; done
	@echo "Killing all processes using port 8000..."
	- for pid in $(lsof -t -i:8000); do kill -9 $$pid; done
