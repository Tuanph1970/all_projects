"""
Inference module for Vietnamese Grade 12 Math Tutor.

Provides simple (non-agent) inference using the fine-tuned model.
"""

import torch
from typing import Dict, Any, Optional, List, Generator
from pathlib import Path
from dataclasses import dataclass

import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import get_config, Config
from training.model_config import load_model_and_tokenizer, load_trained_model
from utils.logger import get_logger

logger = get_logger("inference")


@dataclass
class GenerationConfig:
    """Configuration for text generation."""
    max_new_tokens: int = 1024
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    repetition_penalty: float = 1.1
    do_sample: bool = True
    num_beams: int = 1
    early_stopping: bool = False


class MathTutorInference:
    """
    Simple inference class for the Math Tutor model.

    Provides direct model inference without agent orchestration.
    """

    # System prompt for simple inference
    SYSTEM_PROMPT_VI = """Bạn là một gia sư toán học chuyên nghiệp cho học sinh lớp 12 Việt Nam.
Hãy giải bài toán sau một cách chi tiết, từng bước một.
Giải thích rõ ràng và dễ hiểu."""

    SYSTEM_PROMPT_EN = """You are a professional math tutor for Vietnamese Grade 12 students.
Solve the following problem step by step.
Explain clearly and make it easy to understand."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        config: Optional[Config] = None,
        device: Optional[str] = None,
        quantization: bool = True,
        language: str = "vi",
    ):
        """
        Initialize the inference engine.

        Args:
            model_path: Path to trained model (uses base model if None)
            config: Configuration object
            device: Device to use (cuda/cpu)
            quantization: Whether to use quantization
            language: Output language ("vi" or "en")
        """
        self.config = config or get_config()
        self.language = language
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        logger.info(f"Initializing inference on device: {self.device}")

        # Load model
        if model_path:
            logger.info(f"Loading trained model from: {model_path}")
            self.model, self.tokenizer = load_trained_model(
                Path(model_path),
                config=self.config,
                quantization=quantization,
            )
        else:
            logger.info("Loading base model")
            self.model, self.tokenizer = load_model_and_tokenizer(
                config=self.config,
                quantization=quantization,
                for_training=False,
            )

        self.model.eval()
        logger.info("Model loaded and ready for inference")

        # Default generation config
        self.gen_config = GenerationConfig()

    def _build_prompt(
        self,
        question: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Build the full prompt for the model.

        Args:
            question: User's question
            system_prompt: Custom system prompt
            history: Conversation history

        Returns:
            Formatted prompt string
        """
        if system_prompt is None:
            system_prompt = self.SYSTEM_PROMPT_VI if self.language == "vi" else self.SYSTEM_PROMPT_EN

        # Try using chat template if available
        if hasattr(self.tokenizer, "apply_chat_template"):
            messages = []

            # Add system message
            messages.append({"role": "system", "content": system_prompt})

            # Add history
            if history:
                for msg in history:
                    messages.append(msg)

            # Add current question
            messages.append({"role": "user", "content": question})

            try:
                prompt = self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
                return prompt
            except:
                pass  # Fall back to simple format

        # Simple format fallback
        prompt = f"### System:\n{system_prompt}\n\n"

        if history:
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    prompt += f"### Question:\n{content}\n\n"
                else:
                    prompt += f"### Answer:\n{content}\n\n"

        prompt += f"### Question:\n{question}\n\n### Answer:\n"

        return prompt

    @torch.inference_mode()
    def generate(
        self,
        question: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        gen_config: Optional[GenerationConfig] = None,
    ) -> str:
        """
        Generate a response to a math question.

        Args:
            question: The math question
            system_prompt: Custom system prompt
            history: Conversation history
            gen_config: Generation configuration

        Returns:
            Generated response
        """
        config = gen_config or self.gen_config

        # Build prompt
        prompt = self._build_prompt(question, system_prompt, history)

        logger.debug(f"Prompt length: {len(prompt)} chars")

        # Tokenize
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=4096 - config.max_new_tokens,
        ).to(self.device)

        # Generate
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=config.max_new_tokens,
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=config.top_k,
            repetition_penalty=config.repetition_penalty,
            do_sample=config.do_sample,
            num_beams=config.num_beams,
            early_stopping=config.early_stopping,
            pad_token_id=self.tokenizer.pad_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
        )

        # Decode
        full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Extract just the generated part
        if full_response.startswith(prompt):
            response = full_response[len(prompt):].strip()
        else:
            # Try to find the answer section
            if "### Answer:" in full_response:
                response = full_response.split("### Answer:")[-1].strip()
            elif "assistant" in full_response.lower():
                parts = full_response.split("assistant")
                response = parts[-1].strip() if len(parts) > 1 else full_response
            else:
                response = full_response

        # Clean up response
        response = self._clean_response(response)

        return response

    def _clean_response(self, response: str) -> str:
        """Clean up the generated response."""
        # Remove trailing special tokens
        stop_tokens = ["###", "<|", "[/", "</s>", "<|im_end|>", "<|endoftext|>"]
        for token in stop_tokens:
            if token in response:
                response = response.split(token)[0]

        return response.strip()

    @torch.inference_mode()
    def generate_stream(
        self,
        question: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        gen_config: Optional[GenerationConfig] = None,
    ) -> Generator[str, None, None]:
        """
        Generate a response with streaming output.

        Args:
            question: The math question
            system_prompt: Custom system prompt
            history: Conversation history
            gen_config: Generation configuration

        Yields:
            Generated text tokens
        """
        config = gen_config or self.gen_config

        # Build prompt
        prompt = self._build_prompt(question, system_prompt, history)

        # Tokenize
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=4096 - config.max_new_tokens,
        ).to(self.device)

        # Stream generation using generate with streamer
        from transformers import TextIteratorStreamer
        from threading import Thread

        streamer = TextIteratorStreamer(
            self.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
        )

        generation_kwargs = dict(
            **inputs,
            max_new_tokens=config.max_new_tokens,
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=config.top_k,
            repetition_penalty=config.repetition_penalty,
            do_sample=config.do_sample,
            pad_token_id=self.tokenizer.pad_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
            streamer=streamer,
        )

        # Run generation in background thread
        thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()

        # Stream output
        for text in streamer:
            yield text

        thread.join()

    def solve(
        self,
        problem: str,
        show_steps: bool = True,
    ) -> Dict[str, Any]:
        """
        Solve a math problem and return structured result.

        Args:
            problem: The math problem
            show_steps: Whether to request step-by-step solution

        Returns:
            Dictionary with solution and metadata
        """
        if show_steps:
            if self.language == "vi":
                question = f"{problem}\n\nHãy giải chi tiết từng bước."
            else:
                question = f"{problem}\n\nPlease show detailed step-by-step solution."
        else:
            question = problem

        response = self.generate(question)

        return {
            "success": True,
            "problem": problem,
            "solution": response,
            "language": self.language,
        }


def create_inference_engine(
    model_path: Optional[str] = None,
    quantization: bool = True,
    language: str = "vi",
) -> MathTutorInference:
    """
    Factory function to create inference engine.

    Args:
        model_path: Path to trained model
        quantization: Use quantization
        language: Output language

    Returns:
        MathTutorInference instance
    """
    return MathTutorInference(
        model_path=model_path,
        quantization=quantization,
        language=language,
    )


if __name__ == "__main__":
    print("=" * 60)
    print("Math Tutor Inference Test")
    print("=" * 60)

    # Note: This will fail without a GPU and model
    # Just testing the code structure
    print("\nInference module loaded successfully.")
    print("To test inference, run with a trained model:")
    print("  python chatbot/inference.py --model path/to/model")

    # Test prompt building
    class MockTokenizer:
        def __init__(self):
            self.pad_token_id = 0
            self.eos_token_id = 1

    mock = MockTokenizer()

    # Test the prompt format
    system = "You are a math tutor."
    question = "What is 2 + 2?"

    simple_prompt = f"### System:\n{system}\n\n### Question:\n{question}\n\n### Answer:\n"
    print(f"\nSample prompt format:\n{simple_prompt}")

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)
