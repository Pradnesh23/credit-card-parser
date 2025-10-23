# Credit Card Statement Parser

A full-stack application that extracts and analyzes credit card statements from PDFs using advanced OCR processing.

## ✨ Features

- **Multi-Bank Support**: Parses statements from major banks including Capital One, American Express, ICICI, Kotak, HDFC, and SBI
- **Smart OCR Processing**: Advanced text extraction with auto-rotation and multi-strategy preprocessing
- **Transaction Analysis**: Automatic categorization and spending insights
- **Export Options**: Export to CSV with transaction details and master logs
- **Modern Web Interface**: Responsive design with drag-and-drop upload

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Node.js 16+
- Tesseract OCR
- SQLite (for local development)

### Installation

1. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   ```

### Running Locally

1. Start the backend:
   ```bash
   cd backend
   python app.py
   ```

2. In a new terminal, start the frontend:
   ```bash
   cd frontend
   npm start
   ```

3. Open [http://localhost:3000](http://localhost:3000) in your browser

## 🛠️ Tech Stack

- **Backend**: Python, Flask, Tesseract OCR, OpenCV
- **Frontend**: React, Tailwind CSS, Lucide Icons
- **Database**: SQLite
- **PDF Processing**: PyPDFium2

## 📄 Supported Statement Formats

- PDF statements from major credit card issuers
- Both single and multi-page statements
- Scanned documents with automatic image enhancement

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
- **Advanced Processing Details**: View OCR metadata and validation results
- **Beautiful Gradients**: Modern, professional interface design

## Prerequisites

- **Python 3.9+**
- **Node.js 14+**
- **npm or yarn**
- **Tesseract OCR** (for processing scanned PDFs)
  - Windows: `choco install tesseract`
  - macOS: `brew install tesseract`
  - Ubuntu/Debian: `sudo apt install tesseract-ocr`

## Setup

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Verify Tesseract installation:
   ```bash
   tesseract --version
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd ../frontend
   ```

2. Install Node.js packages:
   ```bash
   npm install
   ```

## Running the Application

### Start the Backend Server

1. Ensure you're in the `backend` directory with your virtual environment activated
2. Start the Flask server:
   ```bash
   python app.py
   ```
   The backend will start on `http://localhost:5000`

### Start the Frontend

1. Open a new terminal and navigate to the `frontend` directory
2. Start the development server:
   ```bash
   npm start
   ```
   The frontend will automatically open in your browser at `http://localhost:3000`

## Usage Guide

### Parsing a Statement

1. **Upload**: Open the application and either:
   - Drag and drop a PDF credit card statement onto the upload area
   - Click the upload area to browse and select a PDF file

2. **Process**: Click the "Parse Statement" button
   - The AI will automatically detect the card issuer
   - Multiple OCR strategies will be tested
   - Best results will be automatically selected

3. **Review**: View the extracted information including:
   - Card details (issuer, last 4 digits)
   - Important dates (statement date, payment due date)
   - Financial summary (total balance, minimum payment)
   - Complete transaction list with categories
   - Spending analysis by category
   - OCR confidence scores and validation results

4. **Export**: Download your data in multiple formats:
   - **This Statement**: Detailed CSV with all transactions
   - **Master Log**: Cumulative CSV of all parsed statements

### Managing History

- **View History**: All previously parsed statements appear in the "Previously Parsed" section
- **Download CSVs**: Click "Statement" or "Master" buttons to download specific CSV files
- **Delete Records**: Click the trash icon to remove a record and its associated CSV files

### Understanding Confidence Scores

- **Green (80%+)**: Excellent extraction quality, highly reliable
- **Yellow (50-79%)**: Good extraction, may need manual verification
- **Red (<50%)**: Poor extraction quality, manual review recommended

## Supported Credit Card Issuers

The parser supports the following banks with specialized extraction patterns:

| Bank | Currency | Special Features |
|------|----------|------------------|
| **Capital One** | GBP (£) | UK format dates, British English patterns |
| **American Express** | USD ($) / INR (Rs) | US and India variants, membership rewards detection |
| **ICICI Bank** | INR (Rs) | Indian format, comprehensive transaction extraction |
| **Kotak Mahindra** | INR (Rs) | Corporate cards, CRN support |
| **HDFC Bank** | INR (Rs) | Times Card support, multiple date formats |
| **SBI Card** | INR (Rs) | State Bank formats, Indian date patterns |

## How It Works

### Processing Pipeline

1. **Upload & Detection**
   - Frontend sends PDF to backend API
   - First page is analyzed to detect card issuer

2. **OCR Processing**
   - PDF pages rendered at 300 DPI with `pypdfium2`
   - Multiple preprocessing strategies applied:
     - **Enhanced Pro**: Maximum quality with bilateral filtering, aggressive denoising, CLAHE enhancement, sharpening, and combined adaptive thresholding
     - **Aggressive**: Dense text optimization with strong denoising
     - **Comprehensive**: Balanced approach with morphological operations
     - **Light**: Fast processing for high-quality scans
   - Auto-rotation and deskewing applied
   - Best strategy automatically selected based on quality scores

3. **Data Extraction**
   - Unified parser with bank-specific patterns
   - Context-aware field detection
   - Currency-aware amount parsing
   - Smart date normalization
   - Transaction extraction with deduplication

4. **Validation & Scoring**
   - Cross-field validation (date consistency, transaction proximity)
   - Confidence scoring for each field
   - Overall quality assessment
   - Validation messages for detected issues

5. **Storage & Export**
   - Data saved to SQLite database
   - Three CSV formats generated:
     - Simple: Summary only
     - Detailed: Complete with transactions
     - Master: Cumulative log
   - Files stored in `backend/exports/`
   - Metadata returned to frontend

6. **Display**
   - Results rendered in modern, responsive UI
   - Confidence indicators and validation results
   - Spending analysis and categorization
   - One-click CSV downloads
   - Parse history management

## API Endpoints

### `POST /api/parse`
Upload and parse a PDF credit card statement.

**Request**: Multipart form data with `file` field containing PDF
**Response**: Parsed data with CSV file paths, confidence scores, and validation results

### `GET /api/download-csv/<filename>`
Download a generated CSV file.

**Parameters**: `filename` - Name of the CSV file (from parse response)
**Response**: CSV file download

### `GET /api/history?limit=25`
Retrieve parsing history.

**Query Parameters**: `limit` - Maximum number of records (default: 20)
**Response**: Array of parse records with metadata

### `DELETE /api/history/<record_id>`
Delete a parse history record and associated CSV files.

**Parameters**: `record_id` - Database ID of the record
**Response**: Success confirmation

### `GET /health`
Health check and system information.

**Response**: System status, version, features, and supported banks

## Project Structure

```
credit-card-parser/
├── backend/
│   ├── app.py                 # Flask server with unified parser
│   ├── requirements.txt       # Python dependencies
│   └── exports/              # Generated CSV files
│       ├── *.csv             # Individual statement CSVs
│       ├── master_statements.csv  # Master log
│       └── history.db        # SQLite database
│
└── frontend/
    ├── src/
    │   ├── App.js            # Main React component
    │   └── index.js          # Entry point
    ├── public/
    ├── package.json          # Node dependencies
    └── README.md
```

## Technical Highlights

### Backend Architecture
- **Unified Parser**: Single parser class handles all bank formats
- **Pattern Library**: Centralized regex patterns with currency awareness
- **Multi-Strategy OCR**: Four preprocessing strategies with automatic selection
- **Quality Scoring**: Sophisticated text quality assessment
- **Validation Framework**: Cross-field consistency checks

### Frontend Features
- **React Hooks**: Modern functional components with state management
- **Lucide Icons**: Beautiful, consistent iconography
- **Tailwind CSS**: Utility-first styling with custom gradients
- **Drag-and-Drop**: Native file upload with visual feedback
- **Responsive Design**: Mobile-first approach with breakpoints

## Limitations & Considerations

- **OCR Accuracy**: Depends on PDF quality; scanned documents may have lower accuracy
- **Bank Format Variations**: Some statement formats may not be fully supported
- **Processing Time**: Enhanced OCR with multiple strategies takes 5-15 seconds per page
- **File Size**: Optimal for PDFs under 10MB
- **Tesseract Required**: Must be installed for scanned PDF processing
- **Currency Detection**: Automatically handles USD, GBP, and INR based on bank
- **Transaction Limits**: Extracts up to 100 transactions per statement

## Troubleshooting

### Backend Issues

**Tesseract not found**
- Verify installation: `tesseract --version`
- Update path in `app.py` if needed
- Windows: Check `C:\Program Files\Tesseract-OCR\tesseract.exe`

**Port 5000 in use**
- Change port in `app.py`: `app.run(debug=True, port=5001)`
- Update `API_URL` in frontend `App.js`

**PDF processing fails**
- Ensure PDF is not corrupted
- Check file size (< 10MB recommended)
- Verify PDF is a credit card statement

### Frontend Issues

**CORS errors**
- Ensure backend is running on port 5000
- Check Flask-CORS is installed: `pip install flask-cors`

**CSV download fails**
- Verify `exports/` directory exists in backend
- Check file permissions
- Ensure backend is accessible

## Performance Optimization

- **Enhanced Pro Mode**: Used for poor-quality scans, highest accuracy
- **Early Exit**: Stops testing strategies when excellent results achieved
- **Smart Strategy Order**: Tests best strategies first
- **Caching**: Results stored in database for quick access
- **Batch Processing**: Multiple PSM modes tested in Enhanced Pro

## Security Notes

- Files are processed locally on your machine
- No data is sent to external services
- CSV files stored in local `exports/` directory
- Database stored locally in SQLite
- Delete function removes both database records and files

## Future Enhancements

- [ ] Support for more banks (Citibank, Chase, etc.)
- [ ] Multi-language support
- [ ] Cloud storage integration
- [ ] Advanced analytics and visualizations
- [ ] Email statement import
- [ ] Mobile app version
- [ ] Batch processing multiple PDFs
- [ ] Custom export templates

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for:
- New bank format support
- OCR improvements
- UI/UX enhancements
- Bug fixes
- Documentation updates

## License

This project is open source and available under the MIT License.

## Acknowledgments

- **Tesseract OCR**: Google's open-source OCR engine
- **pypdfium2**: Fast PDF rendering library
- **Flask**: Python web framework
- **React**: JavaScript UI library
- **Tailwind CSS**: Utility-first CSS framework
- **Lucide Icons**: Beautiful icon set

---

**Version**: 5.0-optimized  
**Last Updated**: 2024  
**Status**: Production Ready

For questions, issues, or feature requests, please open an issue on GitHub.