#!/bin/bash

# EF Core Migrations Creation Script
# This script creates initial migrations for both Auth and Problem services

set -e

echo "========================================="
echo "EF Core Migrations Creation Script"
echo "========================================="
echo ""

BACKEND_DIR="/home/tuanph/TuanPH/all_projects/mathematic-mobile/backend"

# Function to create migration for a service
create_migration() {
    local service_name=$1
    local service_path="$BACKEND_DIR/microservices/$service_name"
    
    echo "Creating migration for $service_name..."
    cd "$service_path"
    
    # Check if EF Core tools are installed
    if ! dotnet tool list --global | grep -q "dotnet-ef"; then
        echo "Installing EF Core tools..."
        dotnet tool install --global dotnet-ef --version 8.0.2
    fi
    
    # Restore packages
    echo "Restoring packages..."
    dotnet restore
    
    # Create migration
    echo "Creating InitialCreate migration..."
    dotnet ef migrations add InitialCreate \
        --context ${service_name^}DbContext \
        --output-dir Migrations
    
    echo "✅ Migration created for $service_name"
    echo ""
}

# Create migrations for Auth Service
create_migration "auth-service"

# Create migrations for Problem Service
create_migration "problem-service"

echo "========================================="
echo "✅ All migrations created successfully!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Review the generated migration files"
echo "2. Run 'dotnet ef database update' to apply migrations"
echo "3. Or use the seed script to create test data"
echo ""
