import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

function App() {
	console.log('App component rendering...');
	console.log('API_BASE:', API_BASE);
	
	// Load session ID from localStorage
	const [sessionId, setSessionId] = useState(() => {
		const saved = localStorage.getItem('chatbot_session_id');
		return saved || null;
	});
	const [filename, setFilename] = useState('');
	const [messages, setMessages] = useState([]);
	const [inputMessage, setInputMessage] = useState('');
	const [isLoading, setIsLoading] = useState(false);
	const [isUploading, setIsUploading] = useState(false);
	const messagesEndRef = useRef(null);

	const scrollToBottom = () => {
		messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
	};

	useEffect(() => {
		scrollToBottom();
	}, [messages]);

	useEffect(() => {
		const loadChatHistory = async () => {
			if (!sessionId) return;
			try {
				const response = await axios.get(`${API_BASE}/chat-history/${sessionId}`);
				if (response.data.history && response.data.history.length > 0) {
					setMessages(response.data.history.map(msg => ({
						role: msg.role,
						content: msg.content
					})));
				}
				if (response.data.filename && response.data.filename !== 'General Chat' && response.data.has_vector_store) {
					setFilename(response.data.filename);
				}
			} catch (error) {
				if (error.response?.status === 404) {
					setSessionId(null);
					setFilename('');
					setMessages([]);
					localStorage.removeItem('chatbot_session_id');
				}
			}
		};
		loadChatHistory();
	}, [sessionId]);

	const handleFileUpload = async (event) => {
		const file = event.target.files[0];
		if (!file) return;
		if (!file.name.endsWith('.pdf')) {
			alert('Please upload a PDF file only.');
			return;
		}
		setIsUploading(true);
		const formData = new FormData();
		formData.append('file', file);
		if (sessionId) {
			formData.append('session_id', sessionId);
		}
		try {
			const response = await axios.post(`${API_BASE}/upload-pdf`, formData, {
				headers: { 'Content-Type': 'multipart/form-data' }
			});
			setSessionId(response.data.session_id);
			setFilename(response.data.filename);
			localStorage.setItem('chatbot_session_id', response.data.session_id);
			// Add system message without clearing existing messages
			setMessages(prev => [...prev, {
				role: 'system',
				content: `PDF "${response.data.filename}" uploaded successfully! You can now ask questions about your documents.`
			}]);
		} catch (error) {
			let errorMsg = error.response?.data?.detail || error.message;
			if (error.response?.status === 429) {
				errorMsg = 'You have exceeded your Gemini API quota. Please check your plan or try again later.';
			}
			setMessages([{
				role: 'system',
				content: `Error uploading PDF: ${errorMsg}`
			}]);
		} finally {
			setIsUploading(false);
		}
	};

	const handleSendMessage = async () => {
		const trimmedMessage = inputMessage.trim();
		if (!trimmedMessage) {
			// Show user feedback for empty input
			setMessages(prev => [...prev, { 
				role: 'system', 
				content: 'Please enter a valid question or message.' 
			}]);
			return;
		}
		if (trimmedMessage.length < 2) {
			setMessages(prev => [...prev, { 
				role: 'system', 
				content: 'Please enter a more detailed question.' 
			}]);
			return;
		}
		
		// Create session ID if none exists (for general chat)
		let currentSessionId = sessionId;
		if (!currentSessionId) {
			// Check localStorage one more time before creating new session
			const savedSession = localStorage.getItem('chatbot_session_id');
			if (savedSession) {
				currentSessionId = savedSession;
				setSessionId(savedSession);
			} else {
				currentSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
				setSessionId(currentSessionId);
				// Save to localStorage
				localStorage.setItem('chatbot_session_id', currentSessionId);
			}
		}
		setIsLoading(true);
		setMessages(prev => [...prev, { role: 'user', content: trimmedMessage }]);
		
		// Add thinking message
		const thinkingId = Date.now();
		setMessages(prev => [...prev, { role: 'assistant', content: 'Thinking...', isThinking: true, id: thinkingId }]);
		
		setInputMessage('');
		try {
			const response = await axios.post(`${API_BASE}/chat`, {
				session_id: currentSessionId,
				message: trimmedMessage
			});

			// Replace thinking message with actual response
			setMessages(prev => prev.map(msg => 
				msg.id === thinkingId ? { role: 'assistant', content: response.data.response } : msg
			));
		} catch (error) {
			let errorMsg = 'Error: Unable to get response.';
			if (error.response?.status === 429) {
				errorMsg = 'You have exceeded your Gemini API quota. Please check your plan or try again later.';
			}
			// Replace thinking message with error
			setMessages(prev => prev.map(msg => 
				msg.id === thinkingId ? { role: 'assistant', content: errorMsg } : msg
			));
		}
		setIsLoading(false);
	};

	const handleReset = async () => {
		// Delete session from backend if it exists
		if (sessionId) {
			try {
				await axios.delete(`${API_BASE}/session/${sessionId}`);
			} catch (error) {
				// Session deletion failed
			}
		}
		
		// Clear frontend state
		setSessionId(null);
		setFilename('');
		setMessages([]);
		setInputMessage('');
		localStorage.removeItem('chatbot_session_id');
	};



	return (
		<div className="container">
			<div className="sidebar">
				<div className="sidebar-header">
					<div className="sidebar-title">
						<img src="https://cdn-icons-png.flaticon.com/512/337/337946.png" alt="PDF" className="pdf-icon" />
						<span>PDF Chatbot</span>
					</div>
				</div>
				<div className="upload-box">
					<label htmlFor="pdf-upload" className="upload-label">
						<span role="img" aria-label="folder" className="upload-icon">📁</span> Click to add a PDF
					</label>
					<input
						id="pdf-upload"
						type="file"
						accept="application/pdf"
						className="file-input"
						onChange={handleFileUpload}
						disabled={isUploading}
						style={{ display: 'none' }}
					/>
					{isUploading && <div className="uploading">Uploading...</div>}
				</div>
			</div>
			<div className="main-chat">
				<div className="chat-header">
					<span>AI Assistant</span>
				</div>
				<div className="messages-box">
					{messages.length === 0 ? (
						<div className="no-messages">Start chatting! You can ask general questions or upload a PDF for document-specific queries.</div>
					) : (
						messages.map((msg, idx) => (
							<div key={idx} className={`message ${msg.role}`}>
								<div className="message-content">
									{msg.isThinking ? (
										<span className="thinking-dots">
											Thinking<span className="dots">...</span>
										</span>
									) : (
										msg.content
									)}
								</div>
							</div>
						))
					)}
					<div ref={messagesEndRef} />
				</div>
				<div className="input-area">
					<input
						type="text"
						value={inputMessage}
						onChange={e => setInputMessage(e.target.value)}
						onKeyDown={e => e.key === 'Enter' && handleSendMessage()}
						placeholder="Ask anything or upload a PDF for document questions..."
						disabled={isLoading}
						className="chat-input"
					/>
					<button onClick={handleSendMessage} disabled={isLoading} className="send-btn">Send</button>
				</div>
				{filename && (
					<div className="current-file-info">
						<span>Current Documents: <b>{filename}</b></span>
						<button className="reset-btn" onClick={handleReset}>Reset</button>
					</div>
				)}
			</div>
		</div>
	);
}

export default App;