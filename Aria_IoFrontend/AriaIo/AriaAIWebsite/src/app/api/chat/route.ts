import { NextRequest, NextResponse } from 'next/server';

// This is a simple API route for the chat system
// In a real implementation, this would connect to a backend service that handles the RAG functionality

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { message, history, user } = body;

    if (!message) {
      return NextResponse.json({ error: 'Message is required' }, { status: 400 });
    }

    console.log('Received message:', message);
    console.log('User:', user);
    console.log('History length:', history?.length || 0);

    // In a real implementation, this would:
    // 1. Process the message using a RAG system (like the ones from the GitHub repos)
    // 2. Retrieve relevant document chunks based on semantic search
    // 3. Generate a response using Gemini 2.0 with context from documents
    
    // For now, we'll simulate a delayed response
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Mock responses for different query types (in a real system, these would come from the LLM)
    let response;
    const lowerMessage = message.toLowerCase();

    if (lowerMessage.includes('leave') || lowerMessage.includes('vacation') || lowerMessage.includes('holiday')) {
      response = "Based on our HR policy documents, employees are entitled to 20 days of paid vacation per year, which increases by 1 day for each year of service up to a maximum of 30 days. You need to apply for leave at least 2 weeks in advance through the HR portal. Emergency leave requests are handled on a case-by-case basis.";
    } else if (lowerMessage.includes('it') || lowerMessage.includes('hardware') || lowerMessage.includes('software')) {
      response = "According to the IT support guidelines, you can request hardware or software support by raising a ticket through the IT portal or by emailing it.support@company.com. For urgent issues, you can call the IT helpdesk at extension 4444. Hardware upgrades must be approved by your department head before being processed by IT.";
    } else if (lowerMessage.includes('health') || lowerMessage.includes('insurance') || lowerMessage.includes('medical')) {
      response = "The employee benefits document states that health insurance coverage includes medical, dental and vision with a $500 deductible for in-network providers. The company covers 80% of the premium for employees and 60% for dependents. Annual health check-ups are fully covered without applying to your deductible.";
    } else if (lowerMessage.includes('working hours') || lowerMessage.includes('flexible') || lowerMessage.includes('schedule')) {
      response = "I've found in the organizational handbook that flexible working hours are available between 7 AM and 7 PM, with core hours from 10 AM to 3 PM when all employees should be available. You need to complete at least 40 hours per week, and any overtime should be approved in advance by your manager.";
    } else if (lowerMessage.includes('remote') || lowerMessage.includes('wfh') || lowerMessage.includes('work from home')) {
      response = "The company's remote work policy indicates that employees can work remotely up to 3 days per week with prior approval from their manager. Certain roles may have different arrangements based on operational requirements. You need to maintain regular communication and be available during core business hours when working remotely.";
    } else {
      response = "Based on the company documents I've analyzed, I don't have specific information about that topic. Would you like me to provide general information about our HR policies, IT support processes, or employee benefits instead?";
    }

    return NextResponse.json({ response });
  } catch (error) {
    console.error('Error processing chat:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
} 