#!/bin/bash

# Trading Agents 전체 빌드 및 배포 스크립트
set -e

echo "🚀 Starting Trading Agents deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper function for colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required commands exist
check_dependencies() {
    print_status "Checking dependencies..."
    
    if ! command -v uv &> /dev/null; then
        print_error "uv is not installed. Please install it first:"
        echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed. Please install Node.js and npm first."
        exit 1
    fi
    
    print_status "All dependencies are available."
}

# Frontend setup and build
setup_frontend() {
    print_status "Setting up frontend..."
    
    cd fe
    
    # Copy environment file if it doesn't exist
    if [ ! -f .env.local ]; then
        if [ -f .env.example ]; then
            print_warning ".env.local not found, copying from .env.example"
            cp .env.example .env.local
        else
            print_warning ".env.local not found and no .env.example available"
        fi
    fi
    
    # Install dependencies
    print_status "Installing frontend dependencies..."
    npm install
    
    # Build frontend
    print_status "Building frontend..."
    npm run build
    
    print_status "Frontend build completed successfully!"
    cd ..
}

# Backend setup
setup_backend() {
    print_status "Setting up backend..."
    
    cd be
    
    # Copy environment file if it doesn't exist
    if [ ! -f .env ]; then
        if [ -f .env.sample ]; then
            print_warning ".env not found, copying from .env.sample"
            cp .env.sample .env
            print_warning "Please update the .env file with your actual configuration!"
        else
            print_warning ".env not found and no .env.sample available"
        fi
    fi
    
    # Install dependencies
    print_status "Installing backend dependencies..."
    make install
    
    print_status "Backend setup completed successfully!"
    cd ..
}

# Deploy FastAPI
deploy_fastapi() {
    print_status "Deploying FastAPI server..."
    
    cd be
    
    # Check if FastAPI is already running and kill it
    if pgrep -f "uvicorn src.main:app" > /dev/null; then
        print_warning "Existing FastAPI process found. Killing it..."
        pkill -f "uvicorn src.main:app" || true
        sleep 2
    fi
    
    # Deploy FastAPI
    make deploy
    
    # Wait a bit and check if the service started
    sleep 3
    if pgrep -f "uvicorn src.main:app" > /dev/null; then
        print_status "FastAPI server deployed successfully on port 8000!"
        print_status "Logs are available in be/fastapi.log"
    else
        print_error "Failed to start FastAPI server. Check be/fastapi.log for errors."
        exit 1
    fi
    
    cd ..
}

# Serve frontend (optional)
serve_frontend() {
    read -p "Do you want to serve the frontend locally? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Starting frontend development server..."
        cd fe
        npm run serve &
        FRONTEND_PID=$!
        print_status "Frontend server started on port 4173 (PID: $FRONTEND_PID)"
        cd ..
    fi
}

# Clean up function
cleanup() {
    print_status "Cleaning up temporary files..."
    
    # Clean backend
    cd be
    make clean
    cd ..
    
    # Clean root directory
    find . -type f -name "*.pyc" -delete
    find . -type d -name "__pycache__" -delete
    
    print_status "Cleanup completed!"
}

# Main deployment process
main() {
    print_status "Starting deployment process..."
    
    # Check dependencies
    check_dependencies
    
    # Setup and build frontend
    setup_frontend
    
    # Setup backend
    setup_backend
    
    # Deploy FastAPI
    deploy_fastapi
    
    # Optional: serve frontend
    serve_frontend
    
    print_status "🎉 Deployment completed successfully!"
    print_status "FastAPI server is running on: http://localhost:8000"
    print_status "API documentation available at: http://localhost:8000/docs"
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Frontend development server: http://localhost:4173"
    fi
    
    print_status "To view FastAPI logs: tail -f be/fastapi.log"
}

# Handle script arguments
case "${1:-}" in
    "clean")
        cleanup
        ;;
    "frontend")
        setup_frontend
        ;;
    "backend")
        setup_backend
        ;;
    "fastapi")
        deploy_fastapi
        ;;
    *)
        main
        ;;
esac