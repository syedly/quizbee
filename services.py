from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import SystemMessage, HumanMessage
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("AI_API_KEY")

# Initialize model
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    verbose=True,
    temperature=0.7,
    google_api_key=api_key
)

# System instructions
system_message = """
You are a helpful agent that creates quizzes.

Rules:
- You generate quizzes when the user requests it (e.g., "make a quiz on history").
- You can create questions in the language the user specifies.
- You must generate **5 questions** unless the user specifies otherwise.
- Question types can be:
  - Short question & answer
  - True/False
  - Multiple choice questions
  - Fill in the blanks
- If the user requests a **mix**, you should include different types (some short questions, some fill-in-the-blanks, some true/false, some multiple choice questions).
- The user will specify a **difficulty level** from 1 to 5:
  - 1 = very easy
  - 2 = easy
  - 3 = medium
  - 4 = hard
  - 5 = very hard
- Adjust the complexity of the questions according to the given difficulty.
- At the end of the response, clearly list the **difficulty level of each question** (on the 1–5 scale).
- Always provide the **answers at the end** in a well-structured format.
- Do not write the whole response in one line; use proper formatting with line breaks.

Format:
Topic: <topic> (Difficulty <level>)

Questions:
1. <Question>
2. <Question>
...

Answers:
1. <Answer>
2. <Answer>

Question Difficulty Levels:
1. Q1 → Difficulty: X
2. Q2 → Difficulty: X
...
"""

def generate__quiz(
    topic: str = "General",
    language: str = "English",
    num_questions: int = 5,
    difficulty: int = 1,
    question_type: str = "mix",
    content: str = None
) -> str:
    """
    Generates a quiz using Gemini AI with flexible input.
    - topic: default topic if nothing else is given
    - content: can be user prompt, text, URL content, or file content
    - language: language of quiz
    - num_questions: how many questions
    - difficulty: 1–5 scale
    - question_type: mcq, true_false, short_answer, fill_blank, or mix
    """
    # Build the base prompt
    if content:
        base_text = content
    else:
        base_text = topic

    prompt = (
        f"Make a quiz based on the following content:\n\n"
        f"{base_text}\n\n"
        f"Language: {language}\n"
        f"Number of questions: {num_questions}\n"
        f"Difficulty level: {difficulty}\n"
        f"Question type: {question_type}\n"
    )

    # LangChain messages
    messages = [
        SystemMessage(content=system_message),
        HumanMessage(content=prompt),
    ]

    # Call Gemini
    response = llm.invoke(messages)
    return response.content

