import {React,useState,useEffect} from 'react';
import { useTranslation } from 'react-i18next';
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

const SolutionAddNew = ()=>{
    const { t } = useTranslation();
    const [tickerList,setTickerList ] = useState([])
    const [modelList,setModelList] = useState([])
    const [isLoading,setIsLoading] = useState(true)

    useEffect(() => {
        const loadData = async () => {
            try {
                setIsLoading(true)
                const [models, tickers] = await Promise.all([
                    getModels(),
                    getTickers()
                ])
                setModelList(models)
                setTickerList(tickers)
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
            <p>{t('solutions.loading_data')}</p>
        </div>
        )
    }

    // Handle empty portfolio case
    if (tickerList.length === 0) {
        return (
            <div className="services">
                <div className="alert alert-warning" role="alert">
                    <h4 className="alert-heading">{t('solutions.no_portfolio_title')}</h4>
                    <p>{t('solutions.no_portfolio_msg')}</p>
                    <hr />
                    <p className="mb-0">
                        Go to <a href="/portfolio">{t('solutions.no_portfolio_link_text')}</a> to add stocks first.
                    </p>
                </div>
            </div>
        )
    }

    return (
        <div className="services">
            <Tabs>
            <TabList>
              <Tab>{t('solutions.tab_general')}</Tab>
              <Tab>{t('solutions.tab_train')}</Tab>
              <Tab>{t('solutions.tab_predict')}</Tab>
            </TabList>

            <TabPanel>
            {tickerList.length > 0 && modelList.length > 0 ?
                <p><GeneralSollutionInfo tickers={tickerList} models={modelList} solution={null}/></p> : null
             }
            </TabPanel>
            <TabPanel>
               <p>{t('solutions.train_placeholder')}</p>

            </TabPanel>
            <TabPanel>
                <p>{t('solutions.predict_placeholder')}</p>

            </TabPanel>

        </Tabs>
        </div>

    )

}
export default SolutionAddNew;