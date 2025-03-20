"use client";

import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useState } from 'react';
import axios from 'axios';
import { toast } from 'react-hot-toast';
import { useAuth } from '@/app/context/AuthContext';

const SignUp = () => {
  const router = useRouter();
  const { setUserEmail, setUserPassword } = useAuth();

  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [otpSent, setOtpSent] = useState(false);
  const [otpVerified, setOtpVerified] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  
  // Replace with your backend URL
  const API_BASE_URL = 'http://localhost:8000'; // Update this with your actual backend URL

  const handleSendOtp = async () => {
    if (!email) return;
    setLoading(true);
    setError('');
    try {
      const response = await axios.post(`${API_BASE_URL}/request_signup_otp`, { 
        "email": email 
      });
      
      if (response.status === 200) {
        setOtpSent(true);
        toast.success('OTP sent successfully!');
        
        // For development, show the debug OTP if available
        if (response.data.debug_otp) {
          toast.success(`Development OTP: ${response.data.debug_otp}`);
        }
      }
    } catch (error) {
      console.error('Failed to send OTP:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to send OTP. Please try again.';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const verifyOtp = async () => {
    if (!otp || !email) return;
    setLoading(true);
    setError('');
    try {
      const response = await axios.post(`${API_BASE_URL}/verify_signup_otp`, { 
        "email": email, 
        "otp": otp 
      });
      
      if (response.data.status === true) {
        setOtpVerified(true);
        toast.success('OTP verified successfully!');
      } else {
        setError('Invalid OTP. Please try again.');
        toast.error('Invalid OTP. Please try again.');
      }
    } catch (error) {
      console.error('Failed to verify OTP:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to verify OTP. Please try again.';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!otpVerified) {
      setError('Please verify OTP first');
      toast.error('Please verify OTP first');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const response = await axios.post(`${API_BASE_URL}/signup`, {
        "email": email,
        "password": password,
        "username": name
      });

      if (response.data.status === true) {
        setUserEmail(email);
        setUserPassword(password);
        localStorage.setItem('userEmail', email);
        localStorage.setItem('userPassword', password);
        
        toast.success('Sign up successful! Redirecting to login...');
        router.push('/auth/login');
      } else {
        setError(response.data.message);
        toast.error(response.data.message);
      }
    } catch (error) {
      console.error('Failed to sign up:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to sign up. Please try again.';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex justify-center items-center h-screen bg-gray-900 text-gray-100">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 w-full max-w-5xl p-8">
        {/* Left Side - Info Section */}
        <div className="flex flex-col justify-center space-y-6">
          <h1 className="text-4xl font-bold">Get in touch.</h1>
          <p className="text-gray-400 text-lg">
            Need some help? Let us know what you need and we'll get straight back to you.
          </p>
        </div>

        {/* Right Side - Form Section */}
        <div className="bg-gray-800 p-8 rounded-lg shadow-lg">
          <h2 className="text-3xl font-bold text-center mb-4">Create Your Account</h2>
          <p className="text-center text-sm text-gray-400 mb-6">Sign up to get started.</p>

          {error && (
            <div className="bg-red-500 bg-opacity-20 border border-red-500 text-red-500 px-4 py-3 rounded-lg mb-6">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Full Name Input */}
            <div>
              <label className="block text-gray-300 mb-2">Username</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-4 py-3 border border-gray-600 bg-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                placeholder="Enter your username"
                required
                disabled={otpVerified && loading}
              />
            </div>

            {/* Email Input */}
            <div>
              <label className="block text-gray-300 mb-2">Email</label>
              <div className="flex gap-2">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-600 bg-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                  placeholder="Enter your email"
                  required
                  disabled={otpSent || loading}
                />
                <button
                  type="button"
                  onClick={handleSendOtp}
                  disabled={loading || !email || otpVerified}
                  className="px-4 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
                >
                  {loading && !otpVerified ? 'Sending...' : otpSent && !otpVerified ? 'Resend' : 'Send OTP'}
                </button>
              </div>
            </div>

            {otpSent && !otpVerified && (
              <div>
                <label className="block text-gray-300 font-medium mb-2">Verification Code (OTP)</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value)}
                    className="flex-1 px-4 py-3 border border-gray-600 bg-gray-700 text-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                    placeholder="Enter OTP"
                    required
                    disabled={loading}
                  />
                  <button
                    type="button"
                    onClick={verifyOtp}
                    disabled={loading || !otp || otpVerified}
                    className="px-4 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
                  >
                    {loading ? 'Verifying...' : 'Verify'}
                  </button>
                </div>
              </div>
            )}

            {/* Password Input - Only show after OTP is verified */}
            {otpVerified && (
              <div>
                <label className="block text-gray-300 mb-2">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-600 bg-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                  placeholder="Create a password"
                  required
                  disabled={loading}
                />
                <p className="text-xs text-gray-400 mt-2">
                  Password must be at least 8 characters with uppercase, lowercase, number, and special character.
                </p>
              </div>
            )}

            {/* Sign Up Button - Only enable after OTP is verified */}
            <button
              type="submit"
              disabled={!otpVerified || !name || !password || loading}
              className="w-full py-3 bg-blue-500 text-white font-semibold rounded-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-50"
            >
              {loading ? 'Creating Account...' : 'Create Account'}
            </button>
          </form>

          {/* Additional Options */}
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-400">
              Already have an account?{' '}
              <Link href="/auth/login" className="text-blue-400 hover:underline">
                Log In
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SignUp;