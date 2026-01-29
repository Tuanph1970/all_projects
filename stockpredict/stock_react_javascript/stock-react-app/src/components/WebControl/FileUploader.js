import axios from "axios";
import { ChangeEvent,useState } from "react"
import { API_BASE_URLS } from '../../constants/api';

export default function FileUploader(props){
    const [file,setFile] = useState([]);
    const [status,setStatus] = useState("idle")
    const [uploadProgress,setUploadProgress] = useState(0);
    const handleFileChange = (e) =>{
        if(e.target.files){
            setFile(e.target.files[0]);
        }

    }
    async function handleFileUpload(){
        if(!file) return;
        props.uploadHandler();
        setStatus("uploading")
        setUploadProgress(0)
        const formData = new FormData();
        formData.append("file",file)
        // Use centralized API configuration for file service
        const api = `${API_BASE_URLS.FILE_SERVICE}/insert_file`
        try {
            await axios.post(api,formData,{
                headers: {
                    'Content-Type':'multipart/form-data',
                },
                onUploadProgress:(progressEvent) =>{
                    const progress = progressEvent.total ? 
                    Math.round((progressEvent.loaded * 100 )/progressEvent.total)
                    : 0;
                    setUploadProgress(progress)
                }
            } )
            setStatus('success')
            setUploadProgress(100)            
        } catch{
            setStatus('error')
            setUploadProgress(0)
        }




    }
    return (
        <div className="space-y-2">
            <input type = "file" onChange={e=>handleFileChange(e)}/>
            {file && (
                <div className="mb-4 text-sm">
                    <p> File name:{file.name}</p>
                </div>    
            )

            }
            {
                file && status !== "uploading" && (
                    <button onClick={handleFileUpload}>Upload</button>
                )
            }
            {status === 'success' && (
                <p className="text-sm text-green-600">
                    File uploaded successfully
                </p>
            )

            }
            {status === 'error' && (
                <p className="text-sm text-red-600">
                    upload failed. Please try again
                </p>
            )

            }
            {status ==="uploading" && (
                <div className="space-y-2">
                    <div className="h-2.5 w-full rounded-full bg-gray-200">
                        <div className="h-2.5 rounded-full bg-blue-600 transition-allduration-300" style={{width:'${uploadProgress}%'}}>
                        </div>    
                    </div>
                    <p className="text-sm text-gray-600">
                        {uploadProgress}
                    </p>    
                </div>    
            )

            }
        </div>
    )
}