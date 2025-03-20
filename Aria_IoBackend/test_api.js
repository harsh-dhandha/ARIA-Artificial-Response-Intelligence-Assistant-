// This is a simple test script to diagnose API issues

const axios = require('axios');
const API_URL = 'http://localhost:8000';

async function testHealthCheck() {
  try {
    console.log('Testing health endpoint...');
    const response = await axios.get(`${API_URL}/health`);
    console.log('Health check response:', response.status, response.data);
    return true;
  } catch (error) {
    console.error('Health check failed:', error.message);
    return false;
  }
}

async function testSignupOTP() {
  try {
    console.log('Testing signup OTP endpoint...');
    const response = await axios.post(`${API_URL}/request_signup_otp`, {
      email: 'test@example.com'
    });
    console.log('Signup OTP response:', response.status, response.data);
    return true;
  } catch (error) {
    console.error('Signup OTP request failed:', error.message);
    if (error.response) {
      console.error('Response data:', error.response.data);
      console.error('Response status:', error.response.status);
    }
    return false;
  }
}

async function runAllTests() {
  const healthOk = await testHealthCheck();
  if (!healthOk) {
    console.log('API server may not be running properly. Please check server logs.');
    return;
  }
  
  await testSignupOTP();
}

// Run the tests
runAllTests();
