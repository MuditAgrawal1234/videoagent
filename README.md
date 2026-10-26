# 🎥 VideoAgent – AI Video Assistant

An AI-powered video assistant that converts video and audio content into meaningful summaries, key decisions, action items, and answers to user questions. It combines speech-to-text, Large Language Models (LLMs), and Retrieval-Augmented Generation (RAG) to make long videos easier to understand.

## ✨ Features

- **Audio Extraction:** Extracts audio from video files for processing.
- **Speech-to-Text:** Converts spoken content into text transcripts.
- **AI-Powered Summarization:** Generates concise summaries of long videos and recordings.
- **Action Item Extraction:** Identifies tasks and important follow-up actions.
- **Key Decision Extraction:** Highlights important decisions discussed in the content.
- **Open Questions:** Identifies questions that remain unanswered.
- **AI Chat with Video Content:** Ask questions about processed content and receive context-based answers using RAG.
- **Interactive Web Interface:** Uses Streamlit to provide a simple interface for interacting with the application.
- **Transcript Export:** Supports exporting generated information into useful document formats, where implemented.

## 🛠️ Technologies Used

- **Python** – Core programming language
- **Streamlit** – Interactive user interface
- **Mistral AI** – Large language model for language understanding and generation
- **LangChain** – LLM integration and processing workflows
- **Speech Recognition** – Transcription of audio content
- **Embeddings & Vector Database** – Semantic search over transcript content
- **Retrieval-Augmented Generation (RAG)** – Context-aware question answering
- **FFmpeg / Audio Processing Tools** – Audio extraction and conversion, depending on the configured environment

## 📁 Project Structure

```text
videoagent/
│
├── core/
│   ├── analyzer.py
│   ├── extractor.py
│   ├── llm_utils.py
│   ├── rag_engine.py
│   ├── summarizer.py
│   ├── transcriber.py
│   └── vector_store.py
│
├── utils/
│   └── audio_processor.py
│
├── downloads/
├── vector_db/
├── app.py
├── main.py
├── Requirements.txt
├── .env
└── .gitignore
```

*Note: Some folders and files are generated locally or created when the application runs. The `.env` file contains configuration secrets and should not be uploaded to GitHub.*

## ⚙️ Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/MuditAgrawal1234/videoagent.git
cd videoagent
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r Requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root and add your Mistral AI API key using the variable name expected by your code.

```env
MISTRAL_API_KEY=your_mistral_api_key
```

Replace the placeholder with your own API key. Never share or commit real API keys.

### 5. Run the application

Start the Streamlit interface:

```bash
streamlit run app.py
```

If your project uses a different entry point, use the corresponding command.

## 🔄 How It Works

1. **Input:** Provide a supported video or audio source.
2. **Audio Processing:** Extract and prepare the audio for transcription.
3. **Transcription:** Convert speech into text.
4. **AI Analysis:** Process the transcript with an LLM to generate a title, summary, action items, decisions, and open questions.
5. **Vector Storage:** Convert transcript segments into embeddings and store them for semantic retrieval.
6. **Question Answering:** Retrieve relevant transcript segments and use them as context for answering user questions.
7. **Output:** View the generated insights and interact with the video content through the interface.

## 🎯 Use Cases

- Summarizing educational videos and lectures
- Extracting meeting minutes and action items
- Reviewing long interviews and discussions
- Finding key information in recorded presentations
- Asking questions about video and audio content

## 🚀 Future Improvements

- Support for more video and audio formats
- Improved multilingual transcription and translation
- Timestamp-based answers and transcript navigation
- Better handling of long recordings
- More export formats and improved error handling

## 👨‍💻 Author

**Mudit Agrawal**

GitHub: [MuditAgrawal1234](https://github.com/MuditAgrawal1234)

## 📄 License

No license has been specified yet. All rights are reserved by default unless a license is added to the repository.
