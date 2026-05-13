import React from "react";

const ModelDetail = (props) => {
    
    const currentModel = props.models.filter(lamda=>lamda['id'] === props.solution['model_id'])[0]
    const arr = Object.entries(currentModel)
    

    return (
        <p>
          <table>
            { arr.map((item) => 
            <tr>
                <td>{item[0]} : </td>
                <td>{item[1]}  </td>
              
            </tr>)

            }
          
        </table>
        </p> 
    )
}
export default ModelDetail;