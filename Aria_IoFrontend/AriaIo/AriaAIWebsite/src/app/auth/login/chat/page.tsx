"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import "@/styles/globals.css"; // Import global styles

export default function DocumentChatPage() {
  const router = useRouter();
  
  return (
    <div className="relative min-h-screen bg-gradient-to-b from-gray-900 to-black text-white flex flex-col">
      {/* Header */}
      <header className="bg-gray-800/50 backdrop-blur-lg border-b border-gray-700/50 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <button 
                onClick={() => router.back()}
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
          </div>
        </div>
      </header>

      {/* Main Content - Placeholder */}
      <main className="flex-1 flex items-center justify-center p-8">
        <div className="max-w-2xl w-full bg-gray-800/40 border border-gray-700/50 rounded-xl p-8 backdrop-blur-sm">
          <h1 className="text-2xl font-bold text-center mb-6 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            Document Chat Interface
          </h1>
          <p className="text-gray-300 text-center mb-8">
            This page will be implemented in the future to provide interactive chat with your uploaded documents.
          </p>
          <div className="flex justify-center">
            <button
              onClick={() => router.back()}
              className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg shadow-lg hover:shadow-blue-500/20 transition transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 flex items-center gap-2"
            >
              <span>Return to Dashboard</span>
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </button>
          </div>
        </div>
      </main>
    </div>
  );
} 