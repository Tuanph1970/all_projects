// Shared table styles for react-data-table-component

export const customTableStyles = {
  table: {
    style: {
      backgroundColor: 'transparent',
    },
  },
  headRow: {
    style: {
      backgroundColor: '#1e40af',
      borderRadius: '8px 8px 0 0',
      minHeight: '52px',
    },
  },
  headCells: {
    style: {
      color: '#ffffff',
      fontSize: '0.75rem',
      fontWeight: '600',
      textTransform: 'uppercase',
      letterSpacing: '0.05em',
      paddingLeft: '16px',
      paddingRight: '16px',
    },
  },
  rows: {
    style: {
      minHeight: '48px',
      fontSize: '0.875rem',
      color: '#1f2937',
      backgroundColor: '#ffffff',
      '&:nth-of-type(odd)': {
        backgroundColor: '#f8fafc',
      },
      '&:hover': {
        backgroundColor: '#e0f2fe',
        cursor: 'pointer',
      },
      borderBottomWidth: '1px',
      borderBottomColor: '#e5e7eb',
      borderBottomStyle: 'solid',
    },
    highlightOnHoverStyle: {
      backgroundColor: '#dbeafe',
      borderBottomColor: '#bfdbfe',
      outline: 'none',
    },
  },
  cells: {
    style: {
      paddingLeft: '16px',
      paddingRight: '16px',
    },
  },
  pagination: {
    style: {
      backgroundColor: '#f8fafc',
      borderTop: '1px solid #e5e7eb',
      borderRadius: '0 0 8px 8px',
    },
    pageButtonsStyle: {
      borderRadius: '6px',
      height: '32px',
      width: '32px',
      padding: '4px',
      margin: '2px',
      cursor: 'pointer',
      transition: '0.2s',
      color: '#1e40af',
      fill: '#1e40af',
      backgroundColor: 'transparent',
      '&:disabled': {
        cursor: 'not-allowed',
        color: '#9ca3af',
        fill: '#9ca3af',
      },
      '&:hover:not(:disabled)': {
        backgroundColor: '#dbeafe',
      },
      '&:focus': {
        outline: 'none',
        backgroundColor: '#bfdbfe',
      },
    },
  },
  noData: {
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '40px',
      color: '#6b7280',
      backgroundColor: '#f9fafb',
    },
  },
  progress: {
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '40px',
    },
  },
};

export const formatNumber = (value) => {
  if (value === null || value === undefined || value === '') return '-';
  const num = Number(value);
  if (isNaN(num)) return value;
  if (Math.abs(num) >= 1e9) {
    return (num / 1e9).toFixed(2) + 'B';
  } else if (Math.abs(num) >= 1e6) {
    return (num / 1e6).toFixed(2) + 'M';
  } else if (Math.abs(num) >= 1e3) {
    return (num / 1e3).toFixed(2) + 'K';
  }
  return num.toLocaleString(undefined, { maximumFractionDigits: 2 });
};

export const formatPercent = (value) => {
  if (value === null || value === undefined || value === '') return '-';
  const num = Number(value);
  if (isNaN(num)) return value;
  return num.toFixed(2) + '%';
};

export const getValueColor = (value) => {
  if (value === null || value === undefined) return '';
  const num = Number(value);
  if (isNaN(num)) return '';
  if (num > 0) return 'text-green-600 font-medium';
  if (num < 0) return 'text-red-600 font-medium';
  return '';
};

// Loading component
export const LoadingComponent = () => (
  <div className="flex items-center justify-center p-8">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    <span className="ml-3 text-gray-600">Loading data...</span>
  </div>
);

// No data component
export const NoDataComponent = () => (
  <div className="flex flex-col items-center justify-center p-8 text-gray-500">
    <svg className="w-12 h-12 mb-3 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
    <p>No data available</p>
  </div>
);
