import React,{useEffect,useState} from "react";
import { useTranslation } from 'react-i18next';
import { useForm } from "react-hook-form"
import httpClient from "../../../../services/httpClient";
import { API_ENDPOINTS } from "../../../../constants/api";
import { useNavigate } from "react-router-dom";
const GeneralSollutionInfo = (props) =>{
    const { t } = useTranslation();
    const navigate = useNavigate();
    const [showPastCovariate,setShowPastCovariate] = useState(false)
    const [showFutureCovariate,setShowFutureCovariate] = useState(false)
    // eslint-disable-next-line no-unused-vars -- react-hook-form returns bindings not all used yet
    const { register,handleSubmit,reset,formState: { errors },watch} = useForm();
    let sol_name = ""
    let model_id = -1
    let tick = -1
    let tar = -1
    let past_cor = []
    let future_cor = []
    if(props.solution){
        sol_name = props.solution['solution_name']
        model_id = props.solution['model_id']
        tick = props.solution['ticker']
        tar = props.solution['target']
        past_cor = props.solution['past_covariate']
        future_cor = props.solution['future_covariate']
    }
    const [solution_name, setSolutionName] = useState(sol_name)
    const [modelId,setModelId] = useState(model_id)
    const [ticker, setTicker] = useState(tick)
    const [target,setTarget] = useState(tar)
    const [selectedPastCovariateIds, setSelectedPastCovariateIds] = useState(past_cor);
    const [selectedFutureCovariateIds, setSelectedFutureCovariateIds] = useState(future_cor);
    const show_covariates = (model_id) =>{
        let models_filters = null
        if(props.solution){
            models_filters = props.models.filter(model=>model['id'] === model_id)
        }
        else {
            models_filters = props.models.filter(model => String(model['id']) === String(model_id))
        }
        console.log(models_filters)
        console.log(props.models)
        if (models_filters.length > 0){
            const past_cor = models_filters[0]['past_covariate'];
            const future_cor = models_filters[0]['future_covariate'];
            setShowPastCovariate(past_cor)
            setShowFutureCovariate(future_cor)
        }
        
    }
    
    const handleCheckboxPastCorvariateChange = (event) => {
        
        const checkedId = event.target.value;
        if(event.target.checked){
            setSelectedPastCovariateIds([...selectedPastCovariateIds,checkedId])
        }else{
            setSelectedPastCovariateIds(selectedPastCovariateIds.filter(id=>id !== checkedId))
        }
        
    }
    const handleCheckboxFutureCorvariateChange = (event) => {
        const checkedId = event.target.value;
        if(event.target.checked){
            setSelectedFutureCovariateIds([...selectedFutureCovariateIds,checkedId])
        }else{
            setSelectedFutureCovariateIds(selectedFutureCovariateIds.filter(id=>id !== checkedId))
        }
        
    }

    const formSubmit = async (data) => {                   
        data['past_covariate'] = selectedPastCovariateIds.map(Number)
        data['future_covariate'] = selectedFutureCovariateIds.map(Number) 
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
        data['target'] = parseInt(data['target'])        
        
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
    useEffect(() => {
        show_covariates(modelId)

    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);
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
                            onChange={(e) => {
                                const model_id = e.target.value;
                                setModelId(model_id);
                                show_covariates(model_id);
                            }}>
                            {props.models.map((model) => (
                            <option value={model['id']}>
                                {model['model_name']}
                            </option>
                            ))}
                            </select>
                            </td>
                            <td>
                                <label>{t('solutions.target_label')}</label>
                            </td>
                            <td>
                            <select {...register("target")} 
                            value={target}
                            onChange={(e)=>setTarget(e.target.value)}
                            >
                            {props.timeseies.map((option_item) => (
                            <option value={option_item['id']}>
                                {option_item['series_name']}
                            </option>
                            ))}
                            </select>
                            </td>
                        </tr>
                        <tr>
                            <td colSpan={2}>
                               {showPastCovariate &&
                                <fieldset>
                                <legend>{t('solutions.past_covariates')}</legend>                                
                                <table>                                    
                                {props.timeseies.map((series) => ( 
                                    <tr>
                                    <td>                                   
                                <label>    
                                <input type="checkbox" value={series['id']}
                                defaultChecked = {selectedPastCovariateIds.includes(series['id'])}
                                onChange={(event) => { handleCheckboxPastCorvariateChange(event) }}
                                />
                                {series['series_name']}
                                </label>
                                    </td>
                                </tr>
                                
                                ))
                                }                                
                                </table>
                                </fieldset>
                            } 
                            
                            </td>
                            <td colSpan={2}>
                            {showFutureCovariate &&
                            <fieldset>
                                <legend>{t('solutions.future_covariates')}</legend>                                
                                <table>                                    
                                {props.timeseies.map((series) => ( 
                                    <tr>
                                    <td>                                   
                                <label>    
                                <input type="checkbox" value={series['id']}
                                defaultChecked={selectedFutureCovariateIds.includes(series['id'])}
                                onChange={(event) => { handleCheckboxFutureCorvariateChange(event) }}
                                  />
                                {series['series_name']}
                                </label>
                                    </td>
                                </tr>
                                
                                ))
                                }                                
                                </table>
                                </fieldset>
                            }
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