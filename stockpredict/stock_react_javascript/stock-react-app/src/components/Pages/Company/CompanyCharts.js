import React,{useEffect,useState} from "react";
import StockChart from "../../ui/StockChart";
import { useTranslation } from 'react-i18next';
import httpClient from "../../../services/httpClient";
import { API_ENDPOINTS } from "../../../constants/api";
import { Button } from "react-bootstrap";
import { ButtonGroup } from "react-bootstrap";
import Select from "react-dropdown-select";
import '../../../../node_modules/bootstrap/dist/css/bootstrap.min.css';

export default function CompanyCharts({symbol}) {
  const { t } = useTranslation(); 
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
      // eslint-disable-next-line react-hooks/exhaustive-deps
      }, [symbol]);
      if (isLoading) {
        return <p>{t('company_page.charts_loading')}</p>;
      }
      else {
        return (    
          <div>
             <div>
                 <ButtonGroup>
                    <Button onClick={oneWeekClick}>{t('company_page.charts_btn_1w')}</Button>
                    <Button onClick={oneMonthClick}>{t('company_page.charts_btn_1m')}</Button>
                    <Button onClick={oneYearClick}>{t('company_page.charts_btn_1y')}</Button>
                    <Button onClick={fiveYearClick}>{t('company_page.charts_btn_5y')}</Button>
                    <Button onClick={allRangeClick}>{t('company_page.charts_btn_all')}</Button>
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
              <StockChart initialData={periodStockData} symbol={symbol}/>
            </div>
          </div> 
        );
      }
};
