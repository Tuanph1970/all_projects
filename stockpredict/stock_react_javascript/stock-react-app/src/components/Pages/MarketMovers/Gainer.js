import React from "react";
import { useState, useEffect } from "react";
import DataTable from 'react-data-table-component';
import axios from "axios";
import './MarketMovers.css';
import { API_ENDPOINTS } from '../../../constants/api';

// Custom styles for DataTable - Green theme for Gainers
const customStyles = {
    table: {
        style: {
            borderRadius: '10px',
            overflow: 'hidden',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
        },
    },
    headRow: {
        style: {
            background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
            minHeight: '50px',
            borderBottom: 'none',
        },
    },
    headCells: {
        style: {
            color: '#ffffff',
            fontSize: '0.75rem',
            fontWeight: '700',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            paddingLeft: '16px',
            paddingRight: '16px',
        },
    },
    rows: {
        style: {
            minHeight: '48px',
            fontSize: '0.8125rem',
            transition: 'all 0.15s ease',
            '&:hover': {
                backgroundColor: '#dcfce7',
                transform: 'scale(1.002)',
            },
        },
        stripedStyle: {
            backgroundColor: '#f0fdf4',
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
            borderTop: '1px solid #e2e8f0',
            backgroundColor: '#f8fafc',
        },
    },
};

const columns = [
    {
        name: 'Mã CP',
        selector: row => row.symbol || row.ticker,
        sortable: true,
        cell: row => (
            <span className="symbol-cell symbol-gainer">{row.symbol || row.ticker}</span>
        ),
    },
    {
        name: 'Tên công ty',
        selector: row => row.name || row.short_name,
        sortable: true,
        cell: row => (
            <span className="company-name-cell">{row.name || row.short_name}</span>
        ),
    },
    {
        name: 'Thay đổi',
        selector: row => row.change_percent || row.variation,
        sortable: true,
        cell: row => {
            const change = row.change_percent || row.variation || 0;
            return (
                <span className="change-cell positive">
                    ▲ {typeof change === 'number' ? change.toFixed(2) : change}%
                </span>
            );
        },
    },
    {
        name: 'Giá CP',
        selector: row => row.close,
        sortable: true,
        cell: row => (
            <span className="price-cell">
                {typeof row.close === 'number' ? row.close.toLocaleString() : row.close}
            </span>
        ),
        right: true,
    },
    {
        name: 'Khối lượng',
        selector: row => row.volume,
        sortable: true,
        cell: row => (
            <span className="volume-cell">
                {typeof row.volume === 'number' ? row.volume.toLocaleString() : row.volume}
            </span>
        ),
        right: true,
    },
    {
        name: 'Sàn GD',
        selector: row => row.exchange,
        sortable: true,
        cell: row => (
            <span className="exchange-cell">
                {row.exchange || 'N/A'}
            </span>
        ),
    },
];

const Gainers = () => {
    const [globalFilterText, setGlobalFilterText] = useState('');
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);

    const handleGlobalFilter = (e) => {
        const value = e.target.value || '';
        setGlobalFilterText(value);
    };

    useEffect(() => {
        axios.get(API_ENDPOINTS.TOP_GAINERS)
            .then(response => {
                setData(response.data);
                setLoading(false);
            })
            .catch(error => {
                console.error('Error fetching data:', error);
                setLoading(false);
            });
    }, []);

    const filteredData = data.filter((row) => {
        return Object.values(row).some((value) =>
            value.toString().toLowerCase().includes(globalFilterText.toLowerCase())
        );
    });

    return (
        <div className="market-movers-container gainers-container">
            <div className="market-movers-header">
                <div className="header-title">
                    <span className="header-icon">📈</span>
                    <h2>Cổ phiếu tăng mạnh nhất</h2>
                </div>
                <div className="header-stats">
                    <span className="stat-badge stat-badge-success">
                        {filteredData.length} cổ phiếu
                    </span>
                </div>
            </div>

            <div className="search-section">
                <div className="search-wrapper">
                    <span className="search-icon">🔍</span>
                    <input
                        type="text"
                        className="search-input"
                        placeholder="Tìm theo mã, tên hoặc giá trị..."
                        onChange={handleGlobalFilter}
                        value={globalFilterText}
                    />
                </div>
            </div>

            <div className="table-wrapper">
                <DataTable
                    columns={columns}
                    data={filteredData}
                    pagination
                    highlightOnHover
                    responsive
                    striped
                    paginationPerPage={10}
                    paginationRowsPerPageOptions={[5, 10, 20, 50]}
                    customStyles={customStyles}
                    progressPending={loading}
                    progressComponent={
                        <div className="loading-spinner">Đang tải dữ liệu...</div>
                    }
                    noDataComponent={
                        <div className="no-data">Không tìm thấy cổ phiếu tăng</div>
                    }
                />
            </div>
        </div>
    );
};

export default Gainers;
