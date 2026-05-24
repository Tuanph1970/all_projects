import React from "react";
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import DataTable from 'react-data-table-component';
import { useTranslation } from 'react-i18next';
import { formatStockPrice, formatPercentageChange, formatMarketCap, formatVolume } from '../../../utils/currencyFormatter';
export const StockGeneral = ({data}) => {
  const { t } = useTranslation();
  const [tableRowsData, setTableRowsData] = useState(data);

  const onChange = async (e) => {
    var searchData = data.filter((item) =>
      item.ticker
        .toString()
        .toLowerCase()
        .includes(e.target.value.toLowerCase())
    );
    setTableRowsData(searchData);
  };
  function getFontColor(row) {
    if (row.close > row.open) return "blue";
    else if (row.close === row.open) return "yellow";
    return "red";
  }

  const general_columns = [
    {
      name: (
        <div>
          {t('stocks.table.col_ticker')}
          <input
            type="text"
            onChange={onChange}
            placeholder={t('stocks.table.ticker_search')}
            style={{ width: "50%", marginLeft: "10px" }}
          />
          </div>
        ),
        selector: row => row.ticker,
        sortable:true,
        cell: row => (
          <Link to={{
            pathname: `../company/${row.ticker}`,
          }}>{row.ticker}</Link>
        ),
    },
    {
      name: t('stocks.table.col_exchange'),
      selector:row => row.exchange,
      sortable:true
  },
    {
        name: t('stocks.table.col_company'),
        selector:row => row.short_name,
        sortable:true
    },
    {
      name: t('stocks.table.col_market_cap'),
      selector:row => row.MarketCap,
      sortable:true,
      cell: row => formatMarketCap(row.MarketCap)
    },
    {
      name: t('stocks.table.col_price'),
      selector:row => row.close,
      sortable:true,
      cell: row => formatStockPrice(row.close)
    },
    {
        name: t('stocks.table.col_change_pct'),
        selector:row => (row.close - row.open)/row.open*100,
        sortable:true,
        cell: (row) => {
          const changePercent = (row.close - row.open)/row.open*100;
          return (
            <div style={{color: getFontColor(row)}}>
              {formatPercentageChange(changePercent)}
            </div>
          );
        }
    },
    {
      name: t('stocks.table.col_industry'),
      selector:row => row.industry,
      sortable:true
    },
    {
        name: t('stocks.table.col_volume'),
        selector:row => row.volume,
        sortable:true,
        cell: row => formatVolume(row.volume)
    },
    {
      name: t('stocks.table.col_pe_ratio'),
      selector:row => row.PE,
      sortable:true
    },

  ]
  useEffect(() => {}, [tableRowsData]);
  return (
    <table>
        <tr>
            <td>
        <DataTable
        columns = {general_columns}
        data = {tableRowsData}
        defaultSortField="ticker"
        pagination
        hightlightOnHover
        responsive
        paginationPerPage={30}
        paginationRowsPerPargeOptions = {[30,50,100]}

      />
            </td>
        </tr>
    </table>
  );
}
