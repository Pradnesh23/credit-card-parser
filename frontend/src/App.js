import React, { useState, useEffect } from 'react';
import { Upload, CreditCard, Calendar, FileText, CheckCircle, XCircle, AlertCircle, Loader2, Download, FolderOpen, BarChart3, TrendingUp, Shield, Zap, Eye, Target, Activity, Trash2 } from 'lucide-react';

const CreditCardParser = () => {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [csvFiles, setCsvFiles] = useState(null);
  const [history, setHistory] = useState([]);
  const [deletingId, setDeletingId] = useState(null);

  const API_URL = window.location.origin.includes('localhost') 
    ? 'http://localhost:3000' 
    : 'http://credit-card-parser-xo-dduk1si.hello-xo.nl:3000';

  const loadHistory = async () => {
    try {
      const res = await fetch(`${API_URL}/api/history?limit=25`);
      if (!res.ok) return;
      const data = await res.json();
      setHistory(Array.isArray(data.items) ? data.items : []);
    } catch (_) {
      // ignore
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (selectedFile) => {
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setError(null);
      setResult(null);
      setCsvFiles(null);
    } else {
      setError('Please select a valid PDF file');
    }
  };

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const parseStatement = async () => {
    if (!file) {
      setError('Please select a file first');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setCsvFiles(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_URL}/api/parse`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setResult(data.data);
        setCsvFiles(data.data.csv_exports);
        loadHistory(); // Refresh history after successful parse
      } else {
        setError(data.error || 'Failed to parse statement');
      }
    } catch (err) {
      setError('Network error. Make sure the backend server is running on port 5000.');
    } finally {
      setLoading(false);
    }
  };

  const downloadCSV = async (filename) => {
    try {
      if (!filename) {
        throw new Error('No filename provided');
      }
      const base = filename.split('\\').pop().split('/').pop();
      const encoded = encodeURIComponent(base);
      const response = await fetch(`${API_URL}/api/download-csv/${encoded}`);
      
      if (!response.ok) {
        throw new Error('Failed to download file');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = base;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError('Failed to download CSV file');
    }
  };

  const deleteRecord = async (recordId) => {
    if (!window.confirm('Are you sure you want to delete this record and its CSV file?')) {
      return;
    }

    setDeletingId(recordId);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/api/history/${recordId}`, {
        method: 'DELETE',
      });

      const data = await response.json();

      if (response.ok && data.success) {
        // Remove from local state
        setHistory(prev => prev.filter(item => item.id !== recordId));
      } else {
        setError(data.error || 'Failed to delete record');
      }
    } catch (err) {
      setError('Network error while deleting record');
    } finally {
      setDeletingId(null);
    }
  };

  const resetForm = () => {
    setFile(null);
    setResult(null);
    setError(null);
    setCsvFiles(null);
    loadHistory();
  };

  const getConfidenceColor = (score) => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.5) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getConfidenceBadge = (score) => {
    if (score >= 0.8) return 'bg-green-100 text-green-800';
    if (score >= 0.5) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  const getConfidenceIcon = (score) => {
    if (score >= 0.8) return <Shield className="w-4 h-4" />;
    if (score >= 0.5) return <AlertCircle className="w-4 h-4" />;
    return <XCircle className="w-4 h-4" />;
  };

  const formatCurrency = (amount) => {
    if (!amount) return '$0.00';
    const num = parseFloat(amount.replace(/[,$]/g, ''));
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(num);
  };

  const getTransactionCategory = (description) => {
    const desc = description.toLowerCase();
    if (desc.includes('grocery') || desc.includes('food') || desc.includes('restaurant')) return 'Food & Dining';
    if (desc.includes('gas') || desc.includes('fuel') || desc.includes('shell') || desc.includes('exxon')) return 'Gas & Transportation';
    if (desc.includes('amazon') || desc.includes('walmart') || desc.includes('target') || desc.includes('store')) return 'Shopping';
    if (desc.includes('netflix') || desc.includes('spotify') || desc.includes('subscription')) return 'Entertainment';
    if (desc.includes('medical') || desc.includes('pharmacy') || desc.includes('health')) return 'Healthcare';
    return 'Other';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center mb-6">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full blur-lg opacity-30"></div>
              <CreditCard className="relative w-16 h-16 text-blue-600 mr-4" />
            </div>
            <div>
              <h1 className="text-5xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                Smart Statement Parser
              </h1>
              <p className="text-gray-500 text-sm mt-1">Powered by Advanced OCR & AI</p>
            </div>
          </div>
          <p className="text-gray-600 text-xl max-w-3xl mx-auto leading-relaxed">
            Transform your credit card statements into actionable insights with our intelligent parsing technology
          </p>
          
          {/* Feature Highlights */}
          <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto">
            <div className="flex items-center gap-2 bg-white/60 backdrop-blur-sm rounded-lg px-4 py-2">
              <Zap className="w-5 h-5 text-yellow-500" />
              <span className="text-sm font-medium text-gray-700">Multi-Variant OCR</span>
            </div>
            <div className="flex items-center gap-2 bg-white/60 backdrop-blur-sm rounded-lg px-4 py-2">
              <Eye className="w-5 h-5 text-blue-500" />
              <span className="text-sm font-medium text-gray-700">Context-Aware</span>
            </div>
            <div className="flex items-center gap-2 bg-white/60 backdrop-blur-sm rounded-lg px-4 py-2">
              <Shield className="w-5 h-5 text-green-500" />
              <span className="text-sm font-medium text-gray-700">Smart Validation</span>
            </div>
            <div className="flex items-center gap-2 bg-white/60 backdrop-blur-sm rounded-lg px-4 py-2">
              <Target className="w-5 h-5 text-purple-500" />
              <span className="text-sm font-medium text-gray-700">High Accuracy</span>
            </div>
          </div>

          {/* Supported Banks */}
          <div className="mt-6 flex items-center justify-center gap-3 flex-wrap">
            <span className="px-4 py-2 bg-gradient-to-r from-blue-100 to-blue-200 text-blue-800 rounded-full text-sm font-semibold shadow-sm">Capital One</span>
            <span className="px-4 py-2 bg-gradient-to-r from-purple-100 to-purple-200 text-purple-800 rounded-full text-sm font-semibold shadow-sm">American Express</span>
            <span className="px-4 py-2 bg-gradient-to-r from-orange-100 to-orange-200 text-orange-800 rounded-full text-sm font-semibold shadow-sm">ICICI Bank</span>
            <span className="px-4 py-2 bg-gradient-to-r from-pink-100 to-pink-200 text-pink-800 rounded-full text-sm font-semibold shadow-sm">Kotak Mahindra</span>
            <span className="px-4 py-2 bg-gradient-to-r from-indigo-100 to-indigo-200 text-indigo-800 rounded-full text-sm font-semibold shadow-sm">HDFC Bank</span>
            <span className="px-4 py-2 bg-gradient-to-r from-green-100 to-green-200 text-green-800 rounded-full text-sm font-semibold shadow-sm">SBI Card</span>
          </div>
          </div>

        {/* Error Display */}
        {error && (
          <div className="max-w-2xl mx-auto mb-6">
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
              <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-red-900">Error</p>
                <p className="text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Upload Section */}
        {!result && (
          <div className="max-w-2xl mx-auto">
            <div
              className={`relative border-2 border-dashed rounded-2xl p-12 text-center transition-all duration-300 ${
                dragActive
                  ? 'border-blue-500 bg-gradient-to-br from-blue-50 to-purple-50 scale-105 shadow-lg'
                  : 'border-gray-300 bg-white/80 backdrop-blur-sm hover:border-blue-400 hover:shadow-xl'
              }`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <input
                type="file"
                id="file-upload"
                accept=".pdf"
                onChange={handleFileInput}
                className="hidden"
              />
              
              <label htmlFor="file-upload" className="cursor-pointer">
                <div className="relative mb-6">
                  <div className={`absolute inset-0 rounded-full transition-all duration-300 ${dragActive ? 'bg-blue-100 scale-110' : 'bg-gray-100'}`}></div>
                  <Upload className={`relative w-20 h-20 mx-auto ${dragActive ? 'text-blue-600 animate-bounce' : 'text-gray-400'}`} />
                </div>
                <p className="text-xl font-bold text-gray-800 mb-3">
                  {file ? (
                    <span className="flex items-center justify-center gap-2">
                      <FileText className="w-6 h-6 text-green-600" />
                      {file.name}
                    </span>
                  ) : (
                    'Drop your PDF here or click to browse'
                  )}
                </p>
                <p className="text-sm text-gray-500 mb-4">
                  Supports PDF files up to 10MB • All major credit card issuers
                </p>
                {file && (
                  <div className="inline-flex items-center gap-2 bg-green-100 text-green-800 px-4 py-2 rounded-full text-sm font-medium">
                    <CheckCircle className="w-4 h-4" />
                    File ready for processing
                  </div>
                )}
              </label>

              {file && (
                <div className="mt-8 flex items-center justify-center gap-4">
                  <button
                    onClick={parseStatement}
                    disabled={loading}
                    className="px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl font-bold hover:from-blue-700 hover:to-purple-700 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-3 shadow-lg hover:shadow-xl transform hover:scale-105"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-6 h-6 animate-spin" />
                        <span>Processing with AI...</span>
                      </>
                    ) : (
                      <>
                        <Zap className="w-6 h-6" />
                        <span>Parse Statement</span>
                      </>
                    )}
                  </button>
                  <button
                    onClick={resetForm}
                    className="px-6 py-4 bg-white/80 backdrop-blur-sm text-gray-700 rounded-xl font-semibold hover:bg-white transition-all duration-300 border border-gray-200 hover:border-gray-300"
                  >
                    Clear
                  </button>
                </div>
              )}
            </div>

            {/* Previous Parses */}
            <div className="mt-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <FolderOpen className="w-5 h-5 text-gray-700" /> Previously Parsed
              </h3>
              {history.length === 0 ? (
                <p className="text-sm text-gray-500">No previous parses yet.</p>
              ) : (
                <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-2 px-3">Date</th>
                        <th className="text-left py-2 px-3">Issuer</th>
                        <th className="text-left py-2 px-3">Card</th>
                        <th className="text-left py-2 px-3">Statement</th>
                        <th className="text-right py-2 px-3">Total</th>
                        <th className="text-right py-2 px-3">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.map(item => (
                        <tr key={item.id} className="border-b border-gray-100 hover:bg-gray-50">
                          <td className="py-2 px-3 text-gray-600">{item.created_at}</td>
                          <td className="py-2 px-3 text-gray-900">{item.issuer}</td>
                          <td className="py-2 px-3 text-gray-900">•••• {item.card_last_4}</td>
                          <td className="py-2 px-3 text-gray-900">{item.statement_date || '—'}</td>
                          <td className="py-2 px-3 text-right text-gray-900">{item.total_balance ? `$${item.total_balance}` : '—'}</td>
                          <td className="py-2 px-3">
                            <div className="flex justify-end gap-2">
                              {item.csv_exports?.detailed && (
                                <button
                                  onClick={() => downloadCSV(item.csv_exports.detailed)}
                                  className="px-2 py-1 border border-blue-300 bg-blue-50 rounded hover:bg-blue-100 transition-colors inline-flex items-center gap-1"
                                  title="Download Statement CSV"
                                >
                                  <Download className="w-3.5 h-3.5 text-blue-600" />
                                  <span className="text-xs text-blue-600 font-medium">Statement</span>
                                </button>
                              )}
                              {item.csv_exports?.master && (
                                <button
                                  onClick={() => downloadCSV(item.csv_exports.master)}
                                  className="px-2 py-1 border border-green-300 bg-green-50 rounded hover:bg-green-100 transition-colors inline-flex items-center gap-1"
                                  title="Download Master Log"
                                >
                                  <Download className="w-3.5 h-3.5 text-green-600" />
                                  <span className="text-xs text-green-600 font-medium">Master</span>
                                </button>
                              )}
                              <button
                                onClick={() => deleteRecord(item.id)}
                                disabled={deletingId === item.id}
                                className="px-2 py-1 border border-red-300 bg-red-50 rounded hover:bg-red-100 transition-colors inline-flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
                                title="Delete Record"
                              >
                                {deletingId === item.id ? (
                                  <Loader2 className="w-3.5 h-3.5 text-red-600 animate-spin" />
                                ) : (
                                  <Trash2 className="w-3.5 h-3.5 text-red-600" />
                                )}
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Results Section */}
        {result && (
          <div className="space-y-8 animate-in fade-in duration-500">
            {/* Success Banner with CSV Download */}
            <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-2xl p-6 shadow-lg">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="relative">
                    <div className="absolute inset-0 bg-green-400 rounded-full blur-lg opacity-30"></div>
                    <CheckCircle className="relative w-8 h-8 text-green-600" />
                  </div>
                  <div>
                    <p className="font-bold text-green-900 text-lg">Statement Successfully Parsed!</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-sm text-green-700">Overall Confidence:</span>
                      <span className={`px-3 py-1 rounded-full text-sm font-bold ${getConfidenceBadge(result.extraction_metadata?.overall_confidence)}`}>
                        {(result.extraction_metadata?.overall_confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={resetForm}
                  className="px-6 py-3 bg-white border border-green-300 text-green-700 rounded-xl hover:bg-green-50 transition-all duration-300 font-semibold shadow-sm hover:shadow-md"
                >
                  Parse Another
                </button>
              </div>

              {/* CSV Download Buttons */}
              {csvFiles && (
                <div className="mt-6 pt-6 border-t border-green-200">
                  <p className="text-sm font-bold text-green-900 mb-4 flex items-center gap-2">
                    <FolderOpen className="w-5 h-5" />
                    Export Your Data:
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <button
                      onClick={() => downloadCSV(csvFiles.detailed)}
                      className="px-6 py-4 bg-white border border-green-300 text-green-700 rounded-xl hover:bg-green-50 transition-all duration-300 flex items-center gap-3 text-sm font-semibold shadow-sm hover:shadow-md transform hover:scale-105"
                    >
                      <Download className="w-5 h-5" />
                      <div className="text-left">
                        <div className="font-bold">This Statement</div>
                        <div className="text-xs text-green-600">Complete details with transactions</div>
                      </div>
                    </button>
                    <button
                      onClick={() => downloadCSV(csvFiles.master)}
                      className="px-6 py-4 bg-white border border-green-300 text-green-700 rounded-xl hover:bg-green-50 transition-all duration-300 flex items-center gap-3 text-sm font-semibold shadow-sm hover:shadow-md transform hover:scale-105"
                    >
                      <Download className="w-5 h-5" />
                      <div className="text-left">
                        <div className="font-bold">Master Log</div>
                        <div className="text-xs text-green-600">All statements combined</div>
                      </div>
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Analytics Dashboard */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Key Metrics */}
              <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Issuer */}
                <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-2xl shadow-lg border border-blue-200 p-6">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 bg-blue-500 rounded-lg">
                      <CreditCard className="w-6 h-6 text-white" />
                    </div>
                    <h3 className="font-bold text-gray-800">Card Issuer</h3>
                  </div>
                  <p className="text-3xl font-bold text-blue-900">{result.card_issuer || 'N/A'}</p>
                </div>

                {/* Card Last 4 */}
                <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-2xl shadow-lg border border-purple-200 p-6">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 bg-purple-500 rounded-lg">
                      <Shield className="w-6 h-6 text-white" />
                    </div>
                    <h3 className="font-bold text-gray-800">Card Last 4</h3>
                  </div>
                  <p className="text-3xl font-bold text-purple-900">
                    •••• {result.card_last_4 || 'N/A'}
                  </p>
                </div>

                {/* Statement Date */}
                <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-2xl shadow-lg border border-green-200 p-6">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 bg-green-500 rounded-lg">
                      <Calendar className="w-6 h-6 text-white" />
                    </div>
                    <h3 className="font-bold text-gray-800">Statement Date</h3>
                  </div>
                  <p className="text-2xl font-bold text-green-900">{result.statement_date || 'N/A'}</p>
                </div>

                {/* Due Date */}
                <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-2xl shadow-lg border border-orange-200 p-6">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 bg-orange-500 rounded-lg">
                      <AlertCircle className="w-6 h-6 text-white" />
                    </div>
                    <h3 className="font-bold text-gray-800">Payment Due</h3>
                  </div>
                  <p className="text-2xl font-bold text-orange-900">{result.payment_due_date || 'N/A'}</p>
                </div>
              </div>

              {/* Financial Summary */}
              <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-2xl shadow-lg border border-gray-200 p-6">
                <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                  <BarChart3 className="w-6 h-6 text-gray-600" />
                  Financial Summary
                </h3>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600 font-medium">Total Balance</span>
                    <span className="text-2xl font-bold text-red-600">
                      {formatCurrency(result.total_balance)}
                    </span>
                  </div>
                  {result.minimum_payment && (
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600 font-medium">Minimum Payment</span>
                      <span className="text-xl font-bold text-blue-600">
                        {formatCurrency(result.minimum_payment)}
                      </span>
                    </div>
                  )}
                  {result.transactions && (
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600 font-medium">Transactions</span>
                      <span className="text-lg font-bold text-gray-800">
                        {result.transactions.length}
                      </span>
                    </div>
                  )}
                  <div className="pt-3 border-t border-gray-200">
                    <div className="flex items-center gap-2">
                      <Activity className="w-4 h-4 text-gray-500" />
                      <span className="text-sm text-gray-600">Processing Quality</span>
                    </div>
                    <div className="mt-2">
                      <div className="flex items-center gap-2">
                        {getConfidenceIcon(result.extraction_metadata?.overall_confidence)}
                        <span className={`text-sm font-semibold ${getConfidenceColor(result.extraction_metadata?.overall_confidence)}`}>
                          {(result.extraction_metadata?.overall_confidence * 100).toFixed(0)}% Accurate
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Transactions Analysis */}
            {result.transactions && result.transactions.length > 0 && (
              <div className="space-y-6">
                {/* Transaction Categories */}
                <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-2xl shadow-lg border border-indigo-200 p-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <TrendingUp className="w-6 h-6 text-indigo-600" />
                    Spending Analysis
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {(() => {
                      const categories = {};
                      result.transactions.forEach(txn => {
                        const category = getTransactionCategory(txn.description);
                        const amount = parseFloat(txn.amount.replace(/[,$]/g, ''));
                        categories[category] = (categories[category] || 0) + amount;
                      });
                      return Object.entries(categories).map(([category, total]) => (
                        <div key={category} className="bg-white/80 backdrop-blur-sm rounded-xl p-4 text-center">
                          <div className="text-sm font-medium text-gray-600 mb-1">{category}</div>
                          <div className="text-lg font-bold text-gray-900">{formatCurrency(total.toString())}</div>
                        </div>
                      ));
                    })()}
                  </div>
                </div>

                {/* Transactions Table */}
                <div className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden">
                  <div className="bg-gradient-to-r from-gray-50 to-gray-100 px-6 py-4 border-b border-gray-200">
                    <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                      <FileText className="w-6 h-6 text-blue-600" />
                      Transaction Details ({result.transactions.length})
                    </h3>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="text-left py-4 px-6 font-bold text-gray-700">Date</th>
                          <th className="text-left py-4 px-6 font-bold text-gray-700">Description</th>
                          <th className="text-left py-4 px-6 font-bold text-gray-700">Category</th>
                          <th className="text-right py-4 px-6 font-bold text-gray-700">Amount</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.transactions.map((txn, idx) => (
                          <tr key={idx} className="border-b border-gray-100 hover:bg-blue-50/50 transition-colors">
                            <td className="py-4 px-6 text-gray-600 font-medium">{txn.date}</td>
                            <td className="py-4 px-6 text-gray-900">{txn.description}</td>
                            <td className="py-4 px-6">
                              <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-semibold">
                                {getTransactionCategory(txn.description)}
                              </span>
                            </td>
                            <td className="py-4 px-6 text-right font-bold text-gray-900">
                              {formatCurrency(txn.amount)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* Advanced Processing Details */}
            {result.extraction_metadata && (
              <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-2xl shadow-lg border border-gray-200 p-6">
                <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
                  <Activity className="w-6 h-6 text-gray-600" />
                  Advanced Processing Details
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                  <div className="text-center">
                    <div className="p-3 bg-blue-100 rounded-xl w-fit mx-auto mb-2">
                      <FileText className="w-6 h-6 text-blue-600" />
                    </div>
                    <p className="text-sm text-gray-600 font-medium">Pages Processed</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {result.extraction_metadata.num_pages || 'N/A'}
                    </p>
                  </div>
                  <div className="text-center">
                    <div className="p-3 bg-green-100 rounded-xl w-fit mx-auto mb-2">
                      <Eye className="w-6 h-6 text-green-600" />
                    </div>
                    <p className="text-sm text-gray-600 font-medium">Text Extracted</p>
                    <p className="text-lg font-bold text-gray-900">
                      {result.extraction_metadata.text_length ? `${Math.round(result.extraction_metadata.text_length / 1000)}K chars` : 'N/A'}
                    </p>
                  </div>
                  <div className="text-center">
                    <div className="p-3 bg-purple-100 rounded-xl w-fit mx-auto mb-2">
                      <Target className="w-6 h-6 text-purple-600" />
                    </div>
                    <p className="text-sm text-gray-600 font-medium">Processing Method</p>
                    <p className="text-sm font-bold text-gray-900">
                      {result.extraction_metadata.extraction_method || 'N/A'}
                    </p>
                  </div>
                  <div className="text-center">
                    <div className="p-3 bg-yellow-100 rounded-xl w-fit mx-auto mb-2">
                      <Shield className="w-6 h-6 text-yellow-600" />
                    </div>
                    <p className="text-sm text-gray-600 font-medium">Confidence</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {(result.extraction_metadata.overall_confidence * 100).toFixed(0)}%
                    </p>
                  </div>
                </div>

                {/* Validation Results */}
                {result.extraction_metadata.validation && (
                  <div className="mt-6 pt-6 border-t border-gray-200">
                    <h4 className="text-lg font-bold text-gray-800 mb-3 flex items-center gap-2">
                      <Shield className="w-5 h-5 text-green-500" />
                      Validation Results
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="bg-white/80 backdrop-blur-sm rounded-xl p-4 text-center">
                        <p className="text-sm text-gray-600 font-medium mb-1">Checks Performed</p>
                        <p className="text-2xl font-bold text-blue-600">
                          {result.extraction_metadata.validation.checks || 0}
                        </p>
                      </div>
                      <div className="bg-white/80 backdrop-blur-sm rounded-xl p-4 text-center">
                        <p className="text-sm text-gray-600 font-medium mb-1">Issues Found</p>
                        <p className="text-2xl font-bold text-orange-600">
                          {result.extraction_metadata.validation.failed || 0}
                        </p>
                      </div>
                      <div className="bg-white/80 backdrop-blur-sm rounded-xl p-4 text-center">
                        <p className="text-sm text-gray-600 font-medium mb-1">Success Rate</p>
                        <p className="text-2xl font-bold text-green-600">
                          {result.extraction_metadata.validation.checks > 0 
                            ? Math.round(((result.extraction_metadata.validation.checks - (result.extraction_metadata.validation.failed || 0)) / result.extraction_metadata.validation.checks) * 100)
                            : 100}%
                        </p>
                      </div>
                    </div>
                    {result.extraction_metadata.validation.messages && result.extraction_metadata.validation.messages.length > 0 && (
                      <div className="mt-4">
                        <p className="text-sm text-gray-600 font-medium mb-2">Validation Messages:</p>
                        <div className="space-y-1">
                          {result.extraction_metadata.validation.messages.map((msg, idx) => (
                            <div key={idx} className="text-sm text-orange-700 bg-orange-50 px-3 py-2 rounded-lg">
                              {msg}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default CreditCardParser;