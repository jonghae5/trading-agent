.PHONY: install run deploy clean

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
