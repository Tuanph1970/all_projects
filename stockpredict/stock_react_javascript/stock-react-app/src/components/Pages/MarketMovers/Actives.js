import React from "react";
import { useState, useEffect } from "react";
import DataTable from 'react-data-table-component';
import axios from "axios";
import './MarketMovers.css';
import { API_ENDPOINTS } from '../../../constants/api';

// Custom styles for DataTable - Blue theme for Most Actives
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
            background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
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
                backgroundColor: '#dbeafe',
                transform: 'scale(1.002)',
            },
        },
        stripedStyle: {
            backgroundColor: '#eff6ff',
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
        selector: row => row.ticker,
        sortable: true,
        cell: row => (
            <span className="symbol-cell symbol-active">{row.ticker}</span>
        ),
    },
    {
        name: 'Tên công ty',
        selector: row => row.short_name,
        sortable: true,
        cell: row => (
            <span className="company-name-cell">{row.short_name}</span>
        ),
    },
    {
        name: 'Thay đổi',
        selector: row => row.variation,
        sortable: true,
        cell: row => {
            const variation = typeof row.variation === 'number' ? row.variation : parseFloat(row.variation) || 0;
            const isPositive = variation >= 0;
            return (
                <span className={`change-cell ${isPositive ? 'positive' : 'negative'}`}>
                    {isPositive ? '▲' : '▼'} {Math.abs(variation).toFixed(2)}%
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
            <span className="volume-cell volume-highlight">
                {typeof row.volume === 'number' ? row.volume.toLocaleString() : row.volume}
            </span>
        ),
        right: true,
    },
    {
        name: 'Vốn hóa',
        selector: row => row.MarketCap,
        sortable: true,
        cell: row => (
            <span className="marketcap-cell">
                {typeof row.MarketCap === 'number' ? row.MarketCap.toLocaleString() : row.MarketCap}
            </span>
        ),
        right: true,
    },
];

const Actives = () => {
    const [globalFilterText, setGlobalFilterText] = useState('');
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);

    const handleGlobalFilter = (e) => {
        const value = e.target.value || '';
        setGlobalFilterText(value);
    };

    useEffect(() => {
        axios.get(API_ENDPOINTS.TOP_ACTIVES)
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
        <div className="market-movers-container actives-container">
            <div className="market-movers-header">
                <div className="header-title">
                    <span className="header-icon">🔥</span>
                    <h2>Giao dịch nhiều nhất</h2>
                </div>
                <div className="header-stats">
                    <span className="stat-badge stat-badge-primary">
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
                        <div className="no-data">Không tìm thấy cổ phiếu</div>
                    }
                />
            </div>
        </div>
    );
};

export default Actives;
