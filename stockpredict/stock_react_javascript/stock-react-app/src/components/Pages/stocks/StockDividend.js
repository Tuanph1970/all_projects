import React from "react";
import { useState, useEffect } from "react";
import DataTable from 'react-data-table-component';
import { Link } from "react-router-dom";
import { useTranslation } from 'react-i18next';
export const StockDividend = ({data}) => {
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
      sortable:true
    },
    {
      name: t('stocks.table.col_div_yield'),
      selector:row => row.Dividend_Yied,
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
