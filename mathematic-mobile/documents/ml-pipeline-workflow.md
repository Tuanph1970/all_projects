# ML Pipeline Workflow - Python ML Service

## Overview

The Python ML Service handles all machine learning operations including OCR, problem classification, solution generation, and model training. It operates independently from the .NET API service and communicates via HTTP REST APIs and message queues.

## ML Service Architecture

```python
homework-solver-ml/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py         # Environment configuration
│   │   └── logging_config.py   # Structured logging setup
│   ├── api/
│   │   ├── __init__.py
│   │   ├── ocr.py             # OCR endpoints
│   │   ├── solution.py        # Solution generation endpoints
│   │   ├── training.py        # Model training endpoints
│   │   ├── models.py          # Model management endpoints
│   │   └── health.py          # Health check endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ocr_service.py     # OCR processing logic
│   │   ├── llm_service.py     # LLM inference logic
│   │   ├── moe_service.py     # Mixture of Experts routing
│   │   ├── training_service.py # Model training and fine-tuning
│   │   ├── cache_service.py   # Redis caching service
│   │   └── queue_service.py   # RabbitMQ message handling
│   ├── models/
│   │   ├── __init__.py
│   │   ├── problem_classifier.py
│   │   ├── algebra_expert.py
│   │   ├── calculus_expert.py
│   │   ├── geometry_expert.py
│   │   └── base_expert.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── image_processing.py
│   │   ├── text_preprocessing.py
│   │   ├── validation.py
│   │   └── metrics.py
│   └── schemas/
│       ├── __init__.py
│       ├── ocr_schemas.py
│       ├── solution_schemas.py
│       └── training_schemas.py
```

## OCR Pipeline Workflow

### Multi-Engine OCR Processing

```python
# OCR Service Implementation
from typing import List, Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
import easyocr
import pytesseract
from mathpix import MathpixAPI

class OCRService:
    def __init__(self):
        self.easyocr_reader = easyocr.Reader(['en'])
        self.mathpix_api = MathpixAPI()
        self.executor = ThreadPoolExecutor(max_workers=3)
    
    async def extract_text_multi_engine(self, image_path: str) -> Dict[str, Any]:
        """Extract text using multiple OCR engines in parallel"""
        
        # Run all OCR engines in parallel
        tasks = [
            asyncio.get_event_loop().run_in_executor(
                self.executor, self._run_easyocr, image_path
            ),
            asyncio.get_event_loop().run_in_executor(
                self.executor, self._run_tesseract, image_path
            ),
            asyncio.get_event_loop().run_in_executor(
                self.executor, self._run_mathpix, image_path
            )
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine and validate results
        combined_result = self._combine_ocr_results(results)
        
        return {
            'text': combined_result['text'],
            'confidence': combined_result['confidence'],
            'math_expressions': combined_result['math_expressions'],
            'metadata': {
                'engines_used': combined_result['engines_used'],
                'processing_time': combined_result['processing_time'],
                'image_quality_score': self._assess_image_quality(image_path)
            }
        }
    
    def _run_easyocr(self, image_path: str) -> Dict[str, Any]:
        """EasyOCR processing for general text recognition"""
        results = self.easyocr_reader.readtext(image_path)
        
        text_parts = []
        confidences = []
        
        for (bbox, text, conf) in results:
            if conf > 0.5:  # Filter low confidence results
                text_parts.append(text)
                confidences.append(conf)
        
        return {
            'engine': 'easyocr',
            'text': ' '.join(text_parts),
            'confidence': sum(confidences) / len(confidences) if confidences else 0,
            'raw_results': results
        }
    
    def _run_tesseract(self, image_path: str) -> Dict[str, Any]:
        """Tesseract OCR for printed text recognition"""
        # Configure Tesseract for mathematical text
        config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789+-*/=()[]{}ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
        
        text = pytesseract.image_to_string(image_path, config=config)
        confidence_data = pytesseract.image_to_data(image_path, output_type=pytesseract.Output.DICT)
        
        # Calculate average confidence
        confidences = [int(conf) for conf in confidence_data['conf'] if int(conf) > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            'engine': 'tesseract',
            'text': text.strip(),
            'confidence': avg_confidence / 100,  # Normalize to 0-1 scale
            'word_confidences': confidences
        }
    
    def _run_mathpix(self, image_path: str) -> Dict[str, Any]:
        """Mathpix OCR specifically for mathematical expressions"""
        try:
            result = self.mathpix_api.latex({
                'src': image_path,
                'formats': ['text', 'latex_simplified'],
                'data_options': {'include_asciimath': True}
            })
            
            return {
                'engine': 'mathpix',
                'text': result.get('text', ''),
                'latex': result.get('latex_simplified', ''),
                'confidence': result.get('confidence', 0),
                'math_expressions': result.get('math_expressions', [])
            }
        except Exception as e:
            return {
                'engine': 'mathpix',
                'text': '',
                'confidence': 0,
                'error': str(e)
            }
```

### OCR Result Fusion

```python
def _combine_ocr_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Intelligent fusion of multiple OCR engine results"""
    
    valid_results = [r for r in results if not isinstance(r, Exception) and r.get('confidence', 0) > 0.3]
    
    if not valid_results:
        return {'text': '', 'confidence': 0, 'math_expressions': [], 'engines_used': []}
    
    # Weight results by confidence and engine reliability
    engine_weights = {'mathpix': 1.0, 'easyocr': 0.8, 'tesseract': 0.6}
    
    weighted_texts = []
    total_weight = 0
    
    for result in valid_results:
        engine = result.get('engine', 'unknown')
        confidence = result.get('confidence', 0)
        weight = engine_weights.get(engine, 0.5) * confidence
        
        if weight > 0:
            weighted_texts.append({
                'text': result.get('text', ''),
                'weight': weight,
                'engine': engine
            })
            total_weight += weight
    
    # Select best result or combine if appropriate
    if weighted_texts:
        best_result = max(weighted_texts, key=lambda x: x['weight'])
        
        # Use mathematical expressions from Mathpix if available
        math_expressions = []
        for result in valid_results:
            if result.get('engine') == 'mathpix' and result.get('math_expressions'):
                math_expressions = result['math_expressions']
                break
        
        return {
            'text': best_result['text'],
            'confidence': best_result['weight'] / engine_weights.get(best_result['engine'], 1.0),
            'math_expressions': math_expressions,
            'engines_used': [r['engine'] for r in weighted_texts],
            'processing_time': 0  # Calculate actual processing time
        }
    
    return {'text': '', 'confidence': 0, 'math_expressions': [], 'engines_used': []}
```

## Problem Classification Pipeline

### Intelligent Problem Type Detection

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

class ProblemClassifier:
    def __init__(self):
        self.model_name = "microsoft/DialoGPT-small"  # Replace with custom trained model
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        
        # Problem type mapping
        self.problem_types = {
            0: 'algebra',
            1: 'calculus',
            2: 'geometry',
            3: 'trigonometry',
            4: 'statistics',
            5: 'linear_algebra',
            6: 'differential_equations',
            7: 'number_theory'
        }
    
    def classify_problem(self, problem_text: str) -> Dict[str, Any]:
        """Classify mathematical problem into categories"""
        
        # Preprocess text
        cleaned_text = self._preprocess_text(problem_text)
        
        # Tokenize
        inputs = self.tokenizer(
            cleaned_text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=512
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Get predictions
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
            
        # Get top predictions
        top_predictions = torch.topk(predictions, k=3)
        
        results = []
        for i, (confidence, class_id) in enumerate(zip(top_predictions.values[0], top_predictions.indices[0])):
            results.append({
                'problem_type': self.problem_types[class_id.item()],
                'confidence': confidence.item(),
                'rank': i + 1
            })
        
        # Rule-based classification as fallback
        rule_based_type = self._rule_based_classification(problem_text)
        
        return {
            'primary_type': results[0]['problem_type'],
            'confidence': results[0]['confidence'],
            'all_predictions': results,
            'rule_based_type': rule_based_type,
            'features_detected': self._extract_features(problem_text)
        }
    
    def _preprocess_text(self, text: str) -> str:
        """Clean and normalize problem text"""
        import re
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Normalize mathematical symbols
        replacements = {
            '×': '*',
            '÷': '/',
            '±': '+/-',
            '≤': '<=',
            '≥': '>=',
            '≠': '!=',
            '√': 'sqrt'
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text.strip()
    
    def _rule_based_classification(self, text: str) -> str:
        """Fallback rule-based classification"""
        text_lower = text.lower()
        
        # Keyword-based classification
        if any(word in text_lower for word in ['derivative', 'integral', 'limit', 'dx', 'dy']):
            return 'calculus'
        elif any(word in text_lower for word in ['triangle', 'circle', 'angle', 'polygon', 'area', 'perimeter']):
            return 'geometry'
        elif any(word in text_lower for word in ['sin', 'cos', 'tan', 'theta', 'radians', 'degrees']):
            return 'trigonometry'
        elif any(word in text_lower for word in ['matrix', 'vector', 'eigenvalue', 'determinant']):
            return 'linear_algebra'
        elif any(word in text_lower for word in ['probability', 'statistics', 'mean', 'median', 'standard deviation']):
            return 'statistics'
        else:
            return 'algebra'  # Default
```

## Mixture of Experts (MoE) System

### Expert Model Router

```python
from abc import ABC, abstractmethod
import logging

class BaseExpert(ABC):
    """Base class for all expert models"""
    
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        self.load_model()
    
    @abstractmethod
    def load_model(self):
        """Load the expert model"""
        pass
    
    @abstractmethod
    def solve_problem(self, problem_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate solution for the given problem"""
        pass

class AlgebraExpert(BaseExpert):
    """Expert model specialized in algebra problems"""
    
    def load_model(self):
        from transformers import AutoTokenizer, AutoModelForCausalLM
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.model = AutoModelForCausalLM.from_pretrained(self.model_path)
        
        if torch.cuda.is_available():
            self.model = self.model.cuda()
    
    def solve_problem(self, problem_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Solve algebra problem with step-by-step solution"""
        
        # Create prompt for algebra problem
        prompt = self._create_algebra_prompt(problem_text, context)
        
        # Generate solution
        inputs = self.tokenizer(prompt, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=1024,
                temperature=0.7,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        solution = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        solution = solution.replace(prompt, "").strip()
        
        # Parse solution into steps
        steps = self._parse_solution_steps(solution)
        
        return {
            'expert_type': 'algebra',
            'solution': solution,
            'steps': steps,
            'confidence': self._calculate_confidence(solution, problem_text),
            'validation': self._validate_algebra_solution(steps)
        }
    
    def _create_algebra_prompt(self, problem_text: str, context: Dict[str, Any]) -> str:
        """Create specialized prompt for algebra problems"""
        return f"""
Solve this algebra problem step by step:

Problem: {problem_text}

Solution:
Step 1: Identify what we need to find
Step 2: Set up the equation
Step 3: Solve the equation
Step 4: Verify the answer

Let me solve this step by step:
"""

class MoERouter:
    """Mixture of Experts routing system"""
    
    def __init__(self):
        self.experts = {}
        self.classifier = ProblemClassifier()
        self.load_experts()
    
    def load_experts(self):
        """Load all expert models"""
        expert_configs = {
            'algebra': {'model_path': 'models/algebra-expert'},
            'calculus': {'model_path': 'models/calculus-expert'},
            'geometry': {'model_path': 'models/geometry-expert'},
            'statistics': {'model_path': 'models/statistics-expert'}
        }
        
        for expert_type, config in expert_configs.items():
            try:
                if expert_type == 'algebra':
                    self.experts[expert_type] = AlgebraExpert(config['model_path'])
                elif expert_type == 'calculus':
                    self.experts[expert_type] = CalculusExpert(config['model_path'])
                # Add other experts...
                
                logging.info(f"Loaded {expert_type} expert model")
            except Exception as e:
                logging.error(f"Failed to load {expert_type} expert: {e}")
    
    def route_and_solve(self, problem_text: str, ocr_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Route problem to appropriate expert and generate solution"""
        
        # Classify problem
        classification = self.classifier.classify_problem(problem_text)
        primary_type = classification['primary_type']
        confidence = classification['confidence']
        
        # Route to expert
        if primary_type in self.experts and confidence > 0.6:
            expert = self.experts[primary_type]
            context = {
                'ocr_metadata': ocr_metadata,
                'classification': classification
            }
            
            solution = expert.solve_problem(problem_text, context)
            solution['routing_confidence'] = confidence
            
            # If confidence is low, try ensemble approach
            if solution['confidence'] < 0.7:
                ensemble_solution = self._ensemble_solve(problem_text, context)
                if ensemble_solution['confidence'] > solution['confidence']:
                    solution = ensemble_solution
            
            return solution
        else:
            # Fallback to general model
            return self._fallback_solve(problem_text, ocr_metadata)
    
    def _ensemble_solve(self, problem_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Use multiple experts and combine results"""
        
        solutions = []
        classification = context['classification']
        
        # Get solutions from top 2 predicted types
        for prediction in classification['all_predictions'][:2]:
            expert_type = prediction['problem_type']
            if expert_type in self.experts:
                try:
                    solution = self.experts[expert_type].solve_problem(problem_text, context)
                    solution['expert_weight'] = prediction['confidence']
                    solutions.append(solution)
                except Exception as e:
                    logging.error(f"Expert {expert_type} failed: {e}")
        
        if solutions:
            # Select best solution based on confidence and expert weight
            best_solution = max(solutions, key=lambda s: s['confidence'] * s['expert_weight'])
            best_solution['ensemble_used'] = True
            return best_solution
        
        return self._fallback_solve(problem_text, context['ocr_metadata'])
```

## Solution Generation Pipeline

### Step-by-Step Solution Generation

```python
class SolutionGenerator:
    """Main solution generation orchestrator"""
    
    def __init__(self):
        self.ocr_service = OCRService()
        self.moe_router = MoERouter()
        self.cache_service = CacheService()
        self.validator = SolutionValidator()
    
    async def generate_complete_solution(self, image_data: bytes, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Complete pipeline from image to solution"""
        
        start_time = time.time()
        
        # Step 1: OCR Processing
        ocr_result = await self._process_ocr(image_data)
        if ocr_result['confidence'] < 0.5:
            return {
                'success': False,
                'error': 'OCR confidence too low',
                'ocr_result': ocr_result
            }
        
        # Step 2: Problem Classification and Routing
        solution_result = self.moe_router.route_and_solve(
            ocr_result['text'], 
            ocr_result['metadata']
        )
        
        # Step 3: Solution Validation
        validation_result = self.validator.validate_solution(
            ocr_result['text'], 
            solution_result
        )
        
        # Step 4: Generate final response
        final_solution = {
            'success': True,
            'problem_text': ocr_result['text'],
            'solution': solution_result['solution'],
            'steps': solution_result['steps'],
            'confidence': min(ocr_result['confidence'], solution_result['confidence']),
            'expert_used': solution_result['expert_type'],
            'validation': validation_result,
            'metadata': {
                'processing_time': time.time() - start_time,
                'ocr_engines': ocr_result['metadata']['engines_used'],
                'image_quality': ocr_result['metadata']['image_quality_score']
            }
        }
        
        # Step 5: Cache result
        await self.cache_service.cache_solution(final_solution)
        
        return final_solution
    
    async def _process_ocr(self, image_data: bytes) -> Dict[str, Any]:
        """Process OCR with caching"""
        
        # Generate cache key from image hash
        import hashlib
        image_hash = hashlib.md5(image_data).hexdigest()
        cache_key = f"ocr:{image_hash}"
        
        # Check cache first
        cached_result = await self.cache_service.get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        # Process OCR
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            temp_file.write(image_data)
            temp_path = temp_file.name
        
        try:
            ocr_result = await self.ocr_service.extract_text_multi_engine(temp_path)
            await self.cache_service.cache_result(cache_key, ocr_result, ttl=3600)
            return ocr_result
        finally:
            os.unlink(temp_path)
```

## Model Training & Fine-tuning Pipeline

### Continuous Learning System

```python
class TrainingService:
    """Handle model training and fine-tuning"""
    
    def __init__(self):
        self.training_data_manager = TrainingDataManager()
        self.model_manager = ModelManager()
    
    async def fine_tune_expert(self, expert_type: str, training_data: List[Dict]) -> Dict[str, Any]:
        """Fine-tune expert model with new data"""
        
        # Prepare training data
        processed_data = self._prepare_training_data(training_data, expert_type)
        
        # Load base model
        base_model_path = f"models/{expert_type}-expert"
        model = self.model_manager.load_model(base_model_path)
        
        # Configure training parameters
        training_args = {
            'output_dir': f'models/{expert_type}-expert-finetuned',
            'num_train_epochs': 3,
            'per_device_train_batch_size': 4,
            'learning_rate': 5e-5,
            'warmup_steps': 100,
            'logging_steps': 10,
            'save_strategy': 'epoch',
            'evaluation_strategy': 'epoch'
        }
        
        # Start training
        trainer = self._create_trainer(model, processed_data, training_args)
        train_result = trainer.train()
        
        # Evaluate model
        eval_result = trainer.evaluate()
        
        # Save fine-tuned model
        trainer.save_model()
        
        return {
            'expert_type': expert_type,
            'training_complete': True,
            'train_loss': train_result.training_loss,
            'eval_loss': eval_result['eval_loss'],
            'model_path': training_args['output_dir'],
            'training_samples': len(training_data)
        }
    
    def collect_feedback_data(self, problem_text: str, generated_solution: str, 
                             user_feedback: Dict[str, Any]) -> None:
        """Collect user feedback for model improvement"""
        
        feedback_data = {
            'problem_text': problem_text,
            'generated_solution': generated_solution,
            'user_rating': user_feedback.get('rating', 0),
            'corrections': user_feedback.get('corrections', []),
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_feedback.get('user_id')
        }
        
        # Store for future training
        self.training_data_manager.add_feedback(feedback_data)
        
        # Trigger retraining if enough new data collected
        if self.training_data_manager.should_retrain():
            asyncio.create_task(self._schedule_retraining())
```

## Performance Monitoring & Optimization

### Real-time Metrics Collection

```python
import time
import psutil
from prometheus_client import Counter, Histogram, Gauge

# Metrics
ocr_requests_total = Counter('ocr_requests_total', 'Total OCR requests')
ocr_processing_time = Histogram('ocr_processing_seconds', 'OCR processing time')
solution_generation_time = Histogram('solution_generation_seconds', 'Solution generation time')
model_memory_usage = Gauge('model_memory_usage_bytes', 'Model memory usage')

class MetricsCollector:
    def __init__(self):
        self.gpu_available = torch.cuda.is_available()
    
    def record_ocr_metrics(self, processing_time: float, confidence: float):
        """Record OCR processing metrics"""
        ocr_requests_total.inc()
        ocr_processing_time.observe(processing_time)
    
    def record_solution_metrics(self, processing_time: float, expert_type: str, confidence: float):
        """Record solution generation metrics"""
        solution_generation_time.labels(expert=expert_type).observe(processing_time)
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system performance metrics"""
        metrics = {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent
        }
        
        if self.gpu_available:
            metrics['gpu_memory'] = torch.cuda.memory_allocated() / 1024**3  # GB
            metrics['gpu_utilization'] = torch.cuda.utilization()
        
        return metrics
```

## Error Handling & Recovery

### Comprehensive Error Management

```python
from enum import Enum
import traceback

class ErrorType(Enum):
    OCR_ERROR = "ocr_error"
    MODEL_ERROR = "model_error"
    VALIDATION_ERROR = "validation_error"
    SYSTEM_ERROR = "system_error"

class MLServiceException(Exception):
    def __init__(self, error_type: ErrorType, message: str, details: Dict = None):
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        super().__init__(message)

class ErrorHandler:
    def __init__(self):
        self.error_counts = defaultdict(int)
        self.recovery_strategies = {
            ErrorType.OCR_ERROR: self._recover_ocr_error,
            ErrorType.MODEL_ERROR: self._recover_model_error,
            ErrorType.VALIDATION_ERROR: self._recover_validation_error
        }
    
    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle errors with appropriate recovery strategies"""
        
        if isinstance(error, MLServiceException):
            error_type = error.error_type
        else:
            error_type = ErrorType.SYSTEM_ERROR
        
        self.error_counts[error_type] += 1
        
        # Log error
        logging.error(f"ML Service Error: {error_type.value} - {str(error)}")
        
        # Attempt recovery
        if error_type in self.recovery_strategies:
            try:
                recovery_result = await self.recovery_strategies[error_type](error, context)
                if recovery_result['success']:
                    return recovery_result
            except Exception as recovery_error:
                logging.error(f"Recovery failed: {recovery_error}")
        
        # Return error response
        return {
            'success': False,
            'error_type': error_type.value,
            'error_message': str(error),
            'recovery_attempted': error_type in self.recovery_strategies,
            'context': context
        }
    
    async def _recover_ocr_error(self, error: MLServiceException, context: Dict) -> Dict:
        """Recover from OCR processing errors"""
        
        # Try alternative OCR engine
        if 'alternative_ocr' not in context:
            # Implement fallback OCR processing
            return {'success': True, 'recovery_method': 'alternative_ocr'}
        
        return {'success': False}
    
    async def _recover_model_error(self, error: MLServiceException, context: Dict) -> Dict:
        """Recover from model inference errors"""
        
        # Try reloading model
        try:
            expert_type = context.get('expert_type', 'algebra')
            # Reload model logic here
            return {'success': True, 'recovery_method': 'model_reload'}
        except Exception:
            return {'success': False}
```

## Queue Processing & Job Management

### Asynchronous Job Processing

```python
import pika
import json
from celery import Celery

# Celery configuration for background tasks
celery_app = Celery(
    'ml_service',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

class QueueProcessor:
    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters('localhost')
        )
        self.channel = self.connection.channel()
        self.setup_queues()
    
    def setup_queues(self):
        """Setup RabbitMQ queues"""
        
        # Solution processing queue
        self.channel.queue_declare(queue='solution_processing', durable=True)
        
        # Training queue
        self.channel.queue_declare(queue='model_training', durable=True)
        
        # Feedback queue
        self.channel.queue_declare(queue='feedback_processing', durable=True)
    
    def start_consuming(self):
        """Start consuming messages from queues"""
        
        self.channel.basic_consume(
            queue='solution_processing',
            on_message_callback=self.process_solution_job,
            auto_ack=False
        )
        
        self.channel.basic_consume(
            queue='model_training',
            on_message_callback=self.process_training_job,
            auto_ack=False
        )
        
        logging.info("Started consuming messages...")
        self.channel.start_consuming()
    
    def process_solution_job(self, ch, method, properties, body):
        """Process solution generation job"""
        
        try:
            job_data = json.loads(body)
            
            # Generate solution
            solution_result = asyncio.run(
                self.solution_generator.generate_complete_solution(
                    job_data['image_data'],
                    job_data['user_context']
                )
            )
            
            # Publish result back to API service
            self.publish_result('solution_complete', {
                'job_id': job_data['job_id'],
                'result': solution_result
            })
            
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            logging.error(f"Solution job failed: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

@celery_app.task
def train_model_task(expert_type: str, training_data: List[Dict]) -> Dict[str, Any]:
    """Celery task for model training"""
    
    training_service = TrainingService()
    result = asyncio.run(
        training_service.fine_tune_expert(expert_type, training_data)
    )
    
    return result

@celery_app.task
def process_feedback_task(feedback_data: Dict[str, Any]) -> None:
    """Process user feedback for model improvement"""
    
    training_service = TrainingService()
    training_service.collect_feedback_data(
        feedback_data['problem_text'],
        feedback_data['solution'],
        feedback_data['feedback']
    )
```

## Health Checks & Monitoring

### Comprehensive Health Monitoring

```python
from fastapi import FastAPI
from fastapi.responses import JSONResponse

async def health_check() -> Dict[str, Any]:
    """Comprehensive health check for ML service"""
    
    health_status = {
        'service': 'ml-service',
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'checks': {}
    }
    
    # Check OCR engines
    try:
        ocr_service = OCRService()
        health_status['checks']['ocr'] = {'status': 'healthy'}
    except Exception as e:
        health_status['checks']['ocr'] = {'status': 'unhealthy', 'error': str(e)}
        health_status['status'] = 'unhealthy'
    
    # Check ML models
    try:
        moe_router = MoERouter()
        model_count = len(moe_router.experts)
        health_status['checks']['models'] = {
            'status': 'healthy',
            'loaded_models': model_count
        }
    except Exception as e:
        health_status['checks']['models'] = {'status': 'unhealthy', 'error': str(e)}
        health_status['status'] = 'unhealthy'
    
    # Check system resources
    system_metrics = MetricsCollector().get_system_metrics()
    health_status['checks']['system'] = {
        'status': 'healthy' if system_metrics['cpu_percent'] < 80 else 'warning',
        'metrics': system_metrics
    }
    
    return health_status

# FastAPI endpoints
app = FastAPI()

@app.get("/health")
async def get_health():
    """Health check endpoint"""
    health = await health_check()
    status_code = 200 if health['status'] == 'healthy' else 503
    return JSONResponse(content=health, status_code=status_code)

@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```