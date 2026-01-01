import os
import logging
import pymysql
from pymysql.cursors import DictCursor

logger = logging.getLogger(__name__)


def get_db_connection():
    """Create a database connection"""
    return pymysql.connect(
        host=os.environ.get("DB_SERVER", "db"),
        port=int(os.environ.get("DB_PORT", 3306)),
        user=os.environ.get("DB_USER", "mathematic_user"),
        password=os.environ.get("DB_PASSWORD", "Mysql_2025"),
        database=os.environ.get("DB_NAME", "MathematicsSolverDb"),
        charset='utf8mb4',
        cursorclass=DictCursor,
        autocommit=True
    )


def init_db():
    """Initialize database tables"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Create Solutions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Solutions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                problem_id INT NOT NULL,
                user_id INT NOT NULL,
                solution_text TEXT NOT NULL,
                steps TEXT,
                method VARCHAR(50) NOT NULL DEFAULT 'symbolic',
                confidence DECIMAL(3,2) NOT NULL DEFAULT 0.90,
                processing_time_ms INT NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_problem_id (problem_id),
                INDEX idx_user_id (user_id),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        # Create SolutionFeedback table for future improvements
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS SolutionFeedback (
                id INT AUTO_INCREMENT PRIMARY KEY,
                solution_id INT NOT NULL,
                user_id INT NOT NULL,
                rating INT,
                is_correct BOOLEAN,
                feedback_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (solution_id) REFERENCES Solutions(id) ON DELETE CASCADE,
                INDEX idx_solution_id (solution_id),
                INDEX idx_user_id (user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        conn.commit()
        cursor.close()
        conn.close()

        logger.info("Database tables initialized successfully")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
