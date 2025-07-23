# AI Travel Agent ✈️

An AI-powered chatbot that helps users plan their trips and itineraries using Python and Google's powerful language models.

---

## About The Project

This project is a demonstration of how large language models can be used to create a conversational travel assistant. It uses a Python backend to handle logic and API calls, and a simple web frontend for user interaction. The goal is to provide a seamless and intelligent trip-planning experience.

---

## Features

- 🤖 **Conversational AI:** Understands natural language queries for travel planning.
- 🗺️ **Custom Itineraries:** Generates travel plans based on user preferences.
- 🗣️ **Voice Capabilities:** Supports voice input and synthesizes speech for output.
- 🏨 **Suggestions:** Can provide recommendations for flights, hotels, and activities.

---

## Getting Started

Follow these steps to get a local copy up and running.

### Prerequisites

- Python 3.9+
- A Google Cloud project with the necessary APIs enabled.

### Installation

1.  **Clone the repository**
    ```sh
    git clone [https://github.com/Anshu404/ai_travel_agent.git](https://github.com/Anshu404/ai_travel_agent.git)
    ```

2.  **Navigate to the project directory**
    ```sh
    cd ai_travel_agent
    ```

3.  **Create and activate a virtual environment**
    ```sh
    python3 -m venv .venv
    source .venv/bin/activate
    ```

4.  **Install required packages**
    *(You should create a `requirements.txt` file by running `pip freeze > requirements.txt`)*
    ```sh
    pip install -r requirements.txt
    ```

5.  **Add Credentials**
    Create a `google_json_key.json` file in the root directory with your Google Cloud Service Account credentials. Remember that this file is listed in your `.gitignore` and should **never** be committed to GitHub.

---

## Usage

To run the application, execute the main backend script:

```sh
python backend/dashboard.py