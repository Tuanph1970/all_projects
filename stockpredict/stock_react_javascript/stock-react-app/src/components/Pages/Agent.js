import React,{useEffect,useState} from "react";
import { useTranslation } from 'react-i18next';
import DatePicker from "react-datepicker";

import "bootstrap/dist/css/bootstrap.min.css";
import { useForm } from "react-hook-form"
import httpClient from "../../services/httpClient";
import { API_ENDPOINTS } from "../../constants/api";

export async function getTickers(){
  const result = await httpClient.get(API_ENDPOINTS.SOLUTION_TICKERS);
  if (result.success) {
    return result.data || [];
  }
  console.error('Error fetching tickers:', result.error);
  return [];
}
export async function getAgents(){
  const result = await httpClient.get(API_ENDPOINTS.AGENTS_LIST);
  if (result.success) {
    return result.data || [];
  }
  console.error('Error fetching agents:', result.error);
  return [];
}

export const Agent = () => {
  const { t } = useTranslation();
  const [statistic,setStatistic] = useState([])
  const [startDate,setStartDate] = useState(new Date());
  const [endDate,setEndDate] = useState(new Date())
  const [isLoading,setIsLoading] = useState([])
  const [ticker,setTicker] = useState([]);
  const [agentType,setAgentType] = useState([]);
  const [agentName,setAgentName] = useState([]);
  const [tickers,setTickers] = useState([])
  const [agents,setAgents] = useState([])
  const [exHistory,setExHistory] = useState("")
  // eslint-disable-next-line no-unused-vars -- value set for future chart panel
  const [timeSeries,setTimeSeries] = useState([])
  const [trainingHistory,setTrainingHistory] = useState("")
  // eslint-disable-next-line no-unused-vars -- value set for future chart panel
  const [buyPoint,setBuyPoint] = useState([])
  // eslint-disable-next-line no-unused-vars -- value set for future chart panel
  const [sellPoint,setSellPoint] = useState([])
  const [agentParams,setAgentParams] = useState([])
  // eslint-disable-next-line no-unused-vars -- react-hook-form returns these for future validation hooks
  const { register,handleSubmit,reset,formState: { errors },watch} = useForm();
  const formSubmit = async (data) => {
      data['start_date'] = startDate.toISOString().split('T')[0]
      data['end_date'] = endDate.toISOString().split('T')[0]

      const agentEndpoint = agentType === 1 ? API_ENDPOINTS.AGENT_ML : API_ENDPOINTS.AGENT_GET;

      try {
        const result = await httpClient.post(agentEndpoint, data);
        if (result.success && result.data) {
            let statisticString = "current amount:" +
            result.data['current_amount'] + "\n" +
            "current_inventory:" +
            result.data['current_inventory'] + "\n" +
            "total_gain:" +
            result.data['total_gain'] + "\n";
            console.log(statisticString)
            setStatistic(statisticString)
            setExHistory(result.data['exchange_history'])
            setTrainingHistory(result.data['training_history'])
            setTimeSeries(result.data['time_series'])
            setBuyPoint(result.data['buy'])
            setSellPoint(result.data['sell'])
        } else {
            console.error('Error running agent:', result.error);
        }
      } catch (error) {
        console.error('Error running agent:', error);
      }
  }
  const handleAgentSelect = (value) =>{
     setAgentName(value);
     let currentAgent = agents.filter(agent=>agent['agent_name'] === value)[0]
     setAgentType(currentAgent['agent_type'])
     let cur_params = Object.entries(currentAgent)
     
     let activeParams = cur_params.filter((param)=>param[1] != null)
     activeParams = activeParams.filter((param)=>param[0] !== 'agent_name')
     activeParams = activeParams.filter((param)=>param[0] !== 'agent_type')
     setAgentParams(activeParams)
  }
  useEffect(() => {
          try {
              getAgents().then((agents)=>setAgents(agents))
              getTickers().then((tickers)=>setTickers(tickers))              
              setIsLoading(true)
          }
          catch{
  
          }
          finally{
              setIsLoading(false)
  
          }        
  }, []);
  if(isLoading) {
     return (
        <p>{t('agent.loading')}</p>
     )
  } else {
  return (

      <div className="services">
          <div className="container">
            <div className="card border-0 shadow p-6">
            <form onSubmit={handleSubmit(formSubmit)} >
              <table>
                 <tr>
                   <td >
                      <table >
                      <tr>
                        <td> <label>{t('agent.start_date')}</label></td>
                        <td> <DatePicker id="start_date" selected={startDate} dateFormat={"yyyy-MM-dd"} onChange={(date)=>setStartDate(new Date(date))}  /></td>
                      </tr>
                      <tr>
                        <td> <label>{t('agent.end_date')}</label></td>
                        <td> <DatePicker id="end_date" selected={endDate} dateFormat={"yyyy-MM-dd"} onChange={(date)=>setEndDate(new Date(date))}  /></td>
                      </tr>
                      <tr>
                      <td>
                            <label>{t('agent.ticker_label')}</label>
                            </td>
                            <td>
                            <select {...register("ticker")}
                                value={ticker}
                                onChange={(e)=>setTicker(e.target.value)}
                            >
                            <option value={null}>{t('agent.select_ticker')}</option>
                            {tickers.map((option_item) => (
                            <option value={option_item['ticker']}>
                                {option_item['ticker']}
                            </option>
                            ))}
                            </select>
                            </td>
                      </tr>
                      <tr>
                      <td>
                            <label>{t('agent.agent_label')}</label>
                            </td>
                            <td>
                            <select {...register("agent_name")}
                                value={agentName}
                                onChange={(e)=>handleAgentSelect(e.target.value)}
                            >
                            <option value={null}>{t('agent.select_agent')}</option>
                            {agents.map((option_item) => (
                            <option value={option_item['agent_name']}>
                                {option_item['agent_name']}
                            </option>
                            ))}
                            </select>
                            </td>
                      </tr>
                      <tr>
                      <td>
                            <label>{t('agent.initial_money')}</label>
                            </td>
                            <td>
                              <input type="text" {...register("initial_money")} defaultValue={10000000} ></input>
                            </td>
                      </tr>
                      {agentParams.map((parameter)=>(
                        <tr>
                           <td> {parameter[0]}</td>
                           <td>
                             <input type="text" id={parameter[0]} {...register(parameter[0])} defaultValue={parameter[1]} />
                           </td>
                        </tr>
                      ))

                    }
                    <tr>
                      <td colSpan={2}>
                        <button type="submit" className="btn btn-primary">{t('agent.run_btn')}</button>
                      </td>
                    </tr>
                    </table>

                   </td>
                   <td>
                      <table>
                        <tr>
                          <td>
                            <textarea value={statistic}>

                            </textarea>
                          </td>                          
                        </tr>
                        <tr>
                          <td>
                            <textarea value={exHistory}>
                              
                            </textarea>
                          </td>                          
                        </tr>
                        <tr>
                          <td>
                            <textarea value={trainingHistory}>

                            </textarea>
                             
                          </td>
                        </tr>
                        <tr>
                          <td>
                            
                          </td>
                        </tr>
                      </table>
                   </td>

                 </tr>
              </table>
                            

            </form>
            </div>
          </div>          
      </div>
  );
 };
};
