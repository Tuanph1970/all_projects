import React, { useState,useEffect } from "react";
import axios from "axios";
import DataTable from 'react-data-table-component'
import { Button, ButtonGroup } from "react-bootstrap";
import FileUploader from "../WebControl/FileUploader";



const deleteFile = (id)=>{
  try {
    const data = {
        "id":id
    }       
    axios.post('http://127.0.0.1:3005/delete_file',data).then((res)=>console.log(res));
  } catch (error) {
 
  } finally {
   
} 

}
const processFile = (id) => {
  try {
       const data = {
           "id":id
       }       
       axios.post('http://127.0.0.1:3005/process_file',data).then((res)=>console.log(res));
  } catch (error) {
    
  } finally {
      
  }
  
  

}
const FileUploadManager = () =>{
    
    const [fileListData, setFileListData] = useState([]);
    const [isLoading,setIsLoading] = useState([])
    function refreshUpload() {
         setIsLoading(true) 
         getFileUploadList();
    }
    
    const getFileUploadList = async() =>{
      try {      
        await axios.get('http://127.0.0.1:3005/upload_files').then((res) =>{
           
           setFileListData(res.data); 
           setIsLoading(true);
        });
      } catch (error) {
        
      } finally {
          setIsLoading(false)                 
      }    
    }    
    const general_columns = [
        {
            name: 'id',
            selector: row => row.id, 
            omit: true, 
        },
        {
          name:'file_name', 
          selector:row => row.file_name, 
          sortable:true
        },
        {
            name:'file_status', 
            selector:row => row.file_status, 
            sortable:true
        },
        {
          name:'owner_id', 
          selector:row => row.owner_id, 
          sortable:true
        },
        {
          name:'action',
          width:"200px",          
          cell: (row) => (
              <div width = "200px">                
              <ButtonGroup>
                 {(row.file_status === 0) &&
                 <Button type="button" onClick={(e)=>processFile(e.target.id)} id={row.id} > Process </Button> 
                 }
                 <Button type="button" onClick={(e)=>deleteFile(e.target).id} id={row.id} > Delete </Button>
              </ButtonGroup>
              </div>
            
          ) 
      },      
    ];
    useEffect(() => {
      getFileUploadList()            
    }, []);
    return (   
            <div>           
            <table> 
                <tr>
                  <td align="right">
                    <FileUploader uploadHandler = {refreshUpload} />
                  </td>
                </tr>
                
                <tr>
                  <td>
                  {!isLoading &&   
                  <DataTable
              columns = {general_columns}
              data = {fileListData}
              defaultSortField="ticker"        
              pagination
              hightlightOnHover
              responsive
              paginationPerPage={30}
              paginationRowsPerPargeOptions = {[30,50,100]}
      
            />
            }
                  </td>
                </tr>                
            </table>
        </div>
    );
  
    

}
export default FileUploadManager