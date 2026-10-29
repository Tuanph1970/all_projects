import React,{useState} from "react";
import { useTranslation } from 'react-i18next';
import { useForm } from "react-hook-form"
import httpClient from "../../../../services/httpClient";
import { API_ENDPOINTS } from "../../../../constants/api";
import { useNavigate } from "react-router-dom";
const GeneralSollutionInfo = (props) =>{
    const { t } = useTranslation();
    const navigate = useNavigate();
    // eslint-disable-next-line no-unused-vars -- react-hook-form returns bindings not all used yet
    const { register,handleSubmit,reset,formState: { errors },watch} = useForm();
    let sol_name = ""
    let model_id = -1
    let tick = -1
    if(props.solution){
        sol_name = props.solution['solution_name']
        model_id = props.solution['model_id']
        tick = props.solution['ticker']
    }
    const [solution_name, setSolutionName] = useState(sol_name)
    const [modelId,setModelId] = useState(model_id)
    const [ticker, setTicker] = useState(tick)
    const formSubmit = async (data) => {                   
        if(props.solution != null){
            data['updated_by'] = 0
            data['id'] = props.solution['id']
            data['updated_date'] = (new Date()).toISOString().replace("T"," ").substring(0, 19)            

        }else {
            data['created_by'] = 0
            data['id'] =  0
            data['created_date'] = (new Date()).toISOString().replace("T"," ").substring(0, 19)            
        }
        
        
        data['status'] = 1        
        data['model_id'] = parseInt(data['model_id'])
        
        if (props.solution == null) {
            const result = await httpClient.post(API_ENDPOINTS.SOLUTION_CREATE, data);
            if (result.success) {
                window.alert("add success");
            } else {
                window.alert("add failed: " + (result.error?.message || 'Unknown error'));
            }
        } else {
            const result = await httpClient.put(API_ENDPOINTS.SOLUTION_UPDATE(data.id), data);
            if (result.success) {
                window.alert("update success");
            } else {
                window.alert("update failed: " + (result.error?.message || 'Unknown error'));
            }
        }
        window.history.back();
        
        
    }
    if (!props.models || props.models.length === 0) {
        return (
            <div className="container">
                <div className="card border-0 shadow p-3 text-center">
                    <p>{t('solutions.no_models_msg')}</p>
                    <button
                        type="button"
                        className="btn btn-primary"
                        onClick={() => navigate('/models')}
                    >
                        {t('solutions.go_to_models_btn')}
                    </button>
                </div>
            </div>
        );
    }

    return (
        <>
        <div className="container">
            <div className="card border-0 shadow p-3">
                <form onSubmit={handleSubmit(formSubmit)}>
                    <table>
                        <tr>
                            <td>
                                <label>{t('solutions.sol_name_label')}</label>
                            </td>
                            <td>
                            <input id="solution_name" {...register('solution_name',{required: true})}
                            type="text"
                            defaultValue= {solution_name}
                            placeholder={t('solutions.sol_name_placeholder')}
                            onChange={(e)=>setSolutionName(e.target.value)}
                            />
                            </td>
                            <td>
                                <label>{t('solutions.ticker_label')}</label>
                            </td>
                            <td>
                            <select {...register("ticker")} 
                                value={ticker}
                                onChange={(e)=>setTicker(e.target.value)}
                            >
                            {props.tickers.map((option_item) => (
                            <option value={option_item['ticker']}>
                                {option_item['ticker']}
                            </option>
                            ))}
                            </select>
                            </td>    
                        </tr>
                        <tr>
                        <td>
                            <label>{t('solutions.model_label')}</label>
                            </td>
                            <td>
                            <select {...register("model_id")}
                            value={modelId}
                            onChange={(e) => setModelId(e.target.value)}>
                            {props.models.map((model) => (
                            <option value={model['id']}>
                                {model['model_name']}
                            </option>
                            ))}
                            </select>
                            </td>
                        </tr>
                    </table>
                                                        
                    <button type="submit" className="btn btn-primary">{t('solutions.save_btn')}</button>
                </form>
            </div>
        </div>
    </>
    )

}
export default GeneralSollutionInfo;