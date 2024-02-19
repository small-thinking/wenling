import os
from abc import ABC, abstractmethod
from collections import OrderedDict

import openai
import retrying
from dotenv import load_dotenv  # type: ignore
from unstructured.partition.pdf import partition_pdf

from wenling.common.utils import Logger, download_pdf


class Model(ABC):
    """
    Abstract base class for all models.
    """

    vendor_type: str

    def __init__(self, vendor_type: str):
        self.vendor_type = vendor_type
        self.logger = Logger(logger_name=os.path.basename(__file__))

    @abstractmethod
    def inference(self, *args, **kwargs):
        pass


class OpenAIChatModel(Model):
    """
    Abstract base class for all OpenAI models.
    """

    client: openai.OpenAI
    model_type: str = "gpt-3.5-turbo-0125"

    def __init__(self, *args, **kwargs):
        super().__init__(vendor_type="openai", *args, **kwargs)
        load_dotenv(override=True)
        self.client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    @retrying.retry(stop_max_attempt_number=3)
    def inference(
        self,
        user_prompt: str,
        sys_prompt: str = "You are a helpful assistant.",
        max_tokens: int = 500,
        response_format: str = "json_object",
        model_type: str = "gpt-3.5-turbo-0125",
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


def pdf_paper_summary(logger: Logger, pdf_url: str, truncate_size: int = 8000):
    try:
        # Download PDF.
        logger.info(f"Downloading PDF from {pdf_url}...")
        pdf_path = download_pdf(pdf_url)
        pdf_path = os.path.expanduser(pdf_path)
        # Parse PDF into paragraphs.
        logger.info(f"Partitioning PDF into paragraphs...")
        elements = partition_pdf(
            filename=pdf_path,
            strategy="fast",
        )

        paragraphs = OrderedDict()
        for idx, element in enumerate(elements[:50]):
            paragraphs[idx] = element.text  # Assuming `element` has a text attribute

        # Concatenate paragraphs into a single string
        text = "\n".join(paragraphs.values())[:truncate_size]
        logger.info("Start to summarize the paper...")
        openai = OpenAIChatModel()
        sys_prompt = """
            You will receive the paper text snippets (may have some noise text). 
            You are a research paper analysis service focused on determining the primary findings of the paper and analyzing its scientific quality.

            Take a deep breath and think step by step about how to best accomplish this goal using the following steps.

            OUTPUT SECTIONS in json format.
            
            Title: Extract the title of the paper.
            
            Authors: List of string includes the first 2 authors and other notable authors, each with their affiliation in parenthesis.

            Contributions: Extract the primary paper unique contribution into a bulleted list of no more than 50 words per bullet.

            If the paper is about a new algorithm, please briefly describe the core idea, and display the core formula if any.
            If the paper is about a new system proposed, briefly describe the system architecture.

            Experiment: Extract the empirical study or experiment in a section.

            If this paper is about a new method that lift the performance, you briefly summarize the notable data used,
            the baseline methods compared, and the lift of the performance.

            If the paper is a general paper, please do the following:
            ---
            Sample size
            Check the Sample Size: The larger the sample size, the more confident you can be in the findings.
            A larger sample size reduces the margin of error and increases the study's power.
            Confidence intervals
            Look at the Confidence Intervals: Confidence intervals provide a range within which the true population
            parameter lies with a certain degree of confidence (usually 95% or 99%).
            Narrower confidence intervals suggest a higher level of precision and confidence in the estimate.
            
            P-Value
            Evaluate the P-value: The P-value tells you the probability that the results occurred by chance.
            A lower P-value (typically less than 0.05) suggests that the findings are statistically
            significant and not due to random chance.
            
            Effect size
            Consider the Effect Size: Effect size tells you how much of a difference there is between groups.
            A larger effect size indicates a stronger relationship and more confidence in the findings.
            
            Study design
            Review the Study Design: Randomized controlled trials are usually considered the gold standard in research.
            If the study is observational, it may be less reliable.
            
            Consistency of results
            Check for Consistency of Results: If the results are consistent across multiple studies,
            it increases the confidence in the findings.
            
            Data analysis methods
            Examine the Data Analysis Methods: Check if the data analysis methods used are appropriate for the type of
            data and research question. Misuse of statistical methods can lead to incorrect conclusions.
            Researcher's interpretation
            Assess the Researcher's Interpretation: The researchers should interpret their results in the context of
            the study's limitations. Overstating the findings can misrepresent the confidence level.
            ---

            Conclusion:
            You output a 50 word summary of the quality of the paper and it's likelihood of being replicated in
            future work as one of three levels: High, Medium, or Low.
            You put that sentence and ratign into a section called SUMMARY.

            OUTPUT INSTRUCTIONS
            Create the output using the formatting above. And put them into a json format.
            And each blob of text should be in markdown format.
            For example:
            {{
                "title": "The title of the paper",
                "authors": "The authors of the paper",
                "summary": "The summary of the paper",
                "contributions": "The contributions of the paper",
                "experiment": "The experiment of the paper",
                "conclusion": "The conclusion of the paper"
            }}
            
        """

        summary = openai.inference(
            user_prompt=text,
            sys_prompt=sys_prompt,
            max_tokens=truncate_size,
            model_type="gpt-3.5-turbo-1106",
        )
        return summary
    finally:
        os.unlink(pdf_path)  # Clean up the temporary file
