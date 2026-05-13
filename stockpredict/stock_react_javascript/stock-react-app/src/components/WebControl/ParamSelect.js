import React from "react";
import { useEffect,useState } from "react";
import { useForm } from "react-hook-form"
const ParamSelect = (props) =>{
    
    const [optionItems,setOptionItems] = useState([])
    // eslint-disable-next-line no-unused-vars -- react-hook-form returns several bindings we don't use yet
    const { register,handleSubmit,reset,formState: { errors },watch} = useForm();
    function getOptions(){
        let items = props.data['options'].split(',')        
        setOptionItems(items)        
    }
    useEffect(() => {
        getOptions()

    // eslint-disable-next-line react-hooks/exhaustive-deps
    },[])

    return (
        
            <dl className="mb-3">
                <dt><label>{props.data['param_name']}</label></dt>
                <dd>
                <select {...register(props.data['param_name'])}
                 selectedValue = {props.selectedValue}
                  >
                            {optionItems.map((option_item) => (
                            <option value={option_item}>
                                {option_item}
                            </option>
                            ))}
                        </select>
                </dd>   
            </dl>
    )

}
export default ParamSelect