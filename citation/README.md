# 🏛️ LegalCite: AI-Powered Citation Assistant

## Overview

LegalCite is an advanced, AI-powered legal citation assistant designed to help legal professionals, researchers, and students validate, reformat, and analyze legal citations across multiple jurisdictions and citation styles.

## 🌟 Key Features

- **Multi-Jurisdiction Support**
  - Comprehensive coverage of citation styles from US, UK, India, Australia, EU, and International courts
  - Supports multiple citation formats like Bluebook, OSCOLA, AGLC, and more

- **AI-Powered Citation Analysis**
  - Intelligent citation validation
  - Automatic hyperlink generation
  - Citation style reformatting
  - Jurisdiction-aware processing

## 📥 Input and 📤 Output Examples

### 1. Citation Validation

#### Input (US Supreme Court Citation)
```
Marbury v. Madison, 5 U.S. (1 Cranch) 137 (1803)
```

#### Output
```json
{
    "is_valid": true,
    "source_type": "case",
    "jurisdiction": "US Supreme Court",
    "error_details": null,
    "suggested_correction": null
}
```

#### Input (Invalid Indian Citation)
```
AIR 1973 SC 146 (Incorrect Format)
```

#### Output
```json
{
    "is_valid": false,
    "source_type": "case",
    "jurisdiction": "Indian Supreme Court",
    "error_details": [
        "Incorrect page number format",
        "Missing full case name"
    ],
    "suggested_correction": "AIR 1973 SC 1461 (Kesavananda Bharati v. State of Kerala)"
}
```

### 2. Citation Reformatting

#### Input (Bluebook to OSCOLA)
```
Marbury v. Madison, 5 U.S. (1 Cranch) 137 (1803)
```

#### Output (OSCOLA Style)
```
Marbury v Madison (1803) 5 US (1 Cranch) 137
```

### 3. Hyperlink Generation

#### Input
```
Marbury v. Madison, 5 U.S. (1 Cranch) 137 (1803)
```

#### Output
```
https://supreme.justia.com/cases/federal/us/5/137/
```

### 4. Jurisdiction-Specific Analysis

#### Input (Australian High Court Citation)
```
Mabo v Queensland (No 2) [1992] HCA 23
```

#### Output
```json
{
    "is_valid": true,
    "style": "AGLC",
    "source_type": "case",
    "jurisdiction": "High Court of Australia",
    "citation_components": {
        "case_name": "Mabo v Queensland",
        "year": 1992,
        "court": "HCA",
        "case_number": 23
    }
}
```

## 🛠 Prerequisites

- Python 3.8+
- Streamlit
- Google Generative AI
- python-dotenv

## 📦 Installation

[... rest of the previous README remains the same ...]