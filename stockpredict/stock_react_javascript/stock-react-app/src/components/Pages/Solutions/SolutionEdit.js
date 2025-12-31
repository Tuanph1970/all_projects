import React,{useEffect,useState} from "react";
import { Tab, Tabs, TabList, TabPanel } from 'react-tabs';
import 'react-tabs/style/react-tabs.css';
import "bootstrap/dist/css/bootstrap.min.css";
import { useRouter } from '../../../context/RouterContext';
import GeneralSollutionInfo from './SolutionDetailComponents/GeneralSolutionInfo';
import TrainingSolution from './SolutionDetailComponents/TrainingSolution';
import PredictSolution from "./SolutionDetailComponents/PredictSolution";
import httpClient from '../../../services/httpClient';
import { API_ENDPOINTS } from '../../../constants/api';

export async function getSolution(solutionId){
    const result = await httpClient.get(API_ENDPOINTS.SOLUTION_DETAIL(solutionId));
    if (result.success) {
        return result.data;
    }
    console.error('Error fetching solution:', result.error);
    return null;
}
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

const SolutionEdit = ()=>{
    const { currentRoute } = useRouter();
    const [isLoading,setIsLoading] = useState(true)
    const [solution,setSolution] = useState(null)
    const [tickerList,setTickerList ] = useState([])
    const [modelList,setModelList] = useState([])
    const [timeSeries,setTimeSeries] = useState([])

    // State for prediction dates (auto-filled after training completes)
    const [predictionDates, setPredictionDates] = useState(null)
    // State for trained model info
    const [trainedModelInfo, setTrainedModelInfo] = useState(null)

    // Extract solutionId from currentRoute
    const solutionId = currentRoute.split('/')[1];

    // Callback to receive prediction dates from TrainingSolution
    const handleTrainingComplete = (trainingResult) => {
        if (trainingResult && trainingResult.prediction_dates) {
            setPredictionDates(trainingResult.prediction_dates)
            console.log('Training complete - Prediction dates set:', trainingResult.prediction_dates)
        }
        if (trainingResult && trainingResult.model_id) {
            setTrainedModelInfo({
                model_id: trainingResult.model_id,
                rmse: trainingResult.rmse
            })
            console.log('Training complete - Model info set:', trainingResult.model_id)
        }
    }

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

                if (solutionId) {
                    const solutiondata = await getSolution(solutionId)
                    console.log('[SolutionEdit] Solution loaded from API:', solutiondata);
                    console.log('[SolutionEdit] prediction_dates:', solutiondata?.prediction_dates);
                    setSolution(solutiondata)
                }
            } catch (error) {
                console.error('Error loading data:', error)
            } finally {
                setIsLoading(false)
            }
        }
        loadData()
    }, [solutionId]);
    if (isLoading){
        return(
        <div className='services'>
            <p> Loading data...</p>;
        </div>
        )

    } else {
        return (
            <div className="services">
                <Tabs>
            <TabList>
              <Tab>General Infomation</Tab>
              <Tab>Train</Tab>
              <Tab>Predict</Tab>
            </TabList>
            <TabPanel>
                {solution && solution["model_id"] > 0 ?
                <p><GeneralSollutionInfo tickers={tickerList} models={modelList} timeseies={timeSeries} solution={solution}/></p> : null
                }
            </TabPanel>
            <TabPanel>
               {solution && solution["id"] > 0 ?
               <p>
                 <TrainingSolution
                    models={modelList}
                    solution={solution}
                    onTrainingComplete={handleTrainingComplete}
                 />
               </p> : null
               }
            </TabPanel>
            <TabPanel>
                {solution && solution["id"] > 0 ?
                <p>
                    <PredictSolution
                        solution={solution}
                        predictionDates={predictionDates}
                        trainedModelInfo={trainedModelInfo}
                    />
                </p> : null
                }

            </TabPanel>

            </Tabs>
            </div>
        )
    }

}
export default SolutionEdit;
