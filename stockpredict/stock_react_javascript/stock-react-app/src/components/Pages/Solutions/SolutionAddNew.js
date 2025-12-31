import {React,useState,useEffect} from 'react';
import { Tab, Tabs, TabList, TabPanel } from 'react-tabs';
import 'react-tabs/style/react-tabs.css';
import "bootstrap/dist/css/bootstrap.min.css";
import GeneralSollutionInfo from './SolutionDetailComponents/GeneralSolutionInfo';

import httpClient from '../../../services/httpClient';
import { API_ENDPOINTS } from '../../../constants/api';

export async function getModels(){
    const result = await httpClient.get(API_ENDPOINTS.MODELS_ALL);
    if (result.success) {
        return result.data || [];
    }
    console.error('Error fetching models:', result.error);
    return [];
}
export async function getTickers(){
    const result = await httpClient.get(API_ENDPOINTS.SOLUTION_TICKERS);
    if (result.success) {
        return result.data || [];
    }
    console.error('Error fetching tickers:', result.error);
    return [];
}
export async function getTimeSeries(){
    const result = await httpClient.get(API_ENDPOINTS.SOLUTION_COVARIATES);
    if (result.success) {
        return result.data || [];
    }
    console.error('Error fetching time series:', result.error);
    return [];
}

const SolutionAddNew = ()=>{
    const [tickerList,setTickerList ] = useState([])
    const [modelList,setModelList] = useState([])
    const [timeSeries,setTimeSeries] = useState([])
    const [isLoading,setIsLoading] = useState(true)

    useEffect(() => {
        const loadData = async () => {
            try {
                setIsLoading(true)
                const [models, tickers, timeSeriesData] = await Promise.all([
                    getModels(),
                    getTickers(),
                    getTimeSeries()
                ])
                setModelList(models)
                setTickerList(tickers)
                setTimeSeries(timeSeriesData)
            } catch (error) {
                console.error('Error loading data:', error)
            } finally {
                setIsLoading(false)
            }
        }
        loadData()
    }, []);

    if (isLoading){
        return(
        <div className='services'>
            <p> Loading data...</p>;
        </div>
        )
    }

    // Handle empty portfolio case
    if (tickerList.length === 0) {
        return (
            <div className="services">
                <div className="alert alert-warning" role="alert">
                    <h4 className="alert-heading">No Stocks in Portfolio</h4>
                    <p>You need to add stocks to your portfolio before creating a solution.</p>
                    <hr />
                    <p className="mb-0">
                        Go to <a href="/portfolio">Portfolio</a> to add stocks first.
                    </p>
                </div>
            </div>
        )
    }

    return (
        <div className="services">
            <Tabs>
            <TabList>
              <Tab>General Infomation</Tab>
              <Tab>Train</Tab>
              <Tab>Predict</Tab>
            </TabList>

            <TabPanel>
            {tickerList.length >0 && modelList.length > 0 && timeSeries.length > 0 ?
                <p><GeneralSollutionInfo tickers={tickerList} models={modelList} timeseies={timeSeries} solution = {null}/></p> : null
             }
            </TabPanel>
            <TabPanel>
               <p> This info will show when new solution </p>

            </TabPanel>
            <TabPanel>
                <p> Testing Param</p>

            </TabPanel>

        </Tabs>
        </div>

    )

}
export default SolutionAddNew;