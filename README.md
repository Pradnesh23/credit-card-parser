# Credit Card Statement Parser

A full-stack application that extracts and analyzes credit card statements from PDFs using advanced OCR processing and AI-powered parsing.

## ✨ Features

- **Multi-Bank Support**: Parses statements from Capital One, American Express, ICICI, Kotak Mahindra, HDFC Bank, and SBI Card
- **Smart OCR Processing**: Advanced text extraction with auto-rotation and multi-strategy preprocessing
- **Transaction Analysis**: Automatic categorization and spending insights
- **Export Options**: Export to CSV with transaction details and master logs
- **Modern Web Interface**: Responsive design with drag-and-drop upload
- **History Management**: View, download, and delete previously parsed statements
- **Confidence Scoring**: Quality assessment for all extracted data

## 🚀 Getting Started

### Prerequisites

- **Python 3.9+**
- **Node.js 14+**
- **npm or yarn**
- **Tesseract OCR** (for processing scanned PDFs)
  - Windows: `choco install tesseract`
  - macOS: `brew install tesseract`
  - Ubuntu/Debian: `sudo apt install tesseract-ocr`

### Installation

1. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv
   # On Windows
   .\venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   
   pip install -r requirements.txt
   ```

2. **Frontend Setup**
   ```bash
   cd frontend
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

## 🛠️ Tech Stack

### Backend
- **Python** 3.9+
- **Flask** 3.0.0 - Web framework
- **Flask-CORS** 4.0.0 - Cross-origin resource sharing
- **PyPDFium2** 4.26.0 - PDF rendering at 300 DPI
- **Tesseract OCR** 0.3.13 - Optical character recognition
- **OpenCV** 4.10.0.84 (headless) - Image processing
- **NumPy** 2.1.3 - Numerical computing
- **Pillow** 10.1.0 - Image manipulation
- **SQLite** - Local database for history

### Frontend
- **React** 19.2.0 - UI library
- **Tailwind CSS** 3.3.0 - Utility-first CSS framework
- **Lucide React** 0.546.0 - Icon library
- **React Scripts** 5.0.1 - Build tooling

## Usage Guide

### Parsing a Statement

1. **Upload**: Open the application and either:
   - Drag and drop a PDF credit card statement onto the upload area
   - Click the upload area to browse and select a PDF file

2. **Process**: Click the "Parse Statement" button
   - The system will automatically detect the card issuer
   - Multiple OCR strategies will be tested (enhanced_pro, aggressive, comprehensive, light)
   - Best results will be automatically selected based on quality scores

3. **Review**: View the extracted information including:
   - Card details (issuer, last 4 digits)
   - Important dates (statement date, payment due date)
   - Financial summary (total balance, minimum payment)
   - Complete transaction list with categories
   - Spending analysis by category (Food & Dining, Gas & Transportation, Shopping, Entertainment, Healthcare, Other)
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

**Note**: The parser automatically detects the card issuer and applies appropriate patterns.

## How It Works

### Processing Pipeline

1. **Upload & Detection**
   - Frontend sends PDF to backend API
   - First page is analyzed to detect card issuer

2. **OCR Processing**
   - PDF pages rendered at 300 DPI with `pypdfium2`
   - Multiple preprocessing strategies applied:
     - **Enhanced Pro**: Maximum quality with bilateral filtering, aggressive denoising, CLAHE enhancement (clipLimit=4.0), sharpening, and combined adaptive thresholding. Tests multiple PSM modes (6, 4, 3)
     - **Aggressive**: Dense text optimization with strong denoising (h=15)
     - **Comprehensive**: Balanced approach with morphological operations and Otsu thresholding
     - **Light**: Fast processing for high-quality scans with CLAHE (clipLimit=2.0)
   - Auto-rotation based on HoughLinesP edge detection
   - Smart early exit when excellent quality is achieved (score > 0.90 AND length > 1000)

3. **Data Extraction**
   - Unified parser with bank-specific patterns
   - Context-aware field detection
   - Currency-aware amount parsing
   - Smart date normalization
   - Transaction extraction with deduplication

4. **Validation & Scoring**
   - Field-level validation (card number format, date format, amount format)
   - Confidence scoring for each field (card_last_4, statement_date, payment_due_date, total_balance, transactions)
   - Overall quality assessment as average of field scores
   - Transaction count-based scoring (minimum 10 for full score)

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
**Response**: JSON with parsed data, CSV file paths, confidence scores, and validation results
```json
{
  "success": true,
  "data": {
    "card_issuer": "Capital One",
    "card_last_4": "1234",
    "statement_date": "12/26/2023",
    "payment_due_date": "01/15/2024",
    "total_balance": "1,234.56",
    "minimum_payment": "123.45",
    "transactions": [...],
    "confidence_scores": {...},
    "extraction_metadata": {...},
    "csv_exports": {
      "simple": "path/to/simple.csv",
      "detailed": "path/to/detailed.csv",
      "master": "path/to/master.csv"
    }
  }
}
```

### `GET /api/download-csv/<filename>`
Download a generated CSV file.

**Parameters**: `filename` - Name of the CSV file (from parse response)
**Response**: CSV file download

### `GET /api/history?limit=25`
Retrieve parsing history.

**Query Parameters**: `limit` - Maximum number of records (default: 20)
**Response**: JSON with array of parse records
```json
{
  "items": [
    {
      "id": 1,
      "created_at": "2024-01-01 12:00:00",
      "issuer": "Capital One",
      "card_last_4": "1234",
      "statement_date": "12/26/2023",
      "total_balance": "1,234.56",
      "csv_exports": {...}
    }
  ]
}
```

### `DELETE /api/history/<record_id>`
Delete a parse history record and associated CSV files.

**Parameters**: `record_id` - Database ID of the record
**Response**: Success confirmation
```json
{
  "success": true,
  "message": "Record deleted successfully"
}
```

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
- **Pattern Library**: Centralized regex patterns with currency awareness (USD, GBP, INR)
- **Multi-Strategy OCR**: Four preprocessing strategies with automatic selection and early exit
- **Quality Scoring**: Sophisticated text quality assessment based on alphanumeric density, currency patterns, dates, and keywords
- **Validation Framework**: Field-level validation with confidence scoring
- **Enhanced Pro Mode**: Maximum quality extraction with multiple PSM modes (6, 4, 3)
- **Auto-Rotation**: HoughLinesP-based automatic rotation correction

### Frontend Features
- **React 19**: Modern functional components with hooks
- **Lucide Icons**: Beautiful, consistent iconography
- **Tailwind CSS**: Utility-first styling with custom gradients
- **Drag-and-Drop**: Native file upload with visual feedback
- **Responsive Design**: Mobile-first approach with breakpoints
- **Transaction Categorization**: Automatic categorization into 6 categories
- **Confidence Visualization**: Color-coded confidence indicators
- **History Management**: View, download, and delete previously parsed statements

## Limitations & Considerations

- **OCR Accuracy**: Depends on PDF quality; scanned documents may have lower accuracy
- **Bank Format Variations**: Some statement formats may not be fully supported
- **Processing Time**: Enhanced OCR with multiple strategies takes 5-15 seconds per page
- **File Size**: Optimal for PDFs under 10MB
- **Tesseract Required**: Must be installed for scanned PDF processing
- **Currency Detection**: Automatically handles USD, GBP, and INR based on bank
- **Transaction Limits**: Extracts up to 100 transactions per statement
- **Pattern Matching**: Uses regex patterns; may miss non-standard formats
- **Date Formats**: Supports multiple date formats but may struggle with ambiguous dates

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
- Backend uses Flask-CORS 4.0.0 with permissive settings for development
- Ensure backend is running on port 5000
- Check `API_URL` in environment variables or fallback to localhost

**CSV download fails**
- Verify `exports/` directory exists in backend
- Check file permissions
- Ensure backend is accessible
- File paths are automatically sanitized with `secure_filename`

## Performance Optimization

- **Enhanced Pro Mode**: Used for poor-quality scans, highest accuracy with bilateral filtering
- **Early Exit**: Stops testing strategies when excellent results achieved (score > 0.90 AND length > 1000)
- **Smart Strategy Order**: Tests enhanced_pro → aggressive → comprehensive → light
- **Database Caching**: Results stored in SQLite for quick access
- **Batch PSM Testing**: Multiple PSM modes (6, 4, 3) tested in Enhanced Pro and Aggressive modes
- **Quality Threshold**: Continues testing if extracted text is too short (< 500 chars)

## Security Notes

- Files are processed locally on your machine
- No data is sent to external services
- CSV files stored in local `exports/` directory
- Database stored locally in SQLite
- Delete function removes both database records and files

## Future Enhancements

- [ ] Support for more banks (Citibank, Chase, Discover, etc.)
- [ ] Multi-language support for non-English statements
- [ ] Cloud storage integration (AWS S3, Google Drive)
- [ ] Advanced analytics and visualizations (charts, trends)
- [ ] Email statement import
- [ ] Mobile app version
- [ ] Batch processing multiple PDFs
- [ ] Custom export templates
- [ ] Automated categorization using ML
- [ ] Budget tracking and alerts
- [ ] Export to Excel with formatting

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

## Key Improvements in Version 5.0

- Unified parser architecture with reduced code duplication
- Enhanced Pro mode for maximum OCR quality
- Smart early exit optimization (tests strategies in order: enhanced_pro → aggressive → comprehensive → light)
- Multiple PSM mode testing (6, 4, 3) for better text extraction
- Centralized pattern library with currency awareness
- Improved date normalization and validation
- Quality scoring with automatic strategy selection
- Transaction deduplication and categorization

For questions, issues, or feature requests, please open an issue on GitHub.