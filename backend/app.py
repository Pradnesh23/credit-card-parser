from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pytesseract
import cv2
import numpy as np
from PIL import Image
import re
from datetime import datetime
import io
from collections import defaultdict
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
import csv
from pathlib import Path
from werkzeug.utils import secure_filename
import sqlite3
import pypdfium2 as pdfium
import platform

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configure Tesseract
if platform.system() == 'Windows':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:
    pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'

app = Flask(__name__)
CORS(app)

EXPORTS_DIR = Path('exports')
EXPORTS_DIR.mkdir(exist_ok=True)
DB_PATH = EXPORTS_DIR / 'history.db'


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    try:
        with get_db_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS parse_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    issuer TEXT,
                    card_last_4 TEXT,
                    statement_date TEXT,
                    payment_due_date TEXT,
                    total_balance TEXT,
                    csv_simple TEXT,
                    csv_detailed TEXT,
                    csv_master TEXT
                )
            ''')
            conn.commit()
    except Exception as e:
        logger.error(f"DB init error: {e}")


@dataclass
class StatementData:
    """Statement data model"""
    card_issuer: Optional[str] = None
    card_last_4: Optional[str] = None
    statement_date: Optional[str] = None
    payment_due_date: Optional[str] = None
    total_balance: Optional[str] = None
    minimum_payment: Optional[str] = None
    available_credit: Optional[str] = None
    transactions: List[Dict[str, str]] = None
    confidence_scores: Dict[str, float] = None
    extraction_metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.transactions is None:
            self.transactions = []
        if self.confidence_scores is None:
            self.confidence_scores = {}
        if self.extraction_metadata is None:
            self.extraction_metadata = {}


class EnhancedOCRProcessor:
    """Advanced OCR processing with multiple strategies"""
    
    @staticmethod
    def auto_rotate(image: np.ndarray) -> Tuple[np.ndarray, float]:
        """Detect and correct rotation"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)
            
            if lines is None:
                return image, 0.0
            
            angles = [np.degrees(np.arctan2(y2 - y1, x2 - x1)) for x1, y1, x2, y2 in lines[:, 0]]
            median_angle = np.median(angles)
            
            if median_angle < -45:
                median_angle = 90 + median_angle
            elif median_angle > 45:
                median_angle = median_angle - 90
            
            if abs(median_angle) > 0.5:
                h, w = gray.shape[:2]
                M = cv2.getRotationMatrix2D((w // 2, h // 2), median_angle, 1.0)
                rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                return rotated, median_angle
            
            return image, 0.0
        except Exception as e:
            logger.debug(f"Auto-rotation failed: {e}")
            return image, 0.0
    
    @staticmethod
    def preprocess_pipeline(image, strategy='comprehensive'):
        """Advanced preprocessing pipeline with enhanced pro mode"""
        try:
            if isinstance(image, Image.Image):
                image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            image, rotation_angle = EnhancedOCRProcessor.auto_rotate(image)
            
            # Resize optimization - higher resolution for enhanced_pro
            height, width = image.shape[:2]
            if strategy == 'enhanced_pro':
                target_height = 3000  # Higher resolution
            else:
                target_height = 2000
            
            if height < 1500 or height > 4000:
                scale = target_height / height
                image = cv2.resize(image, (int(width * scale), target_height), 
                                 interpolation=cv2.INTER_CUBIC if height < 1500 else cv2.INTER_AREA)
            
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
            
            if strategy == 'enhanced_pro':
                # ENHANCED PRO: Maximum quality extraction
                # Step 1: Bilateral filter for edge preservation
                bilateral = cv2.bilateralFilter(gray, 11, 75, 75)
                
                # Step 2: Aggressive denoising
                denoised = cv2.fastNlMeansDenoising(bilateral, None, h=12, templateWindowSize=7, searchWindowSize=21)
                
                # Step 3: Contrast enhancement with stronger CLAHE
                clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(16, 16))
                enhanced = clahe.apply(denoised)
                
                # Step 4: Sharpening kernel
                kernel_sharp = np.array([[-1, -1, -1], 
                                        [-1,  9, -1], 
                                        [-1, -1, -1]])
                sharpened = cv2.filter2D(enhanced, -1, kernel_sharp)
                
                # Step 5: Morphological operations
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
                morph = cv2.morphologyEx(sharpened, cv2.MORPH_CLOSE, kernel)
                
                # Step 6: Adaptive thresholding with multiple methods combined
                # Method 1: Gaussian adaptive
                adaptive1 = cv2.adaptiveThreshold(morph, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                                 cv2.THRESH_BINARY, 21, 5)
                
                # Method 2: Mean adaptive
                adaptive2 = cv2.adaptiveThreshold(morph, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                                                 cv2.THRESH_BINARY, 21, 5)
                
                # Method 3: Otsu
                _, otsu = cv2.threshold(morph, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                # Combine methods (take the best of both)
                processed = cv2.bitwise_and(adaptive1, otsu)
                
                # Final cleanup
                kernel_clean = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
                processed = cv2.morphologyEx(processed, cv2.MORPH_OPEN, kernel_clean)
                
            elif strategy == 'comprehensive':
                denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(denoised)
                kernel = np.ones((2, 2), np.uint8)
                processed = cv2.morphologyEx(enhanced, cv2.MORPH_CLOSE, kernel)
                _, processed = cv2.threshold(processed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            elif strategy == 'light':
                blurred = cv2.GaussianBlur(gray, (3, 3), 0)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(blurred)
                _, processed = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            else:  # aggressive
                denoised = cv2.fastNlMeansDenoising(gray, None, h=15)
                processed = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                                cv2.THRESH_BINARY, 15, 5)
            
            return processed, {'rotation_angle': rotation_angle, 'strategy': strategy}
        except Exception as e:
            logger.error(f"Preprocessing error: {e}")
            return image, {}
    
    @staticmethod
    def extract_text_with_config(image, config='--oem 3 --psm 6'):
        """Extract text using OCR"""
        try:
            pil_image = Image.fromarray(image) if not isinstance(image, Image.Image) else image
            return pytesseract.image_to_string(pil_image, config=config).strip()
        except Exception as e:
            logger.error(f"OCR extraction error: {e}")
            return ""
    
    @staticmethod
    def multi_strategy_ocr(pil_image: Image.Image) -> Dict[str, Any]:
        """Try multiple OCR strategies with enhanced pro mode"""
        results = []
        
        # Optimized strategy order: enhanced_pro -> aggressive -> comprehensive -> light
        # enhanced_pro is best for difficult docs, aggressive for dense text
        strategies = ['enhanced_pro', 'aggressive', 'comprehensive', 'light']
        
        for strategy in strategies:
            try:
                processed, metadata = EnhancedOCRProcessor.preprocess_pipeline(pil_image, strategy=strategy)
                
                # Try multiple PSM modes for enhanced_pro and aggressive
                if strategy in ['enhanced_pro', 'aggressive']:
                    psm_modes = ['--oem 3 --psm 6', '--oem 3 --psm 4', '--oem 3 --psm 3']
                    best_text = ""
                    best_score = 0.0
                    
                    for psm in psm_modes:
                        text = EnhancedOCRProcessor.extract_text_with_config(processed, psm)
                        score = EnhancedOCRProcessor._quality_score(text)
                        if score > best_score:
                            best_score = score
                            best_text = text
                    
                    text = best_text if best_text else EnhancedOCRProcessor.extract_text_with_config(processed)
                else:
                    text = EnhancedOCRProcessor.extract_text_with_config(processed)
                
                score = EnhancedOCRProcessor._quality_score(text)
                results.append({'strategy': strategy, 'text': text, 'score': score, 
                              'length': len(text), 'metadata': metadata})
                
                logger.info(f"Strategy '{strategy}': {len(text)} chars, score {score:.3f}")
                
                # Only early exit if we have EXCELLENT results (high score AND enough content)
                if score > 0.90 and len(text) > 1000:
                    logger.info(f"Excellent quality result achieved, stopping at '{strategy}'")
                    break
                    
                # Continue trying if text is too short (likely missed content)
                if len(text) < 500:
                    logger.info(f"Text too short ({len(text)} chars), trying next strategy")
                    continue
                    
            except Exception as e:
                logger.debug(f"Strategy '{strategy}' failed: {e}")
        
        if not results:
            return {'strategy': 'none', 'text': '', 'score': 0.0}
        
        # Prioritize longer text with decent scores over short text with high scores
        best = max(results, key=lambda r: (r['length'] > 1000, r['score'], r['length']))
        logger.info(f"Best strategy: '{best['strategy']}' with score {best['score']:.3f}, length {best['length']}")
        
        return {**best, 'all_results': results}
    
    @staticmethod
    def _quality_score(text: str) -> float:
        """Calculate OCR quality score"""
        if not text:
            return 0.0
        
        total = len(text)
        useful = sum(c.isalnum() for c in text)
        density = useful / max(total, 1)
        
        # Currency patterns (£, $, Rs)
        has_amount = len(re.findall(r"[£\$]?[\d,]+\.\d{2}", text))
        has_date = len(re.findall(r"\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4}", text))
        has_card = 1 if re.search(r"\d{4}", text) else 0
        
        keywords = ['statement', 'balance', 'payment', 'due', 'card', 'account', 'total', 'date', 'credit']
        keyword_score = sum(1 for kw in keywords if kw.lower() in text.lower()) / len(keywords)
        
        return 0.3 * density + 0.2 * min(1.0, has_amount / 5) + 0.2 * min(1.0, has_date / 3) + 0.1 * has_card + 0.2 * keyword_score


class PatternLibrary:
    """Centralized pattern library for all banks"""
    
    DATE_FORMATS = [
        '%m/%d/%y', '%m/%d/%Y',  # US format: 12/26/23, 01/14/2024
        '%d %B %y', '%d %b %y',  # UK format: 5 October 24
        '%B %d, %Y', '%b %d, %Y',  # AMEX India: February 1, 2024
        '%d %B %Y', '%d %b %Y',  # Full year: 14 January 2024
        '%d-%b-%Y', '%d-%b-%y',  # Kotak: 1-Mar-2023, 19-Mar-2023
        '%m-%d-%Y', '%m-%d-%y', '%d/%m/%Y', '%d-%m-%Y',
        '%Y-%m-%d',
    ]
    
    # Universal patterns with bank-specific variations
    PATTERNS = {
        'card_number': [
            r'(?:Card|Account).*?(?:ending|Ending|No\.?|Number)[:\s]+.*?(\d{4})',
            r'(?:Card|Account).*?[xX*]{4,}[\s\-]*(\d{4,5})',
            r'xxxx\s*xxxx\s*xxxx\s*(\d{4,5})',
            r'\*{4}\s*\*{4}\s*\*{4}\s*(\d{4,5})',
            r'(\d{4}\s+\d{2}[xX*]{2}\s+[xX*]{4}\s+\d{4})',  # HDFC format
            r'MasterCard\s+Account\s+No\.\s+\*+\s*(\d{4})',  # Capital One specific
        ],
        'statement_date': [
            r'Statement\s+date\s+(\d{1,2}\s+\w+\s+\d{2,4})',  # Capital One: "Statement date 5 October 24"
            r'Statement\s+Date[:\s]*(\d{1,2}-\w{3}-\d{4})',  # Kotak: "Statement Date 1-Mar-2023"
            r'Closing\s+Date[:\s]*(\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4})',  # AMEX US: "Closing Date 12/26/23"
            r'Statement\s+(?:Date|Period)[:\s]*.*?(?:to|To)\s+(\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4})',  # AMEX India: "From Dec 15 to Jan 14"
            r'Statement\s+(?:Date|Period)[:\s]*.*?(?:To|to)\s+(\d{1,2}-\w{3}-\d{4})',  # Kotak: "Period 2-Feb-2023 To 1-Mar-2023"
            r'Statement\s+Date[:\s]*(\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4})',  # HDFC: "Statement Date:08/06/2019"
            r'Statement\s+(?:Closing\s+|End\s+|Generation\s+)?Date[:\s]*(\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4})',
            r'Billing\s+(?:Cycle|Period)[:\s]+.*?(?:to|through)\s+(\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4})',
            r'Date[:\s]*(\d{1,2}[\/-]\d{1,2}[\/-]\d{4})',  # Generic fallback
        ],
        'due_date': [
            r"(?:due|Due)\s+on\s+(\d{1,2}\s+\w+\s+\d{2,4})",  # Capital One: "due on 31 Oct 24"
            r"It'?s\s+due\s+on\s+(\d{1,2}\s+\w+\s+\d{2,4})",  # Capital One: "It's due on 31 Oct 24"
            r'Due\s+Date[:\s]*(\d{1,2}-\w{3}-\d{4})',  # Kotak: "Due Date 19-Mar-2023"
            r'(?:Due\s+by|Due\s+Date)[:\s]*(\d{1,2}\s+\w+\s+\d{2,4})',  # AMEX India: "Due by February 1, 2024"
            r'Payment\s+Due\s+Date[:\s]*(\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4})',  # HDFC: "Payment Due Date 28/06/2019"
            r'Payment\s+Due\s+(?:By|On)[:\s]*(\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4})',
            r'Due\s+Date[:\s]+(\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4})',
            r'Pay(?:ment)?\s+by[:\s]+(\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4})',
            r'Last\s+Date\s+(?:of|for)\s+Payment[:\s]+(\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4})',
            r'(\w+\s+\d{1,2},\s+\d{4})',  # AMEX India: "February 1, 2024" (fallback for standalone date)
        ],
        'total_balance': {
            'usd': [
                r'New\s+Balance[:\s]+\$?([\d,]+\.\d{2})',  # AMEX US: "New Balance $0.00"
                r'(?:Account\s+)?Total[:\s]+\$?([\d,]+\.\d{2})',  # AMEX US: "Account Total"
                r'(?:Total|Current)\s+Balance[:\s]+\$?([\d,]+\.\d{2})',
                r'(?:Total\s+)?(?:Amount\s+)?Due[:\s]+\$?([\d,]+\.\d{2})',
                r'(?:Total\s+)?(?:Payment\s+)?Due[:\s]+\$?([\d,]+\.\d{2})',
            ],
            'inr': [
                r'Total\s+Amount\s+Due\s+\(Rs\.\)[:\s]*([\d,]+\.\d{2})',  # Kotak: "Total Amount Due (Rs.) 478,387.66"
                r'Closing\s+Balance\s+Rs[:\s]*([\d,]+\.\d{2})',  # AMEX India: "Closing Balance Rs 56,856.49"
                r'Total\s+Dues[:\s]+(?:Rs\.?|INR)?\s*([\d,]+\.\d{2})',  # HDFC: "Total Dues 45,240.00"
                r'Total\s+(?:Amount\s+)?Due[:\s]+(?:Rs\.?|INR|\(Rs\.\))?\s*([\d,]+\.\d{2})',
                r'Total\s+(?:Payment\s+)?Due[:\s]+(?:Rs\.?|INR)?\s*([\d,]+\.\d{2})',
                r'(?:New|Current|Statement)\s+(?:Balance|Outstanding|Dues)[:\s]+(?:Rs\.?|INR)?\s*([\d,]+\.\d{2})',
                r'Amount\s+Payable[:\s]+(?:Rs\.?|INR)?\s*([\d,]+\.\d{2})',
            ],
            'gbp': [
                r'(?:Your\s+)?(?:new\s+)?balance[:\s]+£([\d,]+\.\d{2})',  # Capital One: "Your new balance £1,219.26"
                r'(?:NEW\s+)?CLOSING\s+BALANCE[:\s]+£([\d,]+\.\d{2})',
                r'(?:Total\s+)?(?:Amount\s+)?Due[:\s]+£([\d,]+\.\d{2})',
                r'(?:Total\s+)?(?:Payment\s+)?Due[:\s]+£([\d,]+\.\d{2})',
                r'(?:Previous|New|Current)\s+balance[:\s]+£([\d,]+\.\d{2})',
            ]
        },
        'minimum_payment': {
            'usd': [
                r'Minimum\s+(?:Payment\s+)?Due[:\s]+\$?([\d,]+\.\d{2})',  # AMEX US: "Minimum Due $0.00"
                r'Minimum\s+(?:Amount\s+Due|Payment)[:\s]+\$?([\d,]+\.\d{2})',
                r'Min(?:imum)?\s+(?:Pay|Pmt|Due)[:\s]+\$?([\d,]+\.\d{2})',
            ],
            'inr': [
                r'Min(?:imum)?\s+Payment\s+Due\s+Rs[:\s]*([\d,]+\.\d{2})',  # AMEX India: "Min Payment Due Rs 41,609.78"
                r'Minimum\s+(?:Payment|Due)[:\s]*Rs\.?\s*([\d,]+\.\d{2})',  # AMEX India alternate
                r'Minimum\s+Amount\s+Due[:\s]+(?:Rs\.?|INR)?\s*([\d,]+\.\d{2})',  # HDFC standard
                r'Minimum\s+(?:Payment|Due)[:\s]+(?:Rs\.?|INR)?\s*([\d,]+\.\d{2})',
                r'Min(?:imum)?\s+(?:Pay|Amt)[:\s]+(?:Rs\.?|INR)?\s*([\d,]+\.\d{2})',
            ],
            'gbp': [
                r'(?:minimum|Minimum)\s+payment[:\s]+(?:is\s+)?£([\d,]+\.\d{2})',  # Capital One: "minimum payment is £62.78"
                r'(?:Minimum|Min\.?)\s+(?:Payment|Due|Amount\s+Due)[:\s]+£([\d,]+\.\d{2})',
            ]
        },
        'transactions': {
            'date_desc_amount': [
                # GBP format
                r'(\d{1,2}\s+\w{3,9})\s+(.+?)\s+£?([\d,]+\.\d{2})',  # "16 Sep Description 43.79"
                # Standard formats
                r'(\d{1,2}[\/-]\d{1,2}(?:[\/-]\d{2,4})?)\s+(.+?)\s+(?:\$|Rs\.?|INR|£)?\s*([\d,]+\.\d{2})',
                r'(\w{3,9}\s+\d{1,2})\s+(.+?)\s+(?:\$|Rs\.?|INR|£)?\s*([\d,]+\.\d{2})',
            ],
        }
    }
    
    @classmethod
    def get_currency_patterns(cls, issuer: str, field: str):
        """Get currency-specific patterns based on issuer"""
        currency_map = {
            'capitalone': 'gbp',  # Capital One UK uses GBP
            'amex': 'inr' if 'india' in issuer.lower() else 'usd',
            'sbi': 'inr',
            'hdfc': 'inr',
            'kotak': 'inr'
        }
        currency = currency_map.get(issuer.lower(), 'usd')
        
        patterns = cls.PATTERNS.get(field, {})
        if isinstance(patterns, dict):
            return patterns.get(currency, patterns.get('usd', []))
        return patterns


class UnifiedCreditCardParser:
    """Unified parser for all credit card issuers"""
    
    def __init__(self, issuer: str):
        self.issuer = issuer
        self.data = StatementData()
        self.text = ""
        self.ocr_processor = EnhancedOCRProcessor()
    
    def extract_text_from_pdf(self, pdf_file) -> bool:
        """Extract text using enhanced OCR"""
        try:
            full_text = []
            pdf = pdfium.PdfDocument(pdf_file)
            
            for page_num in range(len(pdf)):
                page = pdf[page_num]
                pil_image = page.render(scale=300/72).to_pil()
                ocr_result = self.ocr_processor.multi_strategy_ocr(pil_image)
                
                if ocr_result.get('text'):
                    full_text.append(ocr_result['text'])
                    logger.info(f"Page {page_num + 1}: {ocr_result['strategy']}, {ocr_result['length']} chars, score {ocr_result['score']:.2f}")
            
            self.text = "\n".join(full_text)
            self.data.extraction_metadata.update({
                'text_length': len(self.text),
                'num_pages': len(pdf),
                'extraction_method': 'Enhanced OCR',
                'extraction_timestamp': datetime.now().isoformat()
            })
            
            return len(self.text) > 100
        except Exception as e:
            logger.error(f"PDF extraction error: {e}", exc_info=True)
            return False
    
    def fuzzy_find(self, patterns: List[str]) -> Optional[str]:
        """Find pattern in text with fuzzy matching"""
        for pattern in patterns:
            try:
                match = re.search(pattern, self.text, re.IGNORECASE | re.MULTILINE)
                if match:
                    result = match.group(1).strip()
                    # Clean common OCR errors
                    result = result.replace('|', '1').replace('O', '0') if result.isdigit() else result
                    return re.sub(r'\s+', ' ', result)
            except Exception as e:
                logger.debug(f"Pattern error: {e}")
        return None
    
    def extract_date(self, patterns: List[str]) -> Optional[str]:
        """Extract and normalize dates"""
        result = self.fuzzy_find(patterns)
        if not result:
            return None
        
        result = result.strip().replace(',', '')
        
        for fmt in PatternLibrary.DATE_FORMATS:
            try:
                date_obj = datetime.strptime(result, fmt)
                return date_obj.strftime('%m/%d/%Y')
            except ValueError:
                continue
        
        return result
    
    def extract_amount(self, patterns: List[str]) -> Optional[str]:
        """Extract monetary amounts"""
        result = self.fuzzy_find(patterns)
        if not result:
            return None
        
        cleaned = re.sub(r'[^\d,\.\-]', '', result)
        return cleaned if re.match(r'^-?[\d,]*\.?\d+$', cleaned) else None
    
    def extract_transactions(self, max_count: int = 100) -> List[Dict[str, str]]:
        """Extract transactions using universal patterns"""
        transactions = []
        seen = set()
        
        for pattern in PatternLibrary.PATTERNS['transactions']['date_desc_amount']:
            matches = re.findall(pattern, self.text, re.MULTILINE)
            
            for match in matches[:max_count]:
                if len(match) < 3:
                    continue
                
                date, desc, amount = match[0].strip(), match[1].strip()[:150], match[2].strip()
                
                # Filter invalid entries
                skip_words = ['total', 'subtotal', 'balance', 'date', 'description', 'amount', 'payment', 'statement']
                if any(word in desc.lower() for word in skip_words) and len(desc) < 30:
                    continue
                
                try:
                    amt_float = float(amount.replace(',', ''))
                    if amt_float > 100000 or amt_float < 0.01:
                        continue
                except:
                    continue
                
                # Normalize dates
                date = self._normalize_transaction_date(date)
                
                # Deduplicate
                key = (date, amount, desc[:30])
                if key not in seen:
                    seen.add(key)
                    transactions.append({'date': date, 'description': desc, 'amount': amount, 'source': 'text'})
        
        return transactions[:max_count]
    
    def _normalize_transaction_date(self, date_str: str) -> str:
        """Normalize transaction dates to standard format"""
        # Handle "Mon Day" format
        if re.match(r'^\w{3,9}\s+\d{1,2}$', date_str):
            try:
                parsed = datetime.strptime(f"{date_str} {datetime.now().year}", "%b %d %Y")
                return parsed.strftime("%m/%d/%Y")
            except:
                pass
        # Handle "Day Mon" format
        elif re.match(r'^\d{1,2}\s+\w{3}$', date_str):
            try:
                day, month = date_str.split()
                parsed = datetime.strptime(f"{month} {day} {datetime.now().year}", "%b %d %Y")
                return parsed.strftime("%m/%d/%Y")
            except:
                pass
        
        return date_str
    
    def validate_extraction(self):
        """Validate extracted data"""
        scores = {}
        
        # Validate card number
        scores['card_last_4'] = 1.0 if (self.data.card_last_4 and re.match(r'^\d{4,5}', self.data.card_last_4)) else 0.0
        
        # Validate dates
        for field in ['statement_date', 'payment_due_date']:
            value = getattr(self.data, field)
            scores[field] = 1.0 if (value and re.match(r'\d{1,2}/\d{1,2}/\d{4}', value)) else 0.0
        
        # Validate amount
        scores['total_balance'] = 1.0 if (self.data.total_balance and re.match(r'^[\d,]+\.\d{2}', self.data.total_balance)) else 0.0
        
        # Validate transactions
        scores['transactions'] = min(1.0, len(self.data.transactions) / 10)
        
        self.data.confidence_scores = scores
        self.data.extraction_metadata['overall_confidence'] = round(sum(scores.values()) / len(scores), 2) if scores else 0.0
    
    def parse(self, pdf_file) -> Optional[Dict[str, Any]]:
        """Main parsing method"""
        if not self.extract_text_from_pdf(pdf_file):
            return None
        
        self.data.card_issuer = {
            'capitalone': 'Capital One',
            'amex': 'American Express',
            'sbi': 'SBI Card',
            'hdfc': 'HDFC Bank',
            'kotak': 'Kotak Mahindra'
        }.get(self.issuer.lower(), self.issuer)
        
        # Extract card number - handle special case for HDFC full format
        card_result = self.fuzzy_find(PatternLibrary.PATTERNS['card_number'])
        if card_result:
            last_4_matches = re.findall(r'\d{4,5}', card_result)
            self.data.card_last_4 = last_4_matches[-1] if last_4_matches else card_result
        
        # Extract dates
        self.data.statement_date = self.extract_date(PatternLibrary.PATTERNS['statement_date'])
        self.data.payment_due_date = self.extract_date(PatternLibrary.PATTERNS['due_date'])
        
        # Extract amounts with currency-specific patterns
        balance_patterns = PatternLibrary.get_currency_patterns(self.issuer, 'total_balance')
        min_patterns = PatternLibrary.get_currency_patterns(self.issuer, 'minimum_payment')
        
        self.data.total_balance = self.extract_amount(balance_patterns)
        self.data.minimum_payment = self.extract_amount(min_patterns)
        
        # Extract transactions
        self.data.transactions = self.extract_transactions()
        
        # Validate
        self.validate_extraction()
        
        return asdict(self.data)


class CSVExporter:
    """Handles CSV export"""
    
    @staticmethod
    def save_to_csv(data: Dict[str, Any], filename: str = None) -> str:
        """Save summary to CSV"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            issuer = data.get('card_issuer', 'unknown').replace(' ', '_')
            card = data.get('card_last_4', 'XXXX')
            filename = f"{issuer}_{card}_{timestamp}.csv"
        
        filepath = EXPORTS_DIR / filename
        
        main_data = {
            'Card Issuer': data.get('card_issuer', 'N/A'),
            'Card Last 4': data.get('card_last_4', 'N/A'),
            'Statement Date': data.get('statement_date', 'N/A'),
            'Payment Due Date': data.get('payment_due_date', 'N/A'),
            'Total Balance': data.get('total_balance', 'N/A'),
            'Minimum Payment': data.get('minimum_payment', 'N/A'),
            'Extraction Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=main_data.keys())
            writer.writeheader()
            writer.writerow(main_data)
        
        return str(filepath)
    
    @staticmethod
    def save_with_transactions(data: Dict[str, Any], filename: str = None) -> str:
        """Save detailed CSV with transactions"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            issuer = data.get('card_issuer', 'unknown').replace(' ', '_')
            card = data.get('card_last_4', 'XXXX')
            filename = f"{issuer}_{card}_detailed_{timestamp}.csv"
        
        filepath = EXPORTS_DIR / filename
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['STATEMENT SUMMARY'])
            writer.writerow([])
            writer.writerow(['Card Issuer', data.get('card_issuer', 'N/A')])
            writer.writerow(['Card Last 4', data.get('card_last_4', 'N/A')])
            writer.writerow(['Statement Date', data.get('statement_date', 'N/A')])
            writer.writerow(['Payment Due Date', data.get('payment_due_date', 'N/A')])
            writer.writerow(['Total Balance', data.get('total_balance', 'N/A')])
            writer.writerow(['Minimum Payment', data.get('minimum_payment', 'N/A')])
            writer.writerow([])
            
            if data.get('transactions'):
                writer.writerow(['TRANSACTIONS'])
                writer.writerow(['Date', 'Description', 'Amount'])
                for txn in data['transactions']:
                    writer.writerow([txn.get('date', ''), txn.get('description', ''), txn.get('amount', '')])
        
        return str(filepath)
    
    @staticmethod
    def append_to_master(data: Dict[str, Any]) -> str:
        """Append to master CSV"""
        filepath = EXPORTS_DIR / 'master_statements.csv'
        exists = filepath.exists()
        
        row = {
            'Extraction Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Card Issuer': data.get('card_issuer', 'N/A'),
            'Card Last 4': data.get('card_last_4', 'N/A'),
            'Statement Date': data.get('statement_date', 'N/A'),
            'Payment Due Date': data.get('payment_due_date', 'N/A'),
            'Total Balance': data.get('total_balance', 'N/A'),
            'Minimum Payment': data.get('minimum_payment', 'N/A'),
            'Transaction Count': len(data.get('transactions', [])),
            'Confidence': data.get('extraction_metadata', {}).get('overall_confidence', 0)
        }
        
        with open(filepath, 'a' if exists else 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            if not exists:
                writer.writeheader()
            writer.writerow(row)
        
        return str(filepath)


def detect_issuer(text: str) -> Optional[str]:
    """Detect card issuer from text"""
    text_lower = text.lower()
    scores = defaultdict(int)
    
    indicators = {
        'capitalone': ['capital one', 'capitalone', 'capital 1'],
        'amex': ['american express', 'amex', 'aebc', 'americanexpress.com'],
        'icici': ['icici bank credit card', 'icici bank', 'icici'],
        'sbi': ['sbi card', 'state bank of india', 'sbi'],
        'hdfc': ['hdfc bank', 'hdfc'],
        'kotak': ['kotak mahindra', 'kotak']
    }
    
    for issuer, keywords in indicators.items():
        for keyword in keywords:
            if keyword in text_lower:
                scores[issuer] += 10
    
    # Additional location-based indicators
    if 'richmond, va' in text_lower or 'mclean, va' in text_lower or 'carol stream il' in text_lower:
        scores['capitalone'] += 5
        scores['amex'] += 5  # AMEX US also uses Carol Stream
    if 'gurgaon' in text_lower or 'gurugram' in text_lower or 'cyber city' in text_lower:
        scores['amex'] += 8  # AMEX India
    if 'mumbai' in text_lower:
        scores['hdfc'] += 3
        scores['kotak'] += 3
    if 'chennai' in text_lower or 'thiruvanmiyur' in text_lower:
        scores['hdfc'] += 5
    if 'kolkata' in text_lower or 'kolkatta' in text_lower:
        scores['hdfc'] += 2
        scores['sbi'] += 2
    
    # Card-specific indicators
    if 'membership rewards' in text_lower:
        scores['amex'] += 5
    if 'times card' in text_lower:
        scores['hdfc'] += 7
    if 'platinum' in text_lower and 'travel' in text_lower:
        scores['amex'] += 3
    if 'corporate credit card' in text_lower:
        scores['kotak'] += 5
    if 'crn' in text_lower or 'customer relationship number' in text_lower:
        scores['kotak'] += 3
    
    return max(scores, key=scores.get) if scores else None


@app.route('/api/parse', methods=['POST'])
def parse_statement():
    """Parse credit card statement"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    if not file or not file.filename:
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are supported'}), 400
    
    try:
        pdf_bytes = io.BytesIO(file.read())
        
        # Detect issuer from first page
        try:
            pdf_bytes.seek(0)
            pdf = pdfium.PdfDocument(pdf_bytes)
            if len(pdf) == 0:
                return jsonify({'error': 'PDF has no pages'}), 400
            
            first_page = pdf[0]
            pil_image = first_page.render(scale=300/72).to_pil()
            processed, _ = EnhancedOCRProcessor.preprocess_pipeline(pil_image, strategy='light')
            sample_text = EnhancedOCRProcessor.extract_text_with_config(processed)
        except Exception as e:
            logger.warning(f"Issuer detection failed: {e}")
            sample_text = ''
        
        issuer = detect_issuer(sample_text)
        
        if not issuer:
            return jsonify({
                'error': 'Unable to detect credit card issuer',
                'supported_issuers': ['Capital One', 'American Express', 'SBI Card', 'HDFC Bank', 'Kotak Mahindra']
            }), 400
        
        # Parse with unified parser
        pdf_bytes.seek(0)
        parser = UnifiedCreditCardParser(issuer)
        result = parser.parse(pdf_bytes)
        
        if not result:
            return jsonify({'error': 'Failed to parse PDF'}), 500
        
        # Export to CSV
        csv_simple = CSVExporter.save_to_csv(result)
        csv_detailed = CSVExporter.save_with_transactions(result)
        csv_master = CSVExporter.append_to_master(result)
        
        result['csv_exports'] = {
            'simple': csv_simple,
            'detailed': csv_detailed,
            'master': csv_master
        }
        
        # Save to database
        try:
            with get_db_connection() as conn:
                conn.execute(
                    '''INSERT INTO parse_history 
                       (created_at, issuer, card_last_4, statement_date, payment_due_date, 
                        total_balance, csv_simple, csv_detailed, csv_master)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), result.get('card_issuer'),
                     result.get('card_last_4'), result.get('statement_date'),
                     result.get('payment_due_date'), result.get('total_balance'),
                     csv_simple, csv_detailed, csv_master)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"DB insert error: {e}")
        
        return jsonify({
            'success': True,
            'data': result,
            'message': 'Statement parsed and saved successfully'
        })
    
    except Exception as e:
        logger.error(f"Parse error: {e}", exc_info=True)
        return jsonify({'error': f'Error processing PDF: {str(e)}'}), 500


@app.route('/api/download-csv/<path:filename>', methods=['GET'])
def download_csv(filename: str):
    """Download CSV file"""
    try:
        safe_name = secure_filename(Path(filename).name)
        file_path = EXPORTS_DIR / safe_name
        
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(file_path, mimetype='text/csv', as_attachment=True, download_name=safe_name)
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': 'Download failed'}), 500


@app.route('/api/history', methods=['GET'])
def list_history():
    """List parsing history"""
    try:
        limit = int(request.args.get('limit', 20))
        with get_db_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM parse_history ORDER BY id DESC LIMIT ?',
                (limit,)
            ).fetchall()
        
        items = [{
            'id': r['id'],
            'created_at': r['created_at'],
            'issuer': r['issuer'],
            'card_last_4': r['card_last_4'],
            'statement_date': r['statement_date'],
            'total_balance': r['total_balance'],
            'csv_exports': {
                'simple': r['csv_simple'],
                'detailed': r['csv_detailed'],
                'master': r['csv_master']
            }
        } for r in rows]
        
        return jsonify({'items': items})
    except Exception as e:
        logger.error(f"History error: {e}")
        return jsonify({'error': 'Failed to load history'}), 500


@app.route('/api/history/<int:record_id>', methods=['DELETE'])
def delete_history(record_id: int):
    """Delete a parse history record and associated CSV files"""
    try:
        # Get the record to find CSV files
        with get_db_connection() as conn:
            row = conn.execute(
                'SELECT * FROM parse_history WHERE id = ?',
                (record_id,)
            ).fetchone()
            
            if not row:
                return jsonify({'error': 'Record not found'}), 404
            
            # Delete CSV files if they exist
            csv_files = [row['csv_simple'], row['csv_detailed'], row['csv_master']]
            for csv_path in csv_files:
                if csv_path:
                    try:
                        file_path = Path(csv_path)
                        if file_path.exists() and file_path.is_file():
                            file_path.unlink()
                            logger.info(f"Deleted file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete file {csv_path}: {e}")
            
            # Delete database record
            conn.execute('DELETE FROM parse_history WHERE id = ?', (record_id,))
            conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Record deleted successfully'
        })
    except Exception as e:
        logger.error(f"Delete error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to delete record'}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '5.0-optimized',
        'features': [
            'Unified parser architecture',
            'Multi-strategy OCR with early exit',
            'Centralized pattern library',
            'Currency-aware extraction',
            'Smart date normalization',
            'Reduced code duplication',
            'Enhanced performance'
        ],
        'supported_banks': ['Capital One', 'American Express', 'SBI Card', 'HDFC Bank', 'Kotak Mahindra'],
        'exports_directory': str(EXPORTS_DIR.absolute())
    })


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0',debug=True, port=5000)