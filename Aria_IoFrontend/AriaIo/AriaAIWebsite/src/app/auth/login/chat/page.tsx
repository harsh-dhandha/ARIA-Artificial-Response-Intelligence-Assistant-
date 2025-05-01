"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import "@/styles/globals.css"; // Import global styles
import axios from 'axios';
import { useAuth } from '@/app/context/AuthContext';

// Message type definition
interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

// Loading animation component
const LoadingAnimation = () => (
  <div className="flex space-x-2 justify-center items-center h-8">
    <div className="h-3 w-3 bg-blue-400 rounded-full animate-pulse" style={{ animationDelay: '0.1s' }}></div>
    <div className="h-3 w-3 bg-blue-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
    <div className="h-3 w-3 bg-blue-400 rounded-full animate-pulse" style={{ animationDelay: '0.3s' }}></div>
  </div>
);

export default function DocumentChatPage() {
  const router = useRouter();
  const { userEmail } = useAuth();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'system',
      content: 'Hello! I\'m your HR and organizational assistant. I can help with queries related to HR policies, IT support, and other organizational matters based on your uploaded documents. How can I assist you today?',
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [uploadedDocs, setUploadedDocs] = useState<string[]>([]);
  const [showDocsPanel, setShowDocsPanel] = useState(false);
  
  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  // Fetch the user's uploaded documents
  useEffect(() => {
    const fetchDocs = async () => {
      try {
        // This would be replaced with your actual API endpoint
        const response = await axios.get(`/api/documents?user=${userEmail}`);
        setUploadedDocs(response.data.documents || []);
      } catch (error) {
        console.error('Failed to fetch documents:', error);
        // Mock data for now
        setUploadedDocs([
          'Company HR Policy Handbook.pdf',
          'IT Support Guidelines.pdf',
          'Employee Benefits 2023.pdf'
        ]);
      }
    };
    
    if (userEmail) {
      fetchDocs();
    }
  }, [userEmail]);

  // Function to handle sending a message
  const handleSendMessage = async () => {
    if (!input.trim()) return;
    
    // Create new message
    const newUserMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date()
    };
    
    // Update state with user message
    setMessages(prev => [...prev, newUserMessage]);
    setInput('');
    setIsLoading(true);
    
    try {
      // API call to the RAG backend
      // This would be replaced with your actual API endpoint
      const response = await axios.post('/api/chat', {
        message: input,
        history: messages.map(msg => ({
          role: msg.role,
          content: msg.content
        })),
        user: userEmail
      });
      
      // Add assistant response to messages
      const assistantResponse: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.data.response || "I'm sorry, I couldn't process your request at the moment.",
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, assistantResponse]);
    } catch (error) {
      console.error('Error calling chat API:', error);
      
      // Simulated response for development
      setTimeout(() => {
        const simulatedResponses = [
          "Based on our HR policy documents, employees are entitled to 20 days of paid vacation per year, which increases by 1 day for each year of service up to a maximum of 30 days.",
          "According to the IT support guidelines, you can request hardware upgrades through the IT portal after getting approval from your department head.",
          "The employee benefits document states that health insurance coverage includes dental and vision with a $500 deductible for in-network providers.",
          "I've found in the organizational handbook that flexible working hours are available between 7 AM and 7 PM, with core hours from 10 AM to 3 PM when all employees should be available.",
          "The company's remote work policy indicates that employees can work remotely up to 3 days per week with prior approval from their manager."
        ];
        
        const randomResponse = simulatedResponses[Math.floor(Math.random() * simulatedResponses.length)];
        
        const assistantResponse: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: randomResponse,
          timestamp: new Date()
        };
        
        setMessages(prev => [...prev, assistantResponse]);
      }, 1500);
    } finally {
      setIsLoading(false);
    }
  };

  // Format timestamp for messages
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit'
    });
  };

  return (
    <div className="relative min-h-screen bg-gradient-to-b from-gray-900 to-black text-white flex flex-col">
      {/* Header */}
      <header className="bg-gray-800/50 backdrop-blur-lg border-b border-gray-700/50 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <button 
                onClick={() => router.push('/auth/login/api')}
                className="mr-4 p-2 rounded-lg hover:bg-gray-700/50 transition-colors duration-200"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
              </button>
              <span className="text-xl font-semibold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                Document Chat
              </span>
            </div>
            <div className="flex items-center space-x-2">
              <button 
                onClick={() => setShowDocsPanel(!showDocsPanel)}
                className="px-3 py-1.5 bg-gray-700/70 hover:bg-gray-600/70 rounded-lg text-sm font-medium transition-colors duration-200 flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span>Documents</span>
                <span className="bg-blue-500 text-white text-xs px-1.5 py-0.5 rounded-full">{uploadedDocs.length}</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content - Chat Interface */}
      <div className="flex flex-1 overflow-hidden">
        {/* Main Chat Area */}
        <main className="flex-1 flex flex-col p-4 relative overflow-hidden">
          {/* Messages Container */}
          <div className="flex-1 overflow-y-auto mb-4 pr-2 space-y-4 pb-2">
            {messages.map((message) => (
              <div 
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div 
                  className={`max-w-3xl px-4 py-3 rounded-2xl ${
                    message.role === 'user'
                      ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white'
                      : message.role === 'system'
                        ? 'bg-gradient-to-r from-gray-700 to-gray-800 text-white border border-gray-600'
                        : 'bg-gray-800/70 text-white border border-gray-700'
                  }`}
                >
                  <div className="whitespace-pre-wrap">{message.content}</div>
                  <div className={`text-xs mt-1 ${
                    message.role === 'user' ? 'text-blue-200' : 'text-gray-400'
                  }`}>
                    {formatTime(message.timestamp)}
                  </div>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-800/70 px-4 py-3 rounded-2xl border border-gray-700">
                  <LoadingAnimation />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="bg-gray-800/30 border border-gray-700/50 backdrop-blur-sm rounded-xl p-2 w-full">
            <div className="flex items-end">
              <textarea
                className="flex-1 bg-transparent resize-none p-2 text-white focus:outline-none placeholder-gray-400"
                placeholder="Ask about your documents..."
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
              />
              <button
                onClick={handleSendMessage}
                disabled={!input.trim() || isLoading}
                className={`ml-2 p-2 rounded-lg ${
                  !input.trim() || isLoading
                    ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                    : 'bg-gradient-to-r from-blue-500 to-purple-500 text-white hover:opacity-90'
                }`}
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </div>
            
            <div className="mt-2 px-2 flex justify-between items-center">
              <div className="text-xs text-gray-400">
                Ask questions about your uploaded documents
              </div>
              <div className="text-xs text-gray-400">
                {input.length} / 1000
              </div>
            </div>
          </div>
        </main>

        {/* Documents Side Panel */}
        <div className={`bg-gray-800/50 border-l border-gray-700/50 backdrop-blur-sm md:w-80 overflow-y-auto transition-all duration-300 ${
          showDocsPanel ? 'w-full md:translate-x-0' : 'w-0 md:-translate-x-full hidden md:block'
        }`}>
          <div className="p-4">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-white">Your Documents</h3>
              <button
                onClick={() => setShowDocsPanel(false)}
                className="p-1 rounded-lg text-gray-400 hover:text-white hover:bg-gray-700/50 md:hidden"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            {uploadedDocs.length > 0 ? (
              <div className="space-y-2">
                {uploadedDocs.map((doc, index) => (
                  <div key={index} className="bg-gray-700/50 rounded-lg p-3 flex items-start space-x-3 hover:bg-gray-700 transition-colors duration-200">
                    <div className="text-blue-400 flex-shrink-0">
                      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white font-medium truncate">{doc}</p>
                      <p className="text-xs text-gray-400 mt-1">
                        {index === 0 ? 'Uploaded on Mar 28, 2023' : index === 1 ? 'Uploaded on Apr 15, 2023' : 'Uploaded on May 3, 2023'}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <div className="inline-block p-3 bg-gray-700/50 rounded-full mb-4">
                  <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <p className="text-gray-400 mb-2">No documents found</p>
                <button 
                  onClick={() => router.push('/auth/login/api?tab=FILES')}
                  className="text-sm text-blue-400 hover:text-blue-300"
                >
                  Upload documents in the Files tab
                </button>
              </div>
            )}
            
            <div className="mt-6 border-t border-gray-700 pt-4">
              <h4 className="text-sm font-semibold text-gray-300 mb-2">Quick Prompts</h4>
              <div className="space-y-2">
                <button 
                  onClick={() => setInput('What are the company\'s HR policies regarding annual leave?')}
                  className="w-full text-left text-sm p-2 rounded-lg bg-gray-700/50 text-gray-300 hover:bg-gray-700 transition-colors duration-200"
                >
                  What are the company's HR policies regarding annual leave?
                </button>
                <button 
                  onClick={() => setInput('How do I request IT support for hardware issues?')}
                  className="w-full text-left text-sm p-2 rounded-lg bg-gray-700/50 text-gray-300 hover:bg-gray-700 transition-colors duration-200"
                >
                  How do I request IT support for hardware issues?
                </button>
                <button 
                  onClick={() => setInput('What benefits are included in our health insurance plan?')}
                  className="w-full text-left text-sm p-2 rounded-lg bg-gray-700/50 text-gray-300 hover:bg-gray-700 transition-colors duration-200"
                >
                  What benefits are included in our health insurance plan?
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 