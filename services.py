from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import SystemMessage, HumanMessage
from langchain.memory import ConversationBufferMemory
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("AI_API_KEY")

# Initialize model
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    verbose=True,
    temperature=0.7,
    google_api_key=api_key,
    streaming=True,
)

# System instructions
system_message = """
You are a helpful agent that creates quizzes.

Rules:
- Always include a **Category** line at the start that best describes the topic (e.g., Science, History, Geography, Sports, Literature, etc.).
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
Category: <category>

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
    category: str = "General",
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
        f"Category: {category}\n"
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

def check_short_answer(user_answer: str, correct_answer: str) -> bool:
    system_message = """
    You are a helpful assistant that checks short answers.
    - Compare the user's answer with the correct answer.
    - Be lenient with minor spelling mistakes or synonyms.
    - Return True if the answer is correct, otherwise return False.
    """
    messages = [
        SystemMessage(content=system_message),
        HumanMessage(content=f"User's answer: {user_answer}\nCorrect answer: {correct_answer}\nIs the user's answer correct?"),
    ]
    response = llm.invoke(messages)
    return response.content.strip().lower() == "true"

def check_multiple_choice(user_answer: str, correct_answer: str) -> bool:
    system_message = """
    You are a helpful assistant that checks MCQS answers.
    - Compare the user's answer with the correct answer.
    - Be lenient with minor spelling mistakes or synonyms.
    - Return True if the answer is correct, otherwise return False.
    """
    messages = [
        SystemMessage(content=system_message),
        HumanMessage(content=f"User's answer: {user_answer}\nCorrect answer: {correct_answer}\nIs the user's answer correct?"),
    ]
    response = llm.invoke(messages)
    return response.content.strip().lower() == "true"

# def assistant(query: str) -> str:
#     """
#     General-purpose AI model function to handle various queries.
#     """
#     messages = [
#         SystemMessage(content="You are a helpful assistant. that guide about the app and answer general question about studies and tell about the features of the app how the app is working name of the app is quiz hippo and it is a educational purpose app in this app student can enroll itself and make quiz on any topic due to ai powers student can generate quiz by a prompt or by giving a pdf file or a url or text it is very simple t use only some steps required give the context tell about the difficulty question types t/f short question ans choose ans fill in the blanks or mix and give the language in which you want the quiz and how many questions you want and then click on generate quiz and your quiz is ready also student can share the quiz with other student and teacher can also share the quiz with student and student can attempt the quiz and see their results and performance and can also see the correct answers of the question it is very helpful app for students to learn new things and test their knowledge this app is only for educational purpose and the ai name is professor hippo which guide about the app and answer general question about studies"),
#         HumanMessage(content=query),
#     ]
#     response = llm.invoke(messages)
#     return response.content

# Global message history to act as memory

message_history = [
    {
        "role": "system",
        "content": (
            "You are a helpful assistant that guides about the app and answers general questions "
            "about studies. The app name is Quiz Hippo. It is an educational app where students "
            "can enroll, create quizzes on any topic via AI (using prompt, PDF, URL, or text). "
            "Students can set difficulty, question types (T/F, short answer, multiple choice, fill in the blanks, or mixed), language, and number of questions. "
            "Click 'generate quiz' and the quiz is ready. Quizzes can be shared with other students or teachers. "
            "Students can attempt quizzes, view results, performance, and correct answers. "
            "The AI name is Professor Hippo, who guides the user about the app. This app is for educational purposes only."
        )
    }
]

def assistant(query: str) -> str:
    """
    General-purpose AI model function with memory buffer for Gemini 2.0 Flash.
    """
    global message_history

    # Add the user's message to history
    message_history.append({"role": "user", "content": query})

    # Call Gemini LLM with the full history
    response = llm.invoke(message_history)  # assuming llm.invoke works with a list of messages

    # Add AI's response to history
    message_history.append({"role": "assistant", "content": response.content})

    return response.content

