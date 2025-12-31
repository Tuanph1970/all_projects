import React from 'react';
import LoadingSpinner from './LoadingSpinner';
import ErrorMessage from './ErrorMessage';

const DataTable = ({
  data = [],
  columns = [],
  loading = false,
  error = null,
  onRetry = null,
  emptyMessage = 'Không có dữ liệu',
  className = '',
  striped = true,
  hover = true,
  bordered = false,
  actions = null
}) => {
  if (loading) {
    return (
      <div className="text-center p-4">
        <LoadingSpinner text="Đang tải dữ liệu..." />
      </div>
    );
  }

  if (error) {
    return (
      <ErrorMessage 
        message={error} 
        onRetry={onRetry}
        className="mb-0"
      />
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="text-center p-4 text-muted">
        <i className="fas fa-inbox fa-3x mb-3"></i>
        <p>{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className={`table-responsive ${className}`}>
      <table className={`table ${striped ? 'table-striped' : ''} ${hover ? 'table-hover' : ''} ${bordered ? 'table-bordered' : ''}`}>
        <thead className="table-dark">
          <tr>
            {columns.map((column, index) => (
              <th 
                key={index} 
                scope="col"
                style={{ width: column.width }}
                className={column.className}
              >
                {column.label || column.header}
              </th>
            ))}
            {actions && <th scope="col" className="text-center">Thao tác</th>}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {columns.map((column, colIndex) => (
                <td key={colIndex} className={column.cellClassName}>
                  {column.render ? column.render(row[column.key], row) : (row[column.key] ?? 'N/A')}
                </td>
              ))}
              {actions && (
                <td className="text-center">
                  {actions(row, rowIndex)}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default DataTable;