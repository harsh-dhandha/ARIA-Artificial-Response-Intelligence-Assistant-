import { NextRequest, NextResponse } from 'next/server';

// This is a simple API route for retrieving user documents
// In a real implementation, this would connect to a database or storage service

export async function GET(req: NextRequest) {
  try {
    // Get user from query params
    const searchParams = req.nextUrl.searchParams;
    const userEmail = searchParams.get('user');

    if (!userEmail) {
      return NextResponse.json({ error: 'User email is required' }, { status: 400 });
    }

    console.log('Fetching documents for user:', userEmail);

    // In a real implementation, this would:
    // 1. Connect to a database or storage service
    // 2. Query for documents uploaded by this user
    // 3. Return the document metadata
    
    // For now, we'll return mock data
    // Simulate a delayed response
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Mock document data
    const documents = [
      'Company HR Policy Handbook.pdf',
      'IT Support Guidelines.pdf',
      'Employee Benefits 2023.pdf',
      'Organizational Handbook.pdf',
      'Remote Work Policy.pdf'
    ];

    return NextResponse.json({ documents });
  } catch (error) {
    console.error('Error fetching documents:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
} 