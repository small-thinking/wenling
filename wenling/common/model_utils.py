import os
from abc import ABC, abstractmethod

import openai
import retrying

from wenling.common.utils import Logger, load_env


class Model(ABC):
    """
    Abstract base class for all models.
    """

    vendor_type: str

    def __init__(self, vendor_type: str, verbose: bool = False):
        self.vendor_type = vendor_type
        self.logger = Logger(logger_name=os.path.basename(__file__), verbose=verbose)

    @abstractmethod
    def inference(self, *args, **kwargs):
        pass


class OpenAIChatModel(Model):
    """
    Abstract base class for all OpenAI models.
    """

    client: openai.OpenAI
    model_type: str = "gpt-3.5-turbo-1106"

    def __init__(self, *args, **kwargs):
        super().__init__(vendor_type="openai", *args, **kwargs)
        load_env()
        self.client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    @retrying.retry(stop_max_attempt_number=3)
    def inference(
        self,
        user_prompt: str,
        sys_prompt: str = "You are a helpful assistant.",
        max_tokens: int = 500,
        response_format: str = "json_object",
        model_type: str = "gpt-3.5-turbo-1106",
        temperature: float = 0.0,
    ) -> str:
        """
        Generate text completion.
        """
        try:
            response = self.client.chat.completions.create(  # type: ignore
                model=model_type,
                messages=[
                    {
                        "role": "system",
                        "content": sys_prompt,
                    },
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=min(4000, max_tokens),
                response_format={"type": response_format},
                temperature=temperature,
            )
        except Exception as e:
            self.logger.error(f"Got the error: {str(e)}")
            response = None
        # refactor the below line by checking the response.choices[0].message.content step by step, and handle the error.
        if not response or not response.choices or len(response.choices) == 0:
            raise Exception(f"Failed to parse choices from openai.ChatCompletion response. The response: {response}")
        first_choice = response.choices[0]
        if not first_choice.message:
            raise Exception(
                f"Failed to parse message from openai.ChatCompletion response. The choices block: {first_choice}"
            )
        message = first_choice.message
        if not message.content:
            raise Exception(f"Failed to parse content openai.ChatCompletion response. The message block: {message}")
        result = message.content
        return result
