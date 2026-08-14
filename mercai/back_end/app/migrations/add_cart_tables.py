"""
Add cart tables

This migration adds the cart and cart_items tables to support shopping cart functionality.
"""

from sqlalchemy import text

def upgrade(connection):
    """Add cart and cart_items tables"""
    
    # Create carts table
    connection.execute(text("""
        CREATE TABLE carts (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE KEY unique_user_cart (user_id),
            INDEX idx_carts_user_id (user_id)
        )
    """))
    
    # Create cart_items table
    connection.execute(text("""
        CREATE TABLE cart_items (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            cart_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            unit_price DECIMAL(10, 2) NOT NULL,
            total_price DECIMAL(10, 2) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
            UNIQUE KEY unique_cart_product (cart_id, product_id),
            INDEX idx_cart_items_cart_id (cart_id),
            INDEX idx_cart_items_product_id (product_id)
        )
    """))

def downgrade(connection):
    """Remove cart tables"""
    connection.execute(text("DROP TABLE IF EXISTS cart_items"))
    connection.execute(text("DROP TABLE IF EXISTS carts"))