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
function getFontColorFromProps(value, cellProps) {
    const current_value = parseFloat(value);
    const ceiling = parseFloat(cellProps.row.original.listingceiling);
    const ref_value = parseFloat(cellProps.row.original.listingref_price);
    const floor_value = parseFloat(cellProps.row.original.listingfloor);

    // Handle missing or invalid data
    if (isNaN(current_value) || isNaN(ceiling) || isNaN(ref_value) || isNaN(floor_value)) {
        return (
            <span style={{ color: "white" }}>
                {value || "N/A"}
            </span>
        );
    }

    if (current_value === ceiling) {
     return (
       <span style={{ color:"magenta" }}>
       {current_value}
       </span>
     );
   }
   else if((current_value < ceiling) && (current_value > ref_value)){
     return (
       <span style={{ color:"#00BFFF" }}>
       {current_value}
       </span>
     );
   }
   else if(current_value === ref_value)  {
     return(
     <span style={{ color:"yellow" }}>
     {current_value}
     </span>
     );

   }
   else if((current_value < ref_value) && (current_value > floor_value))  {
     return(
     <span style={{ color:"red" }}>
     {current_value}
     </span>
     );
   }
   else if(current_value === floor_value){
     return(
       <span style={{ color:"#00FF00" }}>
       {current_value}
       </span>
     );
   }
   else return(
     <span style={{ color:"white" }}>
     {current_value}
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
            accessor: "listingceiling",
            key: "listingceiling",
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
            accessor: "listingfloor",
            key: "listingfloor",
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
                accessor: "listingref_price",
                key:"listingref_price",
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
              accessor: "bid_askbid_3_price",              
              Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) }
            },
            {
              Header: "KL3",
              accessor: "bid_askbid_3_volume",
              Cell: (cellProps)  => {return getFontColorFromProps(cellProps.row.original.bid_askbid_3_price,cellProps) }
            },
            {
              Header: "Giá 2",
              accessor: "bid_askbid_2_price",
              Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) }
            },
            {
            Header: "KL2",
            accessor: "bid_askbid_2_volume",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.row.original.bid_askbid_2_price,cellProps) }
            },
            {
              Header: "Giá 1",
              accessor: "bid_askbid_1_price",
              Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) }
            },
            {
              Header: "KL1",
              accessor: "bid_askbid_1_volume",
              Cell: (cellProps)  => {return getFontColorFromProps(cellProps.row.original.bid_askbid_1_price,cellProps) }
              
            },
            ],
            },
            {
            Header: "Khớp lệnh",
            // First group columns
            columns: [
            {
            Header: "Giá khớp",
            accessor: "matchmatch_price",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) }
            

            },
            {
            Header: "KL Khớp",
            accessor: "matchmatch_vol",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.row.original.matchmatch_price,cellProps) }

            },
            {
            Header: "+/-",
            accessor: "matchvol_variation",
            },
            {
            Header: "+/-(%)",
            accessor: "matchvol_percent",
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
                accessor: "bid_askask_1_price",
                Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps)},
            
            },
            {
            Header: "KL 1",
            accessor: "bid_askask_1_volume",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.row.original.bid_askask_1_price,cellProps) }
            },
            {
            Header: "Giá 2",
            accessor: "bid_askask_2_price",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) },
            },
            {
            Header: "KL 2",
            accessor: "bid_askask_2_volume",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.row.original.bid_askask_2_price,cellProps) }
            },
            {
            Header: "Giá 3",
            accessor: "bid_askask_3_price",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) },
            },
            {
            Header: "KL 3",
            accessor: "bid_askask_3_volume",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.row.original.bid_askask_3_price,cellProps) }
            },
            ], 
            },
            {
            Header: "Tổng KL",
            accessor: "matchaccumulated_volume",
            },
            {
            Header: "Mở cửa",
            accessor: "matchopen_price",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) },
            },
            {
            Header: "Cao nhất",
            accessor: "matchhighest",
            Cell: (cellProps)  => {return getFontColorFromProps(cellProps.value,cellProps) },
            },
            {
            Header: "Thấp nhất",
            accessor: "matchlowest",
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


