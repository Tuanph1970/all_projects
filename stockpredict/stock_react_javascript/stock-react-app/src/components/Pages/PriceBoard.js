import React, { useState, useEffect } from "react";
import { useTable } from "react-table";
import { useRouter } from "../../context/RouterContext";
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
  const { navigate } = useRouter()
  const handleCellClicked =(cell)  => {
     if (cell.column.id === 'symbol'){
      console.log("aaaa")
      navigate('company/' + cell.value)      
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
    const columns = React.useMemo(
        () => [
          {


            
            Header: "Mã CK",
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
            Header: "Trần",
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
            Header: "Sàn",
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
                Header: "TC",
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
            Header: "Dư mua",
            // First group columns
            columns: [
            {
              Header: "Giá 3",
              accessor: "buyPrice3",
              Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) }
            },
            {
              Header: "KL3",
              accessor: "buyQty3",
              Cell: (cellProps)  => {return getFontColorFromProps(cellProps.row.original.buyPrice3, cellProps, cellProps.value) }
            },
            {
              Header: "Giá 2",
              accessor: "buyPrice2",
              Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) }
            },
            {
            Header: "KL2",
            accessor: "buyQty2",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.row.original.buyPrice2, cellProps, cellProps.value) }
            },
            {
              Header: "Giá 1",
              accessor: "buyPrice1",
              Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) }
            },
            {
              Header: "KL1",
              accessor: "buyQty1",
              Cell: (cellProps)  => {return getFontColorFromProps(cellProps.row.original.buyPrice1, cellProps, cellProps.value) }

            },
            ],
            },
            {
            Header: "Khớp lệnh",
            // First group columns
            columns: [
            {
            Header: "Giá khớp",
            accessor: "matchPrice",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) }

            },
            {
            Header: "KL Khớp",
            accessor: "matchQty",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.row.original.matchPrice, cellProps, cellProps.value) }

            },
            {
            Header: "+/-",
            accessor: "change",
            },
            {
            Header: "+/-(%)",
            accessor: "changePercent",
            },
            ],
            },
            {
            // Second group - Details
            Header: "Dư bán",
            // Second group columns
            columns: [
            {
                Header: "Giá 1",
                accessor: "sellPrice1",
                Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps)},

            },
            {
            Header: "KL 1",
            accessor: "sellQty1",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.row.original.sellPrice1, cellProps, cellProps.value) }
            },
            {
            Header: "Giá 2",
            accessor: "sellPrice2",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) },
            },
            {
            Header: "KL 2",
            accessor: "sellQty2",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.row.original.sellPrice2, cellProps, cellProps.value) }
            },
            {
            Header: "Giá 3",
            accessor: "sellPrice3",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) },
            },
            {
            Header: "KL 3",
            accessor: "sellQty3",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.row.original.sellPrice3, cellProps, cellProps.value) }
            },
            ],
            },
            {
            Header: "Tổng KL",
            accessor: "totalQty",
            },
            {
            Header: "Mở cửa",
            accessor: "openPrice",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) },
            },
            {
            Header: "Cao nhất",
            accessor: "highest",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) },
            },
            {
            Header: "Thấp nhất",
            accessor: "lowest",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) },
            },
            ],
            []
      );
    const [data, setData] = useState([])
    useEffect(() => {
        const fetchPriceBoard = async () => {
          try {
            const result = await httpClient.get(API_ENDPOINTS.PRICEBOARDS);
            if (result.success && result.data) {
              console.log('PriceBoard API Response:', result.data);
              setData(result.data);
            } else {
              console.error('Error fetching price board data:', result.error);
            }
          } catch (error) {
            console.error('Error fetching price board data:', error);
          }
        };
        fetchPriceBoard();
      },[]);

      return (
        <div className="services" style={{ width: '100%', boxSizing: 'border-box' }}>
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


