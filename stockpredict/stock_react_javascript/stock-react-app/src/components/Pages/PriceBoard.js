import React, { useState, useEffect } from "react";
import { useTable } from "react-table";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import httpClient from "../../services/httpClient";
import { API_ENDPOINTS } from "../../constants/api";

const defaultPropGetter = () => ({});
// Expose some prop getters for headers, rows and cells, or more if you want!
function Table({
  columns,
  data,
  getHeaderProps = defaultPropGetter,
  getColumnProps = defaultPropGetter,
  getRowProps = defaultPropGetter,
  getCellProps = defaultPropGetter
}) {
  const navigate = useNavigate();
  const handleCellClicked = (cell) => {
    if (cell.column.id === 'symbol') {
      navigate('/company/' + cell.value);
    }
  };
  const {
    getTableProps,
    getTableBodyProps,
    headerGroups,
    rows,
    prepareRow
  } = useTable({
    columns,
    data
  });

  return (
    <table {...getTableProps()} className="custom-table">
      <thead>
        {headerGroups.map((headerGroup) => (
          <tr {...headerGroup.getHeaderGroupProps()}>
            {headerGroup.headers.map((column) => (
              <th
                // Return an array of prop objects and react-table will merge them appropriately
                {...column.getHeaderProps([
                  {
                    className: "custom-header",
                    style: column.style
                  },
                  getColumnProps(column),
                  getHeaderProps(column)
                ])}
              >
                {column.render("Header")}
              </th>
            ))}
          </tr>
        ))}
      </thead>
      <tbody {...getTableBodyProps()}>
        {rows.map((row, i) => {
          prepareRow(row);
          return (
            // Merge user row props in
            <tr {...row.getRowProps(getRowProps(row)) } >
              
              {row.cells.map((cell) => {
                return (
                  <td onClick={() => handleCellClicked(cell)}
                    // Return an array of prop objects and react-table will merge them appropriately
                    {...cell.getCellProps([
                      {
                        className: cell.column.className,
                        style: cell.column.style
                      },
                      getColumnProps(cell.column),
                      getCellProps(cell)
                    ])}
                  >
                    {cell.render("Cell")}
                  </td>
                );
              })}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
// colorValue: the value used to determine the color (usually a price)
// displayValue: the value to display (optional, defaults to colorValue)
function getFontColorFromProps(colorValue, cellProps, displayValue = null) {
    const color_val = parseFloat(colorValue);
    const display_val = displayValue !== null ? displayValue : colorValue;
    const ceiling = parseFloat(cellProps.row.original.ceiling);
    const ref_value = parseFloat(cellProps.row.original.refPrice);
    const floor_value = parseFloat(cellProps.row.original.floor);

    // Handle missing or invalid data for display value
    if (display_val === null || display_val === undefined || display_val === '') {
        return (
            <span style={{ color: "white" }}>
                N/A
            </span>
        );
    }

    // Handle missing or invalid data for color determination
    if (isNaN(color_val) || isNaN(ceiling) || isNaN(ref_value) || isNaN(floor_value)) {
        return (
            <span style={{ color: "white" }}>
                {display_val}
            </span>
        );
    }

    if (color_val === ceiling) {
     return (
       <span style={{ color:"magenta" }}>
       {display_val}
       </span>
     );
   }
   else if((color_val < ceiling) && (color_val > ref_value)){
     return (
       <span style={{ color:"#00BFFF" }}>
       {display_val}
       </span>
     );
   }
   else if(color_val === ref_value)  {
     return(
     <span style={{ color:"yellow" }}>
     {display_val}
     </span>
     );

   }
   else if((color_val < ref_value) && (color_val > floor_value))  {
     return(
     <span style={{ color:"red" }}>
     {display_val}
     </span>
     );
   }
   else if(color_val === floor_value){
     return(
       <span style={{ color:"#00FF00" }}>
       {display_val}
       </span>
     );
   }
   else return(
     <span style={{ color:"white" }}>
     {display_val}
     </span>
   );
 }
 const PriceBoard = () => {
    const { t } = useTranslation();
    const [refreshing, setRefreshing] = useState(false);
    const columns = React.useMemo(
        () => [
          {
            Header: t('priceboard.col_symbol'),
            accessor: "symbol",
            Cell: (props) => {
              return (
                <span style={{ color: "#00FFFF", fontWeight: "bold", cursor: "pointer" }}>
                  {props.value}
                </span>
              );
            }
            },
            {
            Header: t('priceboard.col_ceiling'),
            accessor: "ceiling",
            key: "ceiling",
            Cell: (props) => {
              return (
                <span style={{ color: "magenta" }}>
                  {props.value}
                </span>
              );
            }
            },
            {
            Header: t('priceboard.col_floor'),
            accessor: "floor",
            key: "floor",
            Cell: (props) => {
              return (
                <span style={{ color: "#00FF00" }}>
                  {props.value}
                </span>
              );
            }
            },
            {
                Header: t('priceboard.col_reference'),
                accessor: "refPrice",
                key:"refPrice",
                Cell: (props) => {
                  return (
                    <span style={{ color: "yellow" }}>
                      {props.value}
                    </span>
                  );
                }
            },
            {
            Header: t('priceboard.col_buy_group'),
            // First group columns
            columns: [
            {
              Header: t('priceboard.col_price_3'),
              accessor: "buyPrice3",
              Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) }
            },
            {
              Header: t('priceboard.col_qty_3'),
              accessor: "buyQty3",
              Cell: (cellProps)  => {return getFontColorFromProps(cellProps.row.original.buyPrice3, cellProps, cellProps.value) }
            },
            {
              Header: t('priceboard.col_price_2'),
              accessor: "buyPrice2",
              Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) }
            },
            {
            Header: t('priceboard.col_qty_2'),
            accessor: "buyQty2",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.row.original.buyPrice2, cellProps, cellProps.value) }
            },
            {
              Header: t('priceboard.col_price_1'),
              accessor: "buyPrice1",
              Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) }
            },
            {
              Header: t('priceboard.col_qty_1'),
              accessor: "buyQty1",
              Cell: (cellProps)  => {return getFontColorFromProps(cellProps.row.original.buyPrice1, cellProps, cellProps.value) }

            },
            ],
            },
            {
            Header: t('priceboard.col_match_group'),
            // First group columns
            columns: [
            {
            Header: t('priceboard.col_match_price'),
            accessor: "matchPrice",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) }

            },
            {
            Header: t('priceboard.col_match_qty'),
            accessor: "matchQty",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.row.original.matchPrice, cellProps, cellProps.value) }

            },
            {
            Header: t('priceboard.col_change_abs'),
            accessor: "change",
            },
            {
            Header: t('priceboard.col_change_pct'),
            accessor: "changePercent",
            },
            ],
            },
            {
            // Second group - Details
            Header: t('priceboard.col_sell_group'),
            // Second group columns
            columns: [
            {
                Header: t('priceboard.col_price_1'),
                accessor: "sellPrice1",
                Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps)},

            },
            {
            Header: t('priceboard.col_qty_1'),
            accessor: "sellQty1",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.row.original.sellPrice1, cellProps, cellProps.value) }
            },
            {
            Header: t('priceboard.col_price_2'),
            accessor: "sellPrice2",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) },
            },
            {
            Header: t('priceboard.col_qty_2'),
            accessor: "sellQty2",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.row.original.sellPrice2, cellProps, cellProps.value) }
            },
            {
            Header: t('priceboard.col_price_3'),
            accessor: "sellPrice3",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) },
            },
            {
            Header: t('priceboard.col_qty_3'),
            accessor: "sellQty3",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.row.original.sellPrice3, cellProps, cellProps.value) }
            },
            ],
            },
            {
            Header: t('priceboard.col_total_qty'),
            accessor: "totalQty",
            },
            {
            Header: t('priceboard.col_open'),
            accessor: "openPrice",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) },
            },
            {
            Header: t('priceboard.col_high'),
            accessor: "highest",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) },
            },
            {
            Header: t('priceboard.col_low'),
            accessor: "lowest",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) },
            },
            ],
            [t]
      );
    const [data, setData] = useState([])

    const fetchPriceBoard = async () => {
      try {
        const result = await httpClient.get(API_ENDPOINTS.PRICEBOARDS);
        if (result.success && result.data) {
          setData(result.data);
        } else {
          console.error('Error fetching price board data:', result.error);
        }
      } catch (error) {
        console.error('Error fetching price board data:', error);
      }
    };

    useEffect(() => {
        fetchPriceBoard();
      },[]);

    const handleRefresh = async () => {
      setRefreshing(true);
      try {
        await httpClient.post(`${API_ENDPOINTS.PRICEBOARDS}/refresh?group=VN30`);
        await fetchPriceBoard();
      } catch (error) {
        console.error('Error refreshing price board:', error);
      } finally {
        setRefreshing(false);
      }
    };

      return (
        <div className="services" style={{ width: '100%', boxSizing: 'border-box' }}>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              style={{
                padding: '6px 16px',
                backgroundColor: refreshing ? '#555' : '#1a73e8',
                color: '#fff',
                border: 'none',
                borderRadius: '4px',
                cursor: refreshing ? 'not-allowed' : 'pointer',
                fontSize: '13px',
              }}
            >
              {refreshing ? t('priceboard.refreshing') : t('priceboard.refresh')}
            </button>
          </div>
          <Table
            columns={columns}
            data={data}
            getRowProps={row => ({
                style: {
                  background: "#0F0F0F",
                },
              })}
          />
        </div>
      );
};
 
export default PriceBoard;


