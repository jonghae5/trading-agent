.PHONY: help cli streamlit install clean

# Default target
help:
	@echo "Available commands:"
	@echo "  make cli        - Run CLI version (python -m cli.main)"
	@echo "  make streamlit  - Run Streamlit web interface"
	@echo "  make install    - Install dependencies"
	@echo "  make clean      - Clean temporary files"
	@echo "  make help       - Show this help message"

# Run CLI version
cli:
	uv run python -m cli.main

# Run Streamlit web interface
streamlit:
	uv run streamlit run streamlit_app.py  --server.port 8501 --theme.base light --server.runOnSave=true

# Install dependencies
# curl -LsSf https://astral.sh/uv/install.sh | sh
install:
	uv sync

# Deploy
deploy:
	nohup uv run streamlit run streamlit_app.py --server.port 8000 --server.address 0.0.0.0 --theme.base light > streamlit.log 2>&1 &
	
# Clean temporary files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/


	
