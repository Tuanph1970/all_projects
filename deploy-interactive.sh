#!/bin/bash

# ============================================================================
# Interactive Multi-Project Deployment Script
# ============================================================================
# This script provides an interactive dialog-based deployment for:
#   - Ceramic Mobile App Backend (Port 8002)
#   - Stock Predict Backend (Port 8004)
#   - Mathematic Mobile Backend (Port 8003)
#   - Ollama LLM Setup (GPU/CPU)
#
# Usage: ./deploy-interactive.sh
# ============================================================================

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Dynamic BASE_DIR detection - automatically detect the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$SCRIPT_DIR"

# Project directories (relative to BASE_DIR)
CERAMIC_DIR="$BASE_DIR/ceramic_mobile_app/back_end"
STOCK_DIR="$BASE_DIR/stockpredict/stock_microservices"
MATH_DIR="$BASE_DIR/mathematic-mobile/backend"

# Environment files
ENV_FILE="$BASE_DIR/.deploy-env"

# Deployment settings
BUILD_FLAG=""
NO_CACHE_FLAG=""
SELECTED_PROJECTS=()
SETUP_OLLAMA=false
OLLAMA_PROFILE=""
SETUP_NGINX=false

# Function to print colored output
print_color() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

# Function to print section headers
print_header() {
    echo
    print_color $CYAN "╔═══════════════════════════════════════════════════════════╗"
    print_color $CYAN "║                                                           ║"
    printf "${CYAN}║${NC} %-57s ${CYAN}║${NC}\n" "$1"
    print_color $CYAN "║                                                           ║"
    print_color $CYAN "╚═══════════════════════════════════════════════════════════╝"
    echo
}

# Function to print a box
print_box() {
    local title=$1
    local content=$2
    echo
    print_color $BLUE "┌─────────────────────────────────────────────────────────┐"
    printf "${BLUE}│${NC} %-55s ${BLUE}│${NC}\n" "$title"
    print_color $BLUE "├─────────────────────────────────────────────────────────┤"
    printf "${BLUE}│${NC} %-55s ${BLUE}│${NC}\n" "$content"
    print_color $BLUE "└─────────────────────────────────────────────────────────┘"
    echo
}

# Function to ask yes/no question
ask_yes_no() {
    local question=$1
    local default=$2
    local answer
    
    if [ "$default" = "y" ]; then
        read -p "$(print_color $YELLOW "$question (Y/n): ")" answer
        answer=${answer:-y}
    else
        read -p "$(print_color $YELLOW "$question (y/N): ")" answer
        answer=${answer:-n}
    fi
    
    [[ "$answer" =~ ^[Yy]$ ]]
}

# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        print_color $RED "Error: Docker is not running!"
        print_color $YELLOW "Please start Docker and try again."
        exit 1
    fi
}

# Function to check if nginx is installed
check_nginx() {
    if command -v nginx &> /dev/null; then
        return 0
    fi
    return 1
}

# Function to check if nginx is running
check_nginx_running() {
    if systemctl is-active --quiet nginx 2>/dev/null; then
        return 0
    fi
    return 1
}

# Function to install nginx
install_nginx() {
    print_color $BLUE "Installing nginx..."
    
    if ! check_nginx; then
        print_color $YELLOW "Nginx is not installed. Installing..."
        sudo apt-get update -qq
        sudo apt-get install -y nginx
        if check_nginx; then
            print_color $GREEN "✓ Nginx installed successfully"
        else
            print_color $RED "✗ Failed to install nginx"
            return 1
        fi
    else
        print_color $GREEN "✓ Nginx is already installed"
    fi
}

# Function to setup nginx configuration
setup_nginx_config() {
    print_header "Nginx Configuration Setup"
    
    # Check if nginx is installed
    if ! check_nginx; then
        if ask_yes_no "Nginx is not installed. Do you want to install it now?" "y"; then
            install_nginx || return 1
        else
            print_color $YELLOW "○ Skipping nginx setup"
            return 1
        fi
    fi
    
    # Check if nginx is running
    if ! check_nginx_running; then
        print_color $YELLOW "⚠ Nginx is not running. Starting nginx..."
        sudo systemctl start nginx
        sudo systemctl enable nginx
        if check_nginx_running; then
            print_color $GREEN "✓ Nginx started and enabled"
        else
            print_color $RED "✗ Failed to start nginx"
            return 1
        fi
    else
        print_color $GREEN "✓ Nginx is running"
    fi
    
    # Backup current config
    print_color $BLUE "📦 Backing up current nginx configuration..."
    if [ -f /etc/nginx/sites-enabled/default ]; then
        sudo cp /etc/nginx/sites-enabled/default /etc/nginx/sites-enabled/default.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
        print_color $GREEN "✓ Backup created"
    fi
    
    # Copy unified nginx config
    print_color $BLUE "📥 Installing unified nginx configuration..."
    local nginx_conf="$BASE_DIR/nginx-all-projects.conf"
    
    if [ ! -f "$nginx_conf" ]; then
        print_color $RED "✗ Nginx configuration file not found: $nginx_conf"
        return 1
    fi
    
    sudo cp "$nginx_conf" /etc/nginx/sites-available/
    print_color $GREEN "✓ Configuration copied to /etc/nginx/sites-available/"
    
    # Enable the config
    print_color $BLUE "🔗 Enabling nginx configuration..."
    sudo ln -sf /etc/nginx/sites-available/nginx-all-projects.conf /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    print_color $GREEN "✓ Configuration enabled"
    
    # Test nginx config
    print_color $BLUE "🔍 Testing nginx configuration..."
    if sudo nginx -t; then
        print_color $GREEN "✓ Nginx configuration test passed"
    else
        print_color $RED "✗ Nginx configuration test failed"
        return 1
    fi
    
    # Reload nginx
    print_color $BLUE "🔄 Reloading nginx..."
    if sudo systemctl reload nginx; then
        print_color $GREEN "✓ Nginx reloaded successfully"
    else
        print_color $RED "✗ Failed to reload nginx"
        return 1
    fi
    
    echo
    print_color $GREEN "✓ Nginx setup complete!"
    print_color $CYAN "Unified API Gateway available at: http://localhost/"
    print_color $CYAN "  - Ceramic API: http://localhost/ceramic/"
    print_color $CYAN "  - Stock API:   http://localhost/stock/"
    print_color $CYAN "  - Math API:    http://localhost/math/"
}

# Function to create environment file if not exists
create_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        print_header "Initial Setup"
        print_color $YELLOW "Creating default environment configuration..."
        
        cat > "$ENV_FILE" <<EOF
# ============================================================================
# Shared Environment Configuration for Multi-Project Deployment
# ============================================================================

# Database Root Password
MYSQL_ROOT_PASSWORD=Mysql_2025

# Ceramic Project Configuration
CERAMIC_API_PORT=8002
CERAMIC_DB_PORT=3308
CERAMIC_DB_NAME=ceramic_db
CERAMIC_DB_USER=ceramic_user
CERAMIC_DB_PASSWORD=Mysql_2025
CERAMIC_REDIS_PORT=6379

# Stock Predict Project Configuration
STOCK_API_PORT=8080
STOCK_DB_PORT=3309
STOCK_DB_NAME=stockpredict_db
STOCK_DB_USER=stock_user
STOCK_DB_PASSWORD=Mysql_2025

# Mathematic Mobile Project Configuration
MATH_API_PORT=8003
MATH_DB_PORT=3310
MATH_DB_NAME=mathematic_db
MATH_DB_USER=mathematic_user
MATH_DB_PASSWORD=Mysql_2025
MATH_REDIS_PORT=6380

# General Configuration
ENVIRONMENT=production
EOF
        print_color $GREEN "✓ Environment file created at: $ENV_FILE"
    fi
}

# Function to load environment variables
load_env() {
    if [ -f "$ENV_FILE" ]; then
        export $(cat "$ENV_FILE" | grep -v '^#' | xargs)
    fi
}

# Function to show project info
show_project_info() {
    local project=$1
    case $project in
        ceramic)
            print_box "Ceramic Mobile App Backend" \
                     "API Port: 8002 | DB Port: 3308 | Redis: 6379"
            ;;
        stock)
            print_box "Stock Predict Full-Stack" \
                     "API: 8004 | Frontend: 3004 | MySQL: 3309 | Grafana: 3100"
            ;;
        math)
            print_box "Mathematics Mobile Backend" \
                     "API Port: 8003 | DB Port: 3310 | Redis: 6380"
            ;;
    esac
}

# Function to check if project is already running
is_project_running() {
    local project_name=$1
    docker ps --filter "label=com.docker.compose.project=$project_name" --format "{{.Names}}" | grep -q .
}

# Function to get running status
get_project_status() {
    local project_name=$1
    if is_project_running "$project_name"; then
        echo "${GREEN}Running${NC}"
    else
        echo "${RED}Stopped${NC}"
    fi
}

# Function to check if project directory exists
check_project_dir() {
    local project=$1
    local dir=""

    case $project in
        ceramic) dir="$CERAMIC_DIR" ;;
        stock) dir="$STOCK_DIR" ;;
        math) dir="$MATH_DIR" ;;
    esac

    if [ ! -d "$dir" ]; then
        print_color $RED "Error: Project directory not found: $dir"
        return 1
    fi
    return 0
}

# Function to detect docker compose command
get_compose_cmd() {
    if docker compose version &> /dev/null; then
        echo "docker compose"
    elif command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    else
        print_color $RED "Error: Docker Compose is not installed"
        exit 1
    fi
}

COMPOSE_CMD=""

# Function to deploy a project
deploy_project() {
    local project=$1
    local project_dir=""
    local project_name=""
    local build_args=""

    # Check if project directory exists
    if ! check_project_dir "$project"; then
        print_color $RED "Skipping $project - directory not found"
        return 1
    fi

    case $project in
        ceramic)
            project_dir="$CERAMIC_DIR"
            project_name="ceramic"
            ;;
        stock)
            project_dir="$STOCK_DIR"
            project_name="stockpredict"
            ;;
        math)
            project_dir="$MATH_DIR"
            project_name="mathematic"
            ;;
    esac

    print_color $BLUE "📦 Deploying $project_name..."

    cd "$project_dir"

    # Build args based on BUILD_FLAG
    if [ -n "$BUILD_FLAG" ]; then
        build_args="--build"
        print_color $YELLOW "🔨 Building images..."

        # If no-cache is requested, we need to build separately first
        if [ -n "$NO_CACHE_FLAG" ]; then
            print_color $YELLOW "🔨 Building with --no-cache (this may take longer)..."
        fi
    fi

    # Deploy based on project type
    case $project in
        ceramic)
            # Ceramic uses its own deploy script or docker-compose
            if [ -f "docker-compose.yml" ]; then
                # Build with --no-cache if requested
                if [ -n "$NO_CACHE_FLAG" ] && [ -n "$BUILD_FLAG" ]; then
                    print_color $YELLOW "🔨 Building Ceramic with --no-cache..."
                    $COMPOSE_CMD -f docker-compose.yml -p "$project_name" build --no-cache
                fi
                print_color $YELLOW "🚀 Starting Ceramic services..."
                $COMPOSE_CMD -f docker-compose.yml -p "$project_name" up -d $build_args
            else
                print_color $RED "docker-compose.yml not found in $project_dir"
                return 1
            fi
            ;;
        stock)
            # Stock uses full-stack compose file (API + Frontend + MySQL)
            local fullstack_compose="$BASE_DIR/stockpredict/docker-compose.full-stack.yml"
            if [ -f "$fullstack_compose" ]; then
                cd "$BASE_DIR/stockpredict"
                # Build with --no-cache if requested
                if [ -n "$NO_CACHE_FLAG" ] && [ -n "$BUILD_FLAG" ]; then
                    print_color $YELLOW "🔨 Building Stock Predict with --no-cache..."
                    $COMPOSE_CMD -f docker-compose.full-stack.yml -p "$project_name" build --no-cache
                fi
                print_color $YELLOW "🚀 Starting Stock Predict Full-Stack (API + Frontend + MySQL)..."
                $COMPOSE_CMD -f docker-compose.full-stack.yml -p "$project_name" up -d $build_args
            elif [ -f "docker-compose.yml" ] && [ -f "docker-compose.local.yml" ]; then
                # Build with --no-cache if requested
                if [ -n "$NO_CACHE_FLAG" ] && [ -n "$BUILD_FLAG" ]; then
                    print_color $YELLOW "🔨 Building Stock services with --no-cache..."
                    $COMPOSE_CMD -f docker-compose.yml -f docker-compose.local.yml -p "$project_name" build --no-cache
                fi
                print_color $YELLOW "🚀 Starting Stock services (backend only)..."
                $COMPOSE_CMD -f docker-compose.yml -f docker-compose.local.yml -p "$project_name" up -d $build_args
            elif [ -f "docker-compose.yml" ]; then
                # Build with --no-cache if requested
                if [ -n "$NO_CACHE_FLAG" ] && [ -n "$BUILD_FLAG" ]; then
                    print_color $YELLOW "🔨 Building Stock services with --no-cache..."
                    $COMPOSE_CMD -f docker-compose.yml -p "$project_name" build --no-cache
                fi
                print_color $YELLOW "🚀 Starting Stock services (base only)..."
                $COMPOSE_CMD -f docker-compose.yml -p "$project_name" up -d $build_args
            else
                print_color $RED "docker-compose files not found"
                return 1
            fi
            ;;
        math)
            # Math uses docker-compose.yml
            if [ -f "docker-compose.yml" ]; then
                # Build with --no-cache if requested
                if [ -n "$NO_CACHE_FLAG" ] && [ -n "$BUILD_FLAG" ]; then
                    print_color $YELLOW "🔨 Building Math with --no-cache..."
                    $COMPOSE_CMD -f docker-compose.yml -p "$project_name" build --no-cache
                fi
                print_color $YELLOW "🚀 Starting Math services..."
                $COMPOSE_CMD -f docker-compose.yml -p "$project_name" up -d $build_args
            else
                print_color $RED "docker-compose.yml not found in $project_dir"
                return 1
            fi
            ;;
    esac

    print_color $GREEN "✓ $project_name deployed successfully!"
}

# Function to show deployment summary
show_deployment_summary() {
    print_header "Deployment Summary"
    
    echo
    print_color $MAGENTA "Selected Projects:"
    for project in "${SELECTED_PROJECTS[@]}"; do
        case $project in
            ceramic)
                print_color $GREEN "  ✓ Ceramic Mobile App Backend"
                ;;
            stock)
                print_color $GREEN "  ✓ Stock Predict Backend"
                ;;
            math)
                print_color $GREEN "  ✓ Mathematics Mobile Backend"
                ;;
        esac
    done
    
    if [ "$SETUP_OLLAMA" = true ]; then
        print_color $GREEN "  ✓ Ollama LLM Setup"
    fi

    if [ "$SETUP_NGINX" = true ]; then
        print_color $GREEN "  ✓ Nginx Unified Gateway"
    fi

    if [ ${#SELECTED_PROJECTS[@]} -eq 0 ] && [ "$SETUP_OLLAMA" = false ] && [ "$SETUP_NGINX" = false ]; then
        print_color $YELLOW "  No projects selected for deployment"
    fi
    
    echo
    print_color $MAGENTA "Build Option:"
    if [ -n "$BUILD_FLAG" ]; then
        print_color $GREEN "  ✓ Build images before deployment"
        if [ -n "$NO_CACHE_FLAG" ]; then
            print_color $GREEN "  ✓ Using --no-cache (fresh build)"
        else
            print_color $YELLOW "  ○ Using cached layers"
        fi
    else
        print_color $YELLOW "  ○ Use existing images"
    fi
    echo
}

# Function to check if NVIDIA GPU is available
check_nvidia_gpu() {
    if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
        return 0
    fi
    return 1
}

# Function to check if nvidia-container-toolkit is installed
check_nvidia_container_toolkit() {
    if dpkg -l 2>/dev/null | grep -q nvidia-container-toolkit; then
        return 0
    fi
    if rpm -q nvidia-container-toolkit &> /dev/null; then
        return 0
    fi
    return 1
}

# Function to install nvidia-container-toolkit
install_nvidia_container_toolkit() {
    print_color $BLUE "Installing NVIDIA Container Toolkit..."
    echo

    # Check if already installed
    if check_nvidia_container_toolkit; then
        print_color $GREEN "✓ NVIDIA Container Toolkit is already installed"
        return 0
    fi

    print_color $YELLOW "This requires sudo privileges."
    echo

    # Add NVIDIA GPG key and repository
    print_color $CYAN "Adding NVIDIA repository..."
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null

    # Install
    print_color $CYAN "Installing nvidia-container-toolkit..."
    sudo apt-get update -qq
    sudo apt-get install -y nvidia-container-toolkit

    # Configure Docker runtime
    print_color $CYAN "Configuring Docker runtime..."
    sudo nvidia-ctk runtime configure --runtime=docker
    sudo systemctl restart docker

    if check_nvidia_container_toolkit; then
        print_color $GREEN "✓ NVIDIA Container Toolkit installed successfully"
    else
        print_color $RED "✗ Failed to install NVIDIA Container Toolkit"
        return 1
    fi
}

# Function to setup Ollama
setup_ollama() {
    local ollama_compose_dir="$STOCK_DIR"

    if [ ! -d "$ollama_compose_dir" ]; then
        print_color $RED "Error: Stock microservices directory not found: $ollama_compose_dir"
        print_color $RED "Ollama is defined in the Stock Predict docker-compose.yml"
        return 1
    fi

    print_header "Ollama LLM Setup"

    # Step 1: GPU detection
    print_color $BLUE "🔍 Detecting GPU..."
    if check_nvidia_gpu; then
        local gpu_info
        gpu_info=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
        print_color $GREEN "✓ NVIDIA GPU detected: $gpu_info"

        # Check nvidia-container-toolkit
        if check_nvidia_container_toolkit; then
            print_color $GREEN "✓ NVIDIA Container Toolkit is installed"
        else
            print_color $YELLOW "⚠ NVIDIA Container Toolkit is NOT installed"
            if ask_yes_no "Do you want to install NVIDIA Container Toolkit for GPU support?" "y"; then
                install_nvidia_container_toolkit
            else
                print_color $YELLOW "○ Skipping GPU support, will use CPU mode"
                OLLAMA_PROFILE="cpu"
            fi
        fi

        # Ask GPU or CPU mode (if toolkit is available)
        if [ -z "$OLLAMA_PROFILE" ]; then
            if ask_yes_no "Do you want to run Ollama with GPU acceleration?" "y"; then
                OLLAMA_PROFILE="gpu"
                print_color $GREEN "✓ Ollama will run with GPU acceleration"
            else
                OLLAMA_PROFILE="cpu"
                print_color $YELLOW "○ Ollama will run in CPU-only mode"
            fi
        fi
    else
        print_color $YELLOW "⚠ No NVIDIA GPU detected - using CPU mode"
        OLLAMA_PROFILE="cpu"
    fi

    # Step 2: Start Ollama container
    echo
    print_color $BLUE "🚀 Starting Ollama container (profile: $OLLAMA_PROFILE)..."
    cd "$ollama_compose_dir"
    $COMPOSE_CMD --profile "$OLLAMA_PROFILE" up -d ollama 2>/dev/null || \
    $COMPOSE_CMD --profile "$OLLAMA_PROFILE" up -d ollama-gpu 2>/dev/null || true

    # Wait for Ollama to be ready
    print_color $YELLOW "⏳ Waiting for Ollama to start..."
    local retries=0
    local max_retries=30
    while [ $retries -lt $max_retries ]; do
        if docker exec stock_ollama ollama list &>/dev/null 2>&1; then
            break
        fi
        sleep 2
        retries=$((retries + 1))
        printf "."
    done
    echo

    if [ $retries -ge $max_retries ]; then
        print_color $RED "✗ Ollama did not start within 60 seconds"
        print_color $YELLOW "You can try manually: docker logs stock_ollama"
        return 1
    fi

    print_color $GREEN "✓ Ollama is running"

    # Step 3: Pull the model
    echo
    print_color $BLUE "📥 Pulling llama3.1 model (this may take a while on first run)..."
    docker exec stock_ollama ollama pull llama3.1

    if [ $? -eq 0 ]; then
        print_color $GREEN "✓ llama3.1 model is ready"
    else
        print_color $RED "✗ Failed to pull llama3.1 model"
        print_color $YELLOW "You can pull it manually later: docker exec stock_ollama ollama pull llama3.1"
        return 1
    fi

    echo
    print_color $GREEN "✓ Ollama setup complete! (Profile: $OLLAMA_PROFILE)"
}

# Main interactive flow
main() {
    clear
    print_header "Interactive Multi-Project Deployment"

    print_color $MAGENTA "Welcome to the Multi-Project Deployment Tool!"
    print_color $MAGENTA "This tool will help you deploy your backend services."
    echo

    # Show detected base directory
    print_color $CYAN "📂 Base directory: $BASE_DIR"
    echo

    # Check Docker
    print_color $BLUE "🔍 Checking Docker..."
    check_docker
    print_color $GREEN "✓ Docker is running"

    # Initialize compose command
    COMPOSE_CMD=$(get_compose_cmd)
    print_color $GREEN "✓ Docker Compose detected: $COMPOSE_CMD"
    
    # Create and load environment
    create_env_file
    load_env
    
    echo
    print_header "Project Status Overview"
    
    # Show current status
    print_color $CYAN "Current project status:"
    echo
    printf "  %-30s %s\n" "Ceramic Mobile App:" "$(get_project_status ceramic)"
    printf "  %-30s %s\n" "Stock Predict:" "$(get_project_status stockpredict)"
    printf "  %-30s %s\n" "Mathematics Mobile:" "$(get_project_status mathematic)"
    echo
    
    # Ask about deployment mode
    print_header "Deployment Configuration"
    
    # Ask about building
    if ask_yes_no "Do you want to build images before deployment?" "n"; then
        BUILD_FLAG="--build"
        print_color $GREEN "✓ Images will be built before deployment"

        # Ask about no-cache (only if building)
        if ask_yes_no "Do you want to build with --no-cache (fresh build, ignores cache)?" "n"; then
            NO_CACHE_FLAG="--no-cache"
            print_color $GREEN "✓ Build will use --no-cache (fresh build)"
        else
            print_color $YELLOW "○ Using cached layers"
        fi
    else
        print_color $YELLOW "○ Using existing images"
    fi
    
    echo
    print_header "Project Selection"
    
    # Ask about each project
    # Ceramic
    show_project_info "ceramic"
    if ask_yes_no "Do you want to deploy Ceramic Mobile App Backend?" "y"; then
        SELECTED_PROJECTS+=("ceramic")
        print_color $GREEN "✓ Ceramic Mobile App Backend selected"
    else
        print_color $YELLOW "○ Skipping Ceramic Mobile App Backend"
    fi
    
    echo
    
    # Stock
    show_project_info "stock"
    if ask_yes_no "Do you want to deploy Stock Predict Backend?" "y"; then
        SELECTED_PROJECTS+=("stock")
        print_color $GREEN "✓ Stock Predict Backend selected"
    else
        print_color $YELLOW "○ Skipping Stock Predict Backend"
    fi
    
    echo
    
    # Mathematics
    show_project_info "math"
    if ask_yes_no "Do you want to deploy Mathematics Mobile Backend?" "y"; then
        SELECTED_PROJECTS+=("math")
        print_color $GREEN "✓ Mathematics Mobile Backend selected"
    else
        print_color $YELLOW "○ Skipping Mathematics Mobile Backend"
    fi

    echo

    # Ollama LLM Setup
    print_box "Ollama LLM (for Knowledge QA)" \
             "GPU/CPU | Model: llama3.1 | Used by Stock Knowledge QA"
    if ask_yes_no "Do you want to setup Ollama LLM?" "n"; then
        SETUP_OLLAMA=true
        print_color $GREEN "✓ Ollama LLM setup selected"
    else
        print_color $YELLOW "○ Skipping Ollama LLM setup"
    fi

    echo

    # Nginx Unified Gateway Setup
    print_box "Nginx Unified API Gateway" \
             "Port 80 | Path-based routing | CORS enabled"
    if ask_yes_no "Do you want to setup Nginx as unified gateway?" "n"; then
        SETUP_NGINX=true
        print_color $GREEN "✓ Nginx setup selected"
    else
        print_color $YELLOW "○ Skipping Nginx setup"
    fi

    # Show summary and confirm
    show_deployment_summary

    if [ ${#SELECTED_PROJECTS[@]} -eq 0 ] && [ "$SETUP_OLLAMA" = false ] && [ "$SETUP_NGINX" = false ]; then
        print_color $YELLOW "No projects selected. Exiting."
        exit 0
    fi

    if ask_yes_no "Proceed with deployment?" "y"; then
        print_header "Deploying Projects"

        for project in "${SELECTED_PROJECTS[@]}"; do
            echo
            deploy_project "$project"
        done

        # Setup Ollama if selected
        if [ "$SETUP_OLLAMA" = true ]; then
            echo
            setup_ollama
        fi

        # Setup Nginx if selected
        if [ "$SETUP_NGINX" = true ]; then
            echo
            setup_nginx_config
        fi

        echo
        print_header "Deployment Complete!"
        
        print_color $GREEN "All selected projects have been deployed successfully!"
        echo
        print_color $CYAN "Access your services at:"

        if [[ " ${SELECTED_PROJECTS[@]} " =~ " ceramic " ]]; then
            echo
            print_color $WHITE "  ┌─ Ceramic Mobile App ─────────────────────────────────┐"
            print_color $YELLOW "  │ API Gateway:        http://localhost:8002"
            print_color $YELLOW "  │ Traefik Dashboard:  http://localhost:8080"
            print_color $YELLOW "  │ Auth API:           http://localhost:8002/api/v1/auth"
            print_color $YELLOW "  │ Products API:       http://localhost:8002/api/v1/products"
            print_color $WHITE "  └─────────────────────────────────────────────────────┘"
        fi

        if [[ " ${SELECTED_PROJECTS[@]} " =~ " stock " ]]; then
            echo
            print_color $WHITE "  ┌─ Stock Predict Full-Stack ──────────────────────────────┐"
            print_color $YELLOW "  │ Frontend App:       http://localhost:3004"
            print_color $YELLOW "  │ API Gateway:        http://localhost:8004"
            print_color $YELLOW "  │ Traefik Dashboard:  http://localhost:8084"
            print_color $YELLOW "  │ Stock API:          http://localhost:8004/stock_helper/api/v2/"
            print_color $YELLOW "  │ MySQL:              localhost:3309"
            print_color $YELLOW "  │ Grafana:            http://localhost:3100"
            print_color $YELLOW "  │ RabbitMQ:           http://localhost:15674"
            print_color $YELLOW "  │ Jaeger:             http://localhost:16686"
            print_color $WHITE "  └─────────────────────────────────────────────────────────┘"
        fi

        if [[ " ${SELECTED_PROJECTS[@]} " =~ " math " ]]; then
            echo
            print_color $WHITE "  ┌─ Mathematics Mobile ─────────────────────────────────┐"
            print_color $YELLOW "  │ API Gateway:        http://localhost:8003"
            print_color $YELLOW "  │ Traefik Dashboard:  http://localhost:8083"
            print_color $YELLOW "  │ Auth API:           http://localhost:8003/api/v1/auth"
            print_color $YELLOW "  │ Problems API:       http://localhost:8003/api/v1/problems"
            print_color $YELLOW "  │ Solutions API:      http://localhost:8003/api/v1/solutions"
            print_color $WHITE "  └─────────────────────────────────────────────────────┘"
        fi

        if [ "$SETUP_OLLAMA" = true ]; then
            echo
            print_color $WHITE "  ┌─ Ollama LLM ────────────────────────────────────────┐"
            print_color $YELLOW "  │ Profile:            $OLLAMA_PROFILE"
            print_color $YELLOW "  │ Model:              llama3.1"
            print_color $YELLOW "  │ Internal API:       http://ollama:11434 (Docker)"
            print_color $YELLOW "  │ Pull new model:     docker exec stock_ollama ollama pull <model>"
            print_color $WHITE "  └─────────────────────────────────────────────────────┘"
        fi

        if [ "$SETUP_NGINX" = true ]; then
            echo
            print_color $WHITE "  ┌─ Nginx Unified API Gateway ───────────────────────────┐"
            print_color $YELLOW "  │ Unified Gateway:    http://localhost/"
            print_color $YELLOW "  │ Ceramic API:        http://localhost/ceramic/"
            print_color $YELLOW "  │ Stock API:          http://localhost/stock/"
            print_color $YELLOW "  │ Math API:           http://localhost/math/"
            print_color $YELLOW "  │ Stock Frontend:     http://localhost/stock-app/"
            print_color $YELLOW "  │ Health Check:       http://localhost/health"
            print_color $WHITE "  └─────────────────────────────────────────────────────┘"
        fi

        echo
        print_color $CYAN "Port Allocation Summary:"
        print_color $WHITE "  Ceramic: 8002 | Math: 8003 | Stock: 8004"
        echo
        print_color $CYAN "To check the status of your services, run:"
        print_color $WHITE "  $SCRIPT_DIR/deploy-projects.sh status"
        echo
        print_color $CYAN "To view logs, run:"
        print_color $WHITE "  $SCRIPT_DIR/deploy-projects.sh logs [project_name]"
        echo
    else
        print_color $YELLOW "Deployment cancelled."
    fi
}

# Run main function
main