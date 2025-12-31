import React,{useEffect,useState} from "react";
import StockChart from "../../ui/StockChart";
import httpClient from "../../../services/httpClient";
import { API_ENDPOINTS } from "../../../constants/api";
import { Button } from "react-bootstrap";
import { ButtonGroup } from "react-bootstrap";
import Select from "react-dropdown-select";
import '../../../../node_modules/bootstrap/dist/css/bootstrap.min.css';

export default function CompanyCharts({symbol}) { 
    const [stockData, setStockData] = useState([]);
    const [isLoading, setIsLoading] = useState([]);
    const [periodStockData,setPeriodStockData] = useState([]);
    const options = [
      {
        value: 1,
        label: 'Leanne Graham'
      },
      {
        value: 2,
        label: 'Ervin Howell'
      }
    ]; 
    const selectItem = (values) => {
        console.log(values);
    }
    const oneWeekClick = () =>{
        let dataLen = stockData.length;
        setPeriodStockData(stockData.slice(dataLen-8,dataLen-1));

    }
    const oneMonthClick = () =>{
      let dataLen = stockData.length;
      setPeriodStockData(stockData.slice(dataLen-31,dataLen-1));

    }
    const oneYearClick = () =>{
      let dataLen = stockData.length;
      setPeriodStockData(stockData.slice(dataLen-364,dataLen-1));

    }
    const fiveYearClick = () =>{
      let dataLen = stockData.length;
      setPeriodStockData(stockData.slice(dataLen-1830,dataLen-1));

    }
    const allRangeClick = () =>{
      setPeriodStockData(stockData)

    }
    const styles = {
      fontSize: 16,
      color: 'blue',
      
    }
    useEffect(() => {
        (async () => {
          try {
            setIsLoading(true);
            const result = await httpClient.get(API_ENDPOINTS.STOCK_HISTORY(symbol));
            if (result.success && result.data) {
              const data = result.data.data || result.data;
              setPeriodStockData(data);
              setStockData(data);
            }
          } catch (error) {
            console.error("Error loading historical data:", error);
          } finally {
            console.log(periodStockData);
            setIsLoading(false);
          }
        })();
      }, [symbol]);
      if (isLoading) {
        return <p>Loading data...</p>;
      }
      else {
        return (    
          <div>
             <div>
                 <ButtonGroup>
                    <Button onClick={oneWeekClick} >1w</Button>
                    <Button onClick={oneMonthClick}>1m</Button> 
                    <Button onClick={oneYearClick}>1y</Button>
                    <Button onClick={fiveYearClick}>5y</Button>                    
                    <Button onClick={allRangeClick}>All</Button>
                    <div style={{width: '500px'}}>
                    <Select
                        menuPlacement="auto"
                        menuPosition="fixed"
                        options={options}
                        values={[]}
                        required
                        multi
                        name="select"
                        style={styles}                        
                        onChange={(value) => selectItem(value)}
                    />
                    </div>
                 </ButtonGroup>
             </div>
             <div>
              <StockChart initialData={periodStockData}/>
            </div>
          </div> 
        );
      }
};
