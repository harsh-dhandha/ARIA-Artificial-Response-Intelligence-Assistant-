# ARIA - Artificial Response Intelligence Assistant

ARIA (Artificial Response Intelligence Assistant) is an advanced voice-enabled chatbot designed to enhance organizational efficiency by providing accurate and helpful information to employees. Built using cutting-edge technologies, ARIA leverages Google Gemini for natural language processing and utilizes voice synthesis through Cartesia, ensuring a seamless and engaging user experience.

## Features

- **Voice Interaction:** Engage with users through natural voice responses, making interactions intuitive and fluid.
- **HR Policies and IT Support:** Provide comprehensive information regarding HR policies, IT support, and organizational logistics.
- **Document Processing:** Analyze and extract relevant information from uploaded documents, summarizing key points for users.
- **Bad Language Filtering:** Implement filters to ensure professional and respectful communication.
- **Two-Factor Authentication:** Enhance security with email-based two-factor authentication.

## Technologies Used

- **Frontend:** Built using Next.js for a responsive and modern user interface.
- **Backend:** Python 3.9-3.12, utilizing LiveKit for real-time communication and voice processing.
- **Voice Synthesis:** Cartesia for generating lifelike voice responses.
- **Natural Language Processing:** Google Gemini for advanced language understanding and response generation.
- **Speech-to-Text Conversion:** Deepgram for accurate voice recognition and transcription.

## Setup Instructions

### Prerequisites

- Node.js
- Python 3.9-3.12
- LiveKit Cloud account (or OSS LiveKit server)
- Cartesia API key (for speech synthesis)
- Google API key (for LLM)
- Deepgram API key (for speech-to-text)

### Frontend Setup

1. Copy `.env.example` to `.env.local` and set the environment variables.
2. Install dependencies and run the development server:

   ```bash
   cd frontend
   npm install
   npm run dev

### Agent Setup

- Copy .env.example to .env and set the environment variables.

#### Create a virtual environment and activate it:

- Copy 
   ```bash
   cd agent
  python3 -m venv venv
  source venv/bin/activate

#### Install the required Python packages:

- Copy -
   ```bash
   pip install -r requirements.txt

-Run the agent:

- Copy - 
   ```bash
   python main.py dev

- Contributing

  ->Contributions are welcome! If you'd like to improve ARIA, please fork the repository and submit a pull request.

#### License
This project is licensed under the MIT License. See the LICENSE file for details.
#### Contact
For any inquiries or support, please reach out to the project maintainers.