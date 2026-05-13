import React from "react";
import { useState, useEffect } from "react";
import DataTable from 'react-data-table-component'
import { Link } from "react-router-dom";
export const StockPerformance = ({data}) => {
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
          Mã CK
          <input
            type="text"
            onChange={onChange}
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
      name:'Sàn', 
      selector:row => row.exchange, 
      sortable:true
  },
    {
        name:'Tên CT', 
        selector:row => row.short_name, 
        sortable:true
    },    
    {
      name:'Giá CP', 
      selector:row => row.close * 1000, 
      sortable:true
    },
    {
        name:'Thay đổi(%)', 
        selector:row => (row.close - row.open)/row.open*100, 
        sortable:true
    },
    {
      name:'Thay đổi(%) 1W', 
      selector:row => row.delta_in_week, 
      sortable:true
    },  
    {
        name:'Thay đổi(%) 1M', 
        selector:row => row.delta_in_month, 
        sortable:true
    },
    {
      name:'Thay đổi(%) 1Y', 
      selector:row => row.delta_in_year, 
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

