"""
Indicator Repository
Database operations for technical indicators
"""

from typing import Dict, List, Optional
import json
from repositories.base_repository import BaseRepository
from core.exceptions import DatabaseException


class IndicatorRepository(BaseRepository):
    def __init__(self):
        super().__init__()

    def table_name(self) -> str:
        """Return the primary table name for this repository"""
        return "technical_indicators"

    def get_all_indicators_by_category(self) -> Dict[str, List[Dict]]:
        """Get all indicators grouped by category"""
        query = """
            SELECT id, name, type, description, calculation_function, default_parameters
            FROM technical_indicators
            ORDER BY type, name
        """
        results = self.execute_query(query)

        # Group by category - includes all indicator types
        grouped = {
            'trend': [],
            'momentum': [],
            'volatility': [],
            'volume': [],
            'support_resistance': [],
            'price_transform': [],
            'bill_williams': []
        }

        for row in results:
            params = json.loads(row['default_parameters']) if row['default_parameters'] else {}
            indicator = {
                'id': row['id'],
                'name': row['name'],
                'type': row['type'],
                'description': row['description'],
                'calculation_function': row['calculation_function'],
                'default_parameters': params
            }
            # Handle any type, including new ones
            if row['type'] in grouped:
                grouped[row['type']].append(indicator)
            else:
                # Create new category if it doesn't exist
                grouped[row['type']] = [indicator]

        return grouped

    def get_indicators_by_type(self, indicator_type: str) -> List[Dict]:
        """Get indicators filtered by type"""
        query = """
            SELECT id, name, type, description, calculation_function, default_parameters
            FROM technical_indicators
            WHERE type = %s
            ORDER BY name
        """
        results = self.execute_query(query, (indicator_type,))

        return [{
            'id': row['id'],
            'name': row['name'],
            'type': row['type'],
            'description': row['description'],
            'calculation_function': row['calculation_function'],
            'default_parameters': json.loads(row['default_parameters']) if row['default_parameters'] else {}
        } for row in results]

    def get_indicator_by_id(self, indicator_id: int) -> Optional[Dict]:
        """Get specific indicator by ID"""
        query = """
            SELECT id, name, type, description, calculation_function, default_parameters
            FROM technical_indicators
            WHERE id = %s
        """
        results = self.execute_query(query, (indicator_id,))

        if not results:
            return None

        row = results[0]
        return {
            'id': row['id'],
            'name': row['name'],
            'type': row['type'],
            'description': row['description'],
            'calculation_function': row['calculation_function'],
            'default_parameters': json.loads(row['default_parameters']) if row['default_parameters'] else {}
        }

    def get_indicator_by_name(self, name: str) -> Optional[Dict]:
        """Get indicator by name"""
        query = """
            SELECT id, name, type, description, calculation_function, default_parameters
            FROM technical_indicators
            WHERE name = %s
        """
        results = self.execute_query(query, (name,))

        if not results:
            return None

        row = results[0]
        return {
            'id': row['id'],
            'name': row['name'],
            'type': row['type'],
            'description': row['description'],
            'calculation_function': row['calculation_function'],
            'default_parameters': json.loads(row['default_parameters']) if row['default_parameters'] else {}
        }

    def get_solution_indicators(self, solution_id: int) -> List[Dict]:
        """Get all indicators configured for a solution"""
        query = """
            SELECT
                si.id,
                si.solution_id,
                si.indicator_id,
                si.indicator_category,
                si.covariate_type,
                si.parameters,
                ti.name as indicator_name,
                ti.description,
                ti.calculation_function
            FROM solution_indicators si
            JOIN technical_indicators ti ON si.indicator_id = ti.id
            WHERE si.solution_id = %s
            ORDER BY si.indicator_category
        """
        results = self.execute_query(query, (solution_id,))

        return [{
            'id': row['id'],
            'solution_id': row['solution_id'],
            'indicator_id': row['indicator_id'],
            'indicator_category': row['indicator_category'],
            'indicator_type': row['indicator_category'],  # Backward compatibility alias
            'covariate_type': row['covariate_type'],
            'indicator_name': row['indicator_name'],
            'description': row['description'],
            'calculation_function': row['calculation_function'],
            'parameters': json.loads(row['parameters']) if row['parameters'] else None
        } for row in results]

    def add_solution_indicator(self, solution_id: int, indicator_id: int,
                              indicator_category: str, covariate_type: str = 'past',
                              parameters: Optional[Dict] = None) -> int:
        """
        Add an indicator to a solution

        Args:
            solution_id: Solution ID
            indicator_id: Technical indicator ID
            indicator_category: One of 'trend', 'momentum', 'volatility', 'volume'
            covariate_type: One of 'past', 'future', 'both' (default: 'past')
            parameters: Custom parameters (overrides template defaults)
        """
        params_json = json.dumps(parameters) if parameters else None

        query = """
            INSERT INTO solution_indicators (solution_id, indicator_id, indicator_category, covariate_type, parameters)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                indicator_id = VALUES(indicator_id),
                covariate_type = VALUES(covariate_type),
                parameters = VALUES(parameters),
                updated_at = CURRENT_TIMESTAMP
        """

        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute(query, (solution_id, indicator_id, indicator_category, covariate_type, params_json))
            connection.commit()
            return cursor.lastrowid or cursor.rowcount
        except Exception as e:
            if connection:
                connection.rollback()
            raise DatabaseException(f"Failed to add solution indicator: {str(e)}", e)
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def update_solution_indicator(self, solution_id: int, indicator_id: int,
                                 parameters: Dict) -> bool:
        """Update indicator parameters for a solution"""
        params_json = json.dumps(parameters)

        query = """
            UPDATE solution_indicators
            SET parameters = %s, updated_at = CURRENT_TIMESTAMP
            WHERE solution_id = %s AND indicator_id = %s
        """

        result = self.execute_non_query(query, (params_json, solution_id, indicator_id))
        return result > 0

    def remove_solution_indicator(self, solution_id: int, indicator_id: int) -> bool:
        """Remove an indicator from a solution"""
        query = """
            DELETE FROM solution_indicators
            WHERE solution_id = %s AND indicator_id = %s
        """

        result = self.execute_non_query(query, (solution_id, indicator_id))
        return result > 0

    def clear_solution_indicators(self, solution_id: int) -> bool:
        """Remove all indicators from a solution"""
        query = """
            DELETE FROM solution_indicators
            WHERE solution_id = %s
        """

        self.execute_non_query(query, (solution_id,))
        return True

    def get_solution_indicator_by_category(self, solution_id: int,
                                           indicator_category: str) -> Optional[Dict]:
        """Get a specific indicator category for a solution"""
        query = """
            SELECT
                si.id,
                si.solution_id,
                si.indicator_id,
                si.indicator_category,
                si.covariate_type,
                si.parameters,
                ti.name as indicator_name,
                ti.description,
                ti.calculation_function
            FROM solution_indicators si
            JOIN technical_indicators ti ON si.indicator_id = ti.id
            WHERE si.solution_id = %s AND si.indicator_category = %s
        """
        results = self.execute_query(query, (solution_id, indicator_category))

        if not results:
            return None

        row = results[0]
        return {
            'id': row['id'],
            'solution_id': row['solution_id'],
            'indicator_id': row['indicator_id'],
            'indicator_category': row['indicator_category'],
            'indicator_type': row['indicator_category'],  # Backward compatibility alias
            'covariate_type': row['covariate_type'],
            'indicator_name': row['indicator_name'],
            'description': row['description'],
            'calculation_function': row['calculation_function'],
            'parameters': json.loads(row['parameters']) if row['parameters'] else None
        }

    # Backward compatibility alias
    def get_solution_indicator_by_type(self, solution_id: int, indicator_type: str) -> Optional[Dict]:
        """Deprecated: Use get_solution_indicator_by_category instead"""
        return self.get_solution_indicator_by_category(solution_id, indicator_type)

    def create_indicator(self, name: str, indicator_type: str, description: str,
                        calculation_function: str, default_parameters: Dict) -> int:
        """Create a new technical indicator"""
        params_json = json.dumps(default_parameters) if default_parameters else None

        query = """
            INSERT INTO technical_indicators (name, type, description, calculation_function, default_parameters)
            VALUES (%s, %s, %s, %s, %s)
        """

        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute(query, (name, indicator_type, description, calculation_function, params_json))
            connection.commit()
            return cursor.lastrowid
        except Exception as e:
            if connection:
                connection.rollback()
            raise DatabaseException(f"Failed to create indicator: {str(e)}", e)
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def update_indicator(self, indicator_id: int, name: Optional[str] = None,
                        indicator_type: Optional[str] = None, description: Optional[str] = None,
                        calculation_function: Optional[str] = None,
                        default_parameters: Optional[Dict] = None) -> bool:
        """Update an existing technical indicator"""
        updates = []
        values = []

        if name is not None:
            updates.append("name = %s")
            values.append(name)

        if indicator_type is not None:
            updates.append("type = %s")
            values.append(indicator_type)

        if description is not None:
            updates.append("description = %s")
            values.append(description)

        if calculation_function is not None:
            updates.append("calculation_function = %s")
            values.append(calculation_function)

        if default_parameters is not None:
            updates.append("default_parameters = %s")
            values.append(json.dumps(default_parameters))

        if not updates:
            return True  # Nothing to update

        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(indicator_id)

        query = f"""
            UPDATE technical_indicators
            SET {', '.join(updates)}
            WHERE id = %s
        """

        result = self.execute_non_query(query, tuple(values))
        return result > 0

    def delete_indicator(self, indicator_id: int) -> bool:
        """Delete a technical indicator"""
        query = """
            DELETE FROM technical_indicators
            WHERE id = %s
        """

        result = self.execute_non_query(query, (indicator_id,))
        return result > 0
